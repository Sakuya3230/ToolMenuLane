# -*- coding: utf-8 -*-

import json

try:
    from PySide6.QtWidgets import *
    from PySide6.QtGui import *
    from PySide6.QtCore import *
except ImportError:
    from PySide2.QtWidgets import *
    from PySide2.QtGui import *
    from PySide2.QtCore import *


__all__ = ["MenuConfigEditor"]


class _Node(object):
    """ツリーの各行が指す、実データ(dict)への参照をまとめたもの。
    dataはJSONの構造そのもの(dict)であり、編集はこのdictを直接書き換える形で行う"""

    def __init__(self, kind, data, siblings):
        self.kind = kind          # "profile" または "item"
        self.data = data          # 実データのdict
        self.siblings = siblings  # このdataが属しているリスト(削除/並び替えに使う)


class MenuConfigEditor(QDialog):

    CORNER_RADIUS    = 14
    BACKGROUND_COLOR = QColor(30, 30, 30, 235)
    BORDER_COLOR     = QColor(255, 255, 255, 30)
    TITLE_COLOR      = QColor(230, 230, 230)
    DRAG_HANDLE_HEIGHT = 34
    INVALID_TEXT_COLOR = "#ff6b6b"

    savedToPath = Signal(str)

    def __init__(self, initial_path=None, parent=None):
        super(MenuConfigEditor, self).__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(760, 520)

        self._is_dragging = False
        self._drag_start_global = None
        self._drag_start_window_pos = None

        self._current_path = None
        self._root_data = {"settings": {}, "profiles": []}
        self._new_item_counter = 0
        self._current_node = None
        self._updating_form = False   # フォーム側からのシグナルが、読み込み時の値設定で誤発火しないようにするガード
        self._is_dirty = False   # ← 追加
        self._closing_confirmed = False   # ← 追加

        self._build_ui()

        if initial_path:
            self._load_from_path(initial_path)
        else:
            self._new_document()

    # ---------------------------------------------------------
    # UI構築
    # ---------------------------------------------------------
    def _build_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        self._background = QWidget(self)
        outer_layout.addWidget(self._background)

        root_layout = QVBoxLayout(self._background)
        root_layout.setContentsMargins(16, 16, 16, 16)

        self._title_label = QLabel(u"メニュー構成エディタ")   # ← title_labelからself._title_labelへ変更
        self._title_label.setFixedHeight(self.DRAG_HANDLE_HEIGHT)
        self._title_label.setStyleSheet(
            "color: rgba({0},{1},{2},255); font-weight: bold; background: transparent;".format(
                self.TITLE_COLOR.red(), self.TITLE_COLOR.green(), self.TITLE_COLOR.blue()
            )
        )
        root_layout.addWidget(self._title_label)

        file_row = QHBoxLayout()
        self._open_button = QPushButton(u"開く...")
        self._save_button = QPushButton(u"上書き保存")
        self._save_as_button = QPushButton(u"名前を付けて保存...")
        self._path_label = QLabel(u"(未保存)")
        self._path_label.setStyleSheet("color: rgba(200,200,200,160); background: transparent;")
        file_row.addWidget(self._open_button)
        file_row.addWidget(self._save_button)
        file_row.addWidget(self._save_as_button)
        file_row.addStretch()
        file_row.addWidget(self._path_label)
        root_layout.addLayout(file_row)

        split_layout = QHBoxLayout()
        root_layout.addLayout(split_layout, 1)

        left_layout = QVBoxLayout()
        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setSelectionMode(QAbstractItemView.SingleSelection)
        left_layout.addWidget(self._tree, 1)

        tree_button_row = QHBoxLayout()
        self._add_profile_button = QPushButton(u"+ Profile")
        self._add_item_button = QPushButton(u"+ 項目")
        self._delete_button = QPushButton(u"削除")
        self._move_up_button = QPushButton(u"↑")
        self._move_down_button = QPushButton(u"↓")
        tree_button_row.addWidget(self._add_profile_button)
        tree_button_row.addWidget(self._add_item_button)
        tree_button_row.addWidget(self._delete_button)
        tree_button_row.addWidget(self._move_up_button)
        tree_button_row.addWidget(self._move_down_button)
        left_layout.addLayout(tree_button_row)

        split_layout.addLayout(left_layout, 1)

        self._form_widget = QWidget()
        form_layout = QFormLayout(self._form_widget)

        self._id_edit = QLineEdit()
        form_layout.addRow(u"ID", self._id_edit)

        self._label_edit = QLineEdit()
        form_layout.addRow(u"Label", self._label_edit)

        icon_row = QHBoxLayout()
        self._icon_edit = QLineEdit()
        self._icon_browse_button = QPushButton(u"参照...")
        icon_row.addWidget(self._icon_edit)
        icon_row.addWidget(self._icon_browse_button)
        form_layout.addRow(u"Icon", icon_row)

        color_row = QHBoxLayout()
        self._color_swatch = QLabel()
        self._color_swatch.setFixedSize(24, 24)
        self._color_button = QPushButton(u"色を選択...")
        self._color_clear_button = QPushButton(u"クリア")
        color_row.addWidget(self._color_swatch)
        color_row.addWidget(self._color_button)
        color_row.addWidget(self._color_clear_button)
        form_layout.addRow(u"Color", color_row)

        self._action_edit = QLineEdit()
        self._action_edit.setPlaceholderText(u"module.path:function")
        form_layout.addRow(u"Action", self._action_edit)

        action_hint = QLabel(u'"："を含む場合は関数呼び出し、含まない場合はPythonコードとして直接実行されます。')   # ← 追加
        action_hint.setStyleSheet("color: rgba(200,200,120,180); font-size: 10px; background: transparent;")   # ← 追加
        action_hint.setWordWrap(True)   # ← 追加
        form_layout.addRow(u"", action_hint)   # ← 追加

        self._args_edit = QLineEdit()
        self._args_edit.setPlaceholderText(u'["value1", 2, true]')
        form_layout.addRow(u"Args", self._args_edit)

        self._kwargs_edit = QLineEdit()
        self._kwargs_edit.setPlaceholderText(u'{"key": "value"}')
        form_layout.addRow(u"Kwargs", self._kwargs_edit)

        split_layout.addWidget(self._form_widget, 1)

        self._form_widget.setEnabled(False)

        button_row = QHBoxLayout()
        button_row.addStretch()
        self._close_button = QPushButton(u"閉じる")
        button_row.addWidget(self._close_button)
        root_layout.addLayout(button_row)

        # ---- 接続 ----
        self._tree.currentItemChanged.connect(self._on_tree_selection_changed)

        self._add_profile_button.clicked.connect(self._on_add_profile)
        self._add_item_button.clicked.connect(self._on_add_item)
        self._delete_button.clicked.connect(self._on_delete_selected)
        self._move_up_button.clicked.connect(lambda: self._on_move_selected(-1))
        self._move_down_button.clicked.connect(lambda: self._on_move_selected(1))

        self._id_edit.textChanged.connect(self._on_id_changed)
        self._label_edit.textChanged.connect(self._on_label_changed)
        self._icon_edit.textChanged.connect(self._on_icon_changed)
        self._icon_browse_button.clicked.connect(self._on_browse_icon)
        self._color_button.clicked.connect(self._on_pick_color)
        self._color_clear_button.clicked.connect(self._on_clear_color)
        self._action_edit.textChanged.connect(self._on_action_changed)
        self._args_edit.textChanged.connect(self._on_args_changed)
        self._kwargs_edit.textChanged.connect(self._on_kwargs_changed)

        self._open_button.clicked.connect(self._on_open_clicked)
        self._save_button.clicked.connect(self._on_save_clicked)
        self._save_as_button.clicked.connect(self._on_save_as_clicked)
        self._close_button.clicked.connect(self.close)

    # ---------------------------------------------------------
    # ドラッグ移動・背景描画(タイトル部分のみドラッグ可能)
    # ---------------------------------------------------------
    def closeEvent(self, event):   # ← 追加
        if self._is_dirty and not self._closing_confirmed:
            reply = QMessageBox.question(
                self, u"未保存の変更",
                u"変更が保存されていません。保存してから閉じますか？",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save
            )

            if reply == QMessageBox.Cancel:
                event.ignore()
                return

            if reply == QMessageBox.Save:
                self._on_save_clicked()
                if self._is_dirty:
                    # 保存自体がキャンセルされた(名前を付けて保存でファイル未選択、等)場合は閉じない
                    event.ignore()
                    return

        self._closing_confirmed = True
        super(MenuConfigEditor, self).closeEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(self.BORDER_COLOR, 1))
        painter.setBrush(QBrush(self.BACKGROUND_COLOR))
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), self.CORNER_RADIUS, self.CORNER_RADIUS)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and event.pos().y() <= self.DRAG_HANDLE_HEIGHT + 16:
            self._is_dragging = True
            self._drag_start_global = self._get_event_global_pos(event)
            self._drag_start_window_pos = self.pos()
        super(MenuConfigEditor, self).mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._is_dragging and self._drag_start_global is not None:
            current_global = self._get_event_global_pos(event)
            delta = current_global - self._drag_start_global
            self.move(self._drag_start_window_pos + delta)
        super(MenuConfigEditor, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._is_dragging = False
        self._drag_start_global = None
        self._drag_start_window_pos = None
        super(MenuConfigEditor, self).mouseReleaseEvent(event)

    def _get_event_global_pos(self, event):
        if hasattr(event, "globalPosition"):
            point = event.globalPosition()
            return QPoint(int(point.x()), int(point.y()))
        return event.globalPos()

    # ---------------------------------------------------------
    # ファイル操作
    # ---------------------------------------------------------

    def _new_document(self):
        self._root_data = {
            "settings": {},
            "profiles": [
                {"id": "default", "label": "Default", "icon": None, "color": None, "items": []}
            ]
        }
        self._current_path = None
        self._path_label.setText(u"(未保存)")
        self._rebuild_tree()

    def _load_from_path(self, path):
        try:
            with open(path, "r") as f:
                data = json.load(f)
        except (IOError, ValueError) as e:
            QMessageBox.warning(self, u"読み込みエラー", u"JSONの読み込みに失敗しました:\n{0}".format(e))
            return

        data.setdefault("settings", {})
        data.setdefault("profiles", [])
        self._root_data = data
        self._current_path = path
        self._path_label.setText(path)
        self._rebuild_tree()

    def _on_open_clicked(self):
        path, _ = QFileDialog.getOpenFileName(self, u"メニュー構成を開く", "", "JSON Files (*.json)")
        if not path:
            return
        self._load_from_path(path)

    def _on_save_clicked(self):
        if self._current_path is None:
            self._on_save_as_clicked()
            return
        self._save_to_path(self._current_path)

    def _on_save_as_clicked(self):
        path, _ = QFileDialog.getSaveFileName(self, u"名前を付けて保存", "", "JSON Files (*.json)")
        if not path:
            return
        if not path.lower().endswith(".json"):
            path += ".json"
        self._save_to_path(path)

    def _save_to_path(self, path):
        try:
            with open(path, "w") as f:
                json.dump(self._root_data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            QMessageBox.warning(self, u"保存エラー", u"保存に失敗しました:\n{0}".format(e))
            return

        self._current_path = path
        self._path_label.setText(path)
        self._is_dirty = False   # ← 追加
        self._update_title()   # ← 追加
        self.savedToPath.emit(path)   # ← 追加

    # ---------------------------------------------------------
    # ツリー構築
    # ---------------------------------------------------------

    def _rebuild_tree(self):
        self._tree.blockSignals(True)
        self._tree.clear()

        profiles = self._root_data.setdefault("profiles", [])
        for profile in profiles:
            profile_item = self._create_tree_item(_Node("profile", profile, profiles))
            self._tree.addTopLevelItem(profile_item)
            self._add_child_items(profile_item, profile.setdefault("items", []))

        self._tree.expandAll()
        self._tree.blockSignals(False)

        self._current_node = None
        self._form_widget.setEnabled(False)

    def _add_child_items(self, parent_tree_item, items_list):
        for item_data in items_list:
            tree_item = self._create_tree_item(_Node("item", item_data, items_list))
            parent_tree_item.addChild(tree_item)
            self._add_child_items(tree_item, item_data.setdefault("submenu", []))

    def _create_tree_item(self, node):
        text = node.data.get("label") or node.data.get("id") or u"(no id)"
        tree_item = QTreeWidgetItem([text])
        tree_item.setData(0, Qt.UserRole, node)
        return tree_item

    def _refresh_tree_item_text(self, tree_item, node):
        text = node.data.get("label") or node.data.get("id") or u"(no id)"
        tree_item.setText(0, text)

    # ---------------------------------------------------------
    # ツリー選択 → フォームへの反映
    # ---------------------------------------------------------

    def _on_tree_selection_changed(self, current, previous):
        if current is None:
            self._current_node = None
            self._form_widget.setEnabled(False)
            return

        node = current.data(0, Qt.UserRole)
        self._current_node = node
        self._form_widget.setEnabled(True)

        is_item = (node.kind == "item")
        self._action_edit.setEnabled(is_item)
        self._args_edit.setEnabled(is_item)
        self._kwargs_edit.setEnabled(is_item)

        self._updating_form = True
        try:
            self._id_edit.setText(node.data.get("id") or "")
            self._label_edit.setText(node.data.get("label") or "")
            self._icon_edit.setText(node.data.get("icon") or "")
            self._update_color_swatch(node.data.get("color"))

            if is_item:
                self._action_edit.setText(node.data.get("action") or "")
                self._args_edit.setText(json.dumps(node.data.get("args", [])))
                self._kwargs_edit.setText(json.dumps(node.data.get("kwargs", {})))
                self._set_line_edit_valid(self._args_edit, True)
                self._set_line_edit_valid(self._kwargs_edit, True)
            else:
                self._action_edit.setText("")
                self._args_edit.setText("")
                self._kwargs_edit.setText("")
        finally:
            self._updating_form = False

    def _update_color_swatch(self, hex_color):
        if hex_color:
            self._color_swatch.setStyleSheet(
                "background-color: {0}; border: 1px solid rgba(255,255,255,60); border-radius: 3px;".format(hex_color)
            )
        else:
            self._color_swatch.setStyleSheet(
                "background-color: transparent; border: 1px dashed rgba(255,255,255,80); border-radius: 3px;"
            )

    # ---------------------------------------------------------
    # フォーム → データへの反映
    # ---------------------------------------------------------

    def _current_tree_item(self):
        return self._tree.currentItem()

    def _on_id_changed(self, text):
        if self._updating_form or self._current_node is None:
            return
        self._current_node.data["id"] = text
        self._refresh_tree_item_text(self._current_tree_item(), self._current_node)
        self._mark_dirty()

    def _on_label_changed(self, text):
        if self._updating_form or self._current_node is None:
            return
        self._current_node.data["label"] = text
        self._refresh_tree_item_text(self._current_tree_item(), self._current_node)
        self._mark_dirty()

    def _on_icon_changed(self, text):
        if self._updating_form or self._current_node is None:
            return
        self._current_node.data["icon"] = text or None
        self._mark_dirty()

    def _on_browse_icon(self):
        if self._current_node is None:
            return
        path, _ = QFileDialog.getOpenFileName(
            self, u"アイコンを選択", "", "Images (*.png *.jpg *.jpeg *.svg *.bmp)"
        )
        if not path:
            return
        self._icon_edit.setText(path)   # textChangedで_on_icon_changedが呼ばれ、データに反映される

    def _on_pick_color(self):
        if self._current_node is None:
            return
        current = QColor(self._current_node.data.get("color") or "#FFFFFF")
        color = QColorDialog.getColor(current, self, u"色を選択")
        if not color.isValid():
            return
        self._current_node.data["color"] = color.name()
        self._update_color_swatch(color.name())
        self._mark_dirty()

    def _on_clear_color(self):
        if self._current_node is None:
            return
        self._current_node.data["color"] = None
        self._update_color_swatch(None)
        self._mark_dirty()

    def _on_action_changed(self, text):
        if self._updating_form or self._current_node is None:
            return
        self._current_node.data["action"] = text or None
        self._mark_dirty()

    def _on_args_changed(self, text):
        if self._updating_form or self._current_node is None:
            return
        self._validate_and_apply_json(self._args_edit, text, "args", list, [])

    def _on_kwargs_changed(self, text):
        if self._updating_form or self._current_node is None:
            return
        self._validate_and_apply_json(self._kwargs_edit, text, "kwargs", dict, {})

    def _validate_and_apply_json(self, line_edit, text, key, expected_type, empty_value):
        stripped = text.strip()
        if not stripped:
            self._current_node.data[key] = empty_value
            self._set_line_edit_valid(line_edit, True)
            self._mark_dirty()
            return

        try:
            parsed = json.loads(stripped)
        except ValueError:
            self._set_line_edit_valid(line_edit, False)
            return

        if not isinstance(parsed, expected_type):
            self._set_line_edit_valid(line_edit, False)
            return

        self._current_node.data[key] = parsed
        self._set_line_edit_valid(line_edit, True)
        self._mark_dirty()

    def _set_line_edit_valid(self, line_edit, is_valid):
        if is_valid:
            line_edit.setStyleSheet("")
        else:
            line_edit.setStyleSheet("color: {0};".format(self.INVALID_TEXT_COLOR))

    # ---------------------------------------------------------
    # ツリーの追加・削除・並び替え
    # ---------------------------------------------------------

    def _next_new_id(self, prefix):
        self._new_item_counter += 1
        return u"{0}_{1}".format(prefix, self._new_item_counter)

    def _on_add_profile(self):
        new_id = self._next_new_id("profile")
        new_profile = {"id": new_id, "label": u"New Profile", "icon": None, "color": None, "items": []}

        profiles = self._root_data.setdefault("profiles", [])
        profiles.append(new_profile)

        tree_item = self._create_tree_item(_Node("profile", new_profile, profiles))
        self._tree.addTopLevelItem(tree_item)
        self._tree.setCurrentItem(tree_item)
        self._mark_dirty()

    def _on_add_item(self):
        current_tree_item = self._current_tree_item()
        if current_tree_item is None:
            QMessageBox.information(self, u"項目の追加", u"先に親となるProfileまたは項目を選択してください。")
            return

        node = current_tree_item.data(0, Qt.UserRole)
        new_id = self._next_new_id("item")
        new_item = {
            "id": new_id, "label": u"New Item", "icon": None, "color": None,
            "action": None, "args": [], "kwargs": {}, "submenu": []
        }

        if node.kind == "profile":
            items_list = node.data.setdefault("items", [])
        else:
            items_list = node.data.setdefault("submenu", [])

        items_list.append(new_item)

        new_tree_item = self._create_tree_item(_Node("item", new_item, items_list))
        current_tree_item.addChild(new_tree_item)
        current_tree_item.setExpanded(True)
        self._tree.setCurrentItem(new_tree_item)
        self._mark_dirty()

    def _on_delete_selected(self):
        current_tree_item = self._current_tree_item()
        if current_tree_item is None:
            return

        node = current_tree_item.data(0, Qt.UserRole)

        reply = QMessageBox.question(
            self, u"削除の確認",
            u"「{0}」を削除しますか？ 子項目も含めて全て削除されます。".format(
                node.data.get("label") or node.data.get("id")
            ),
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        node.siblings.remove(node.data)

        parent_tree_item = current_tree_item.parent()
        if parent_tree_item is None:
            index = self._tree.indexOfTopLevelItem(current_tree_item)
            self._tree.takeTopLevelItem(index)
        else:
            parent_tree_item.removeChild(current_tree_item)
        self._mark_dirty()

    def _on_move_selected(self, direction):
        current_tree_item = self._current_tree_item()
        if current_tree_item is None:
            return

        node = current_tree_item.data(0, Qt.UserRole)
        siblings = node.siblings
        index = siblings.index(node.data)
        new_index = index + direction

        if not (0 <= new_index < len(siblings)):
            return

        siblings[index], siblings[new_index] = siblings[new_index], siblings[index]
        self._rebuild_tree_preserving_selection(node.data)
        self._mark_dirty()

    def _rebuild_tree_preserving_selection(self, data_to_reselect):
        self._rebuild_tree()
        self._select_node_by_data(data_to_reselect)

    def _select_node_by_data(self, data_ref):
        iterator = QTreeWidgetItemIterator(self._tree)
        while iterator.value():
            tree_item = iterator.value()
            node = tree_item.data(0, Qt.UserRole)
            if node.data is data_ref:
                self._tree.setCurrentItem(tree_item)
                return
            iterator += 1

    def _mark_dirty(self):   # ← 追加
        self._is_dirty = True
        self._update_title()

    def _update_title(self):   # ← 追加
        # タイトルラベル自体は_build_ui内のローカル変数なので、インスタンス変数に昇格させて参照できるようにする
        suffix = u" *" if self._is_dirty else u""
        self._title_label.setText(u"メニュー構成エディタ{0}".format(suffix))