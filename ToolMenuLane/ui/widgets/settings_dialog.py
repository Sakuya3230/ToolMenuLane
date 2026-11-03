# -*- coding: utf-8 -*-

try:
    from PySide6.QtWidgets import *
    from PySide6.QtGui import *
    from PySide6.QtCore import *
except ImportError:
    from PySide2.QtWidgets import *
    from PySide2.QtGui import *
    from PySide2.QtCore import *


__all__ = ["SettingsDialog"]


class SettingsDialog(QDialog):

    CORNER_RADIUS   = 14
    BACKGROUND_COLOR = QColor(30, 30, 30, 235)
    BORDER_COLOR       = QColor(255, 255, 255, 30)
    TITLE_COLOR           = QColor(230, 230, 230)
    DRAG_HANDLE_HEIGHT      = 34

    def __init__(self, settings_manager, parent=None):
        super(SettingsDialog, self).__init__(parent)
        self.setWindowTitle(u"ToolMenuLane 設定")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)   # ← 追加
        self.setAttribute(Qt.WA_TranslucentBackground)    

        self._settings = settings_manager
        self._resolved = False

        self._is_dragging = False   # ← 追加
        self._drag_start_global = None   # ← 追加
        self._drag_start_window_pos = None   # ← 追加

        self._settings.beginEdit()

        self._build_ui()
        self._load_current_values()
        self._connect_widget_signals()

    def paintEvent(self, event):   # ← 追加。角丸+半透明の背景を自前描画
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.setPen(QPen(self.BORDER_COLOR, 1))
        painter.setBrush(QBrush(self.BACKGROUND_COLOR))
        painter.drawRoundedRect(
            self.rect().adjusted(0, 0, -1, -1), self.CORNER_RADIUS, self.CORNER_RADIUS
        )

    def mousePressEvent(self, event):   # ← 追加。ドラッグ移動
        if event.button() == Qt.LeftButton and event.pos().y() <= self.DRAG_HANDLE_HEIGHT + 16:
            self._is_dragging = True
            self._drag_start_global = self._get_event_global_pos(event)
            self._drag_start_window_pos = self.pos()
        super(SettingsDialog, self).mousePressEvent(event)

    def mouseMoveEvent(self, event):   # ← 追加
        if self._is_dragging and self._drag_start_global is not None:
            current_global = self._get_event_global_pos(event)
            delta = current_global - self._drag_start_global
            self.move(self._drag_start_window_pos + delta)
        super(SettingsDialog, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):   # ← 追加
        self._is_dragging = False
        self._drag_start_global = None
        self._drag_start_window_pos = None
        super(SettingsDialog, self).mouseReleaseEvent(event)

    def _get_event_global_pos(self, event):   # ← 追加
        if hasattr(event, "globalPosition"):
            point = event.globalPosition()
            return QPoint(int(point.x()), int(point.y()))
        return event.globalPos()

    def _build_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        self._background = QWidget(self)
        outer_layout.addWidget(self._background)

        content_layout = QVBoxLayout(self._background)
        content_layout.setContentsMargins(16, 16, 16, 16)

        title_label = QLabel(u"ToolMenuLane 設定")
        title_label.setFixedHeight(self.DRAG_HANDLE_HEIGHT)
        title_label.setStyleSheet(
            "color: rgba({0},{1},{2},255); font-weight: bold; background: transparent;".format(
                self.TITLE_COLOR.red(), self.TITLE_COLOR.green(), self.TITLE_COLOR.blue()
            )
        )
        content_layout.addWidget(title_label)

        form = QFormLayout()
        content_layout.addLayout(form)

        self._orientation_combo = QComboBox()
        self._orientation_combo.addItem(u"縦", "vertical")
        self._orientation_combo.addItem(u"横", "horizontal")
        form.addRow(u"メインメニューの向き", self._orientation_combo)

        self._direction_combo = QComboBox()
        self._direction_combo.addItem(u"右", "right")
        self._direction_combo.addItem(u"左", "left")
        form.addRow(u"サブメニュー展開方向", self._direction_combo)

        self._main_size_spin = QSpinBox()
        self._main_size_spin.setRange(50, 2000)
        self._main_size_spin.setSingleStep(10)
        form.addRow(u"メインメニューの長さ", self._main_size_spin)

        self._submenu_size_spin = QSpinBox()
        self._submenu_size_spin.setRange(50, 2000)
        self._submenu_size_spin.setSingleStep(10)
        form.addRow(u"サブメニューの長さ", self._submenu_size_spin)

        self._spacing_spin = QSpinBox()
        self._spacing_spin.setRange(0, 100)
        self._spacing_spin.setSingleStep(2)
        form.addRow(u"アイテムの間隔", self._spacing_spin)

        self._opacity_spin = QDoubleSpinBox()
        self._opacity_spin.setRange(0.2, 1.0)
        self._opacity_spin.setSingleStep(0.05)
        self._opacity_spin.setDecimals(2)
        form.addRow(u"透明度", self._opacity_spin)

        # ---- サイズ関連 (ここから追加) ----
        self._global_scale_spin = QDoubleSpinBox()   # ← 追加
        self._global_scale_spin.setRange(0.6, 1.6)
        self._global_scale_spin.setSingleStep(0.05)
        self._global_scale_spin.setDecimals(2)
        form.addRow(u"全体サイズ", self._global_scale_spin)

        main_scale_row = QHBoxLayout()   # ← 追加
        self._main_scale_override_check = QCheckBox(u"個別指定")
        self._main_scale_spin = QDoubleSpinBox()
        self._main_scale_spin.setRange(0.6, 1.6)
        self._main_scale_spin.setSingleStep(0.05)
        self._main_scale_spin.setDecimals(2)
        main_scale_row.addWidget(self._main_scale_override_check)
        main_scale_row.addWidget(self._main_scale_spin)
        form.addRow(u"メインメニューのサイズ", main_scale_row)

        submenu_scale_row = QHBoxLayout()   # ← 追加
        self._submenu_scale_override_check = QCheckBox(u"個別指定")
        self._submenu_scale_spin = QDoubleSpinBox()
        self._submenu_scale_spin.setRange(0.6, 1.6)
        self._submenu_scale_spin.setSingleStep(0.05)
        self._submenu_scale_spin.setDecimals(2)
        submenu_scale_row.addWidget(self._submenu_scale_override_check)
        submenu_scale_row.addWidget(self._submenu_scale_spin)
        form.addRow(u"サブメニューのサイズ", submenu_scale_row)

        accent_row = QHBoxLayout()   # ← 追加
        self._accent_color_swatch = QLabel()   # ← 追加
        self._accent_color_swatch.setFixedSize(24, 24)   # ← 追加
        self._accent_color_button = QPushButton(u"色を選択...")   # ← 追加
        accent_row.addWidget(self._accent_color_swatch)   # ← 追加
        accent_row.addWidget(self._accent_color_button)   # ← 追加
        form.addRow(u"アクセントカラー", accent_row)   # ← 追加

        base_row = QHBoxLayout()   # ← 追加
        self._base_color_swatch = QLabel()   # ← 追加
        self._base_color_swatch.setFixedSize(24, 24)   # ← 追加
        self._base_color_button = QPushButton(u"色を選択...")   # ← 追加
        base_row.addWidget(self._base_color_swatch)   # ← 追加
        base_row.addWidget(self._base_color_button)   # ← 追加
        form.addRow(u"背景の基本色", base_row)   # ← 追加

        self._close_after_marking_check = QCheckBox(u"ドラッグ操作後に自動で閉じる")
        form.addRow(u"", self._close_after_marking_check)

        self._inertia_check = QCheckBox(u"慣性スクロールを有効にする")
        form.addRow(u"", self._inertia_check)

        self._breadcrumb_check = QCheckBox(u"サブメニューをコンパクトに折りたたむ")   # ← 追加
        form.addRow(u"", self._breadcrumb_check)   # ← 追加

        button_row = QHBoxLayout()
        self._reset_button = QPushButton(u"初期化")
        button_row.addWidget(self._reset_button)
        button_row.addStretch()
        self._apply_button = QPushButton(u"Apply")
        self._cancel_button = QPushButton(u"Cancel")
        button_row.addWidget(self._apply_button)
        button_row.addWidget(self._cancel_button)
        content_layout.addLayout(button_row)

        self._reset_button.clicked.connect(self._on_reset)
        self._apply_button.clicked.connect(self._on_apply)
        self._cancel_button.clicked.connect(self._on_cancel)

    def _load_current_values(self):
        self._set_combo_value(self._orientation_combo, self._settings.get("orientation", "vertical"))
        self._set_combo_value(self._direction_combo, self._settings.get("submenu_direction", "right"))
        self._main_size_spin.setValue(self._settings.get("main_viewport_size", 220))
        self._submenu_size_spin.setValue(self._settings.get("submenu_viewport_size", 240))
        self._spacing_spin.setValue(self._settings.get("spacing", 8))
        self._opacity_spin.setValue(self._settings.get("opacity", 1.0))
        self._close_after_marking_check.setChecked(self._settings.get("close_all_after_marking", False))
        self._inertia_check.setChecked(self._settings.get("inertia_scroll_enabled", True))

        global_scale = self._settings.get("global_scale", 1.0)   # ← 追加
        self._global_scale_spin.setValue(global_scale)   # ← 追加

        self._load_scale_override(   # ← 追加
            self._main_scale_override_check, self._main_scale_spin, "main_scale", global_scale
        )
        self._load_scale_override(   # ← 追加
            self._submenu_scale_override_check, self._submenu_scale_spin, "submenu_scale", global_scale
        )
        self._update_accent_swatch(self._settings.get("accent_color", "#FFD700"))
        self._update_base_swatch(self._settings.get("base_color", "#FFFFFF"))   # ← 追加
        self._breadcrumb_check.setChecked(self._settings.get("breadcrumb_collapse_enabled", True))

    def _update_accent_swatch(self, hex_color):   # ← 追加
        self._accent_color_swatch.setStyleSheet(
            "background-color: {0}; border: 1px solid rgba(255,255,255,60); border-radius: 3px;".format(hex_color)
        )

    def _update_base_swatch(self, hex_color):   # ← 追加
        self._base_color_swatch.setStyleSheet(
            "background-color: {0}; border: 1px solid rgba(255,255,255,60); border-radius: 3px;".format(hex_color)
        )

    def _load_scale_override(self, check, spin, key, global_scale):   # ← 追加
        """個別設定は、値がglobal_scaleと異なる場合にのみ「個別指定」として扱う。
        この方式により、既存のJSON設定(常に数値が入っている)ともそのまま互換性がある"""
        value = self._settings.get(key, global_scale)
        is_override = (value != global_scale)
        check.setChecked(is_override)
        spin.setValue(value if is_override else global_scale)
        spin.setEnabled(is_override)



    def _set_combo_value(self, combo, value):
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _connect_widget_signals(self):
        self._orientation_combo.currentIndexChanged.connect(self._on_orientation_changed)
        self._direction_combo.currentIndexChanged.connect(self._on_direction_changed)
        self._main_size_spin.valueChanged.connect(lambda v: self._settings.setValue("main_viewport_size", v))
        self._submenu_size_spin.valueChanged.connect(lambda v: self._settings.setValue("submenu_viewport_size", v))
        self._spacing_spin.valueChanged.connect(lambda v: self._settings.setValue("spacing", v))
        self._opacity_spin.valueChanged.connect(lambda v: self._settings.setValue("opacity", v))
        self._close_after_marking_check.toggled.connect(
            lambda v: self._settings.setValue("close_all_after_marking", v)
        )
        self._inertia_check.toggled.connect(
            lambda v: self._settings.setValue("inertia_scroll_enabled", v)
        )

        self._global_scale_spin.valueChanged.connect(self._on_global_scale_changed)   # ← 追加
        self._main_scale_override_check.toggled.connect(   # ← 追加
            lambda checked: self._on_scale_override_toggled(
                checked, self._main_scale_spin, "main_scale"
            )
        )
        self._main_scale_spin.valueChanged.connect(   # ← 追加
            lambda v: self._on_scale_override_value_changed(v, self._main_scale_override_check, "main_scale")
        )
        self._submenu_scale_override_check.toggled.connect(   # ← 追加
            lambda checked: self._on_scale_override_toggled(
                checked, self._submenu_scale_spin, "submenu_scale"
            )
        )
        self._submenu_scale_spin.valueChanged.connect(   # ← 追加
            lambda v: self._on_scale_override_value_changed(v, self._submenu_scale_override_check, "submenu_scale")
        )
        self._accent_color_button.clicked.connect(self._on_pick_accent_color)
        self._base_color_button.clicked.connect(self._on_pick_base_color)
        self._breadcrumb_check.toggled.connect(   # ← 追加
            lambda v: self._settings.setValue("breadcrumb_collapse_enabled", v)
        )
        self._settings.valueChanged.connect(self._on_settings_value_changed)

    def _on_global_scale_changed(self, value):   # ← 追加
        self._settings.setValue("global_scale", value)

        # 「個別指定」していない項目は、global_scaleの変更にそのまま追従させる
        if not self._main_scale_override_check.isChecked():
            self._main_scale_spin.blockSignals(True)
            self._main_scale_spin.setValue(value)
            self._main_scale_spin.blockSignals(False)
            self._settings.setValue("main_scale", value)

        if not self._submenu_scale_override_check.isChecked():
            self._submenu_scale_spin.blockSignals(True)
            self._submenu_scale_spin.setValue(value)
            self._submenu_scale_spin.blockSignals(False)
            self._settings.setValue("submenu_scale", value)

    def _on_scale_override_toggled(self, checked, spin, key):   # ← 追加
        spin.setEnabled(checked)
        if checked:
            self._settings.setValue(key, spin.value())
        else:
            # 個別指定を外したら、即座にglobal_scaleへ合わせる
            global_value = self._global_scale_spin.value()
            spin.blockSignals(True)
            spin.setValue(global_value)
            spin.blockSignals(False)
            self._settings.setValue(key, global_value)

    def _on_scale_override_value_changed(self, value, check, key):   # ← 追加
        if check.isChecked():
            self._settings.setValue(key, value)

    def _on_pick_accent_color(self):   # ← 追加
        current = QColor(self._settings.get("accent_color", "#FFD700"))
        color = QColorDialog.getColor(current, self, u"アクセントカラーを選択")
        if not color.isValid():
            return
        self._settings.setValue("accent_color", color.name())

    def _on_pick_base_color(self):   # ← 追加
        current = QColor(self._settings.get("base_color", "#FFFFFF"))
        color = QColorDialog.getColor(current, self, u"背景の基本色を選択")
        if not color.isValid():
            return
        self._settings.setValue("base_color", color.name())

    def _on_settings_value_changed(self, key, value):
        widget_map = {
            "orientation": (self._orientation_combo, "combo"),
            "submenu_direction": (self._direction_combo, "combo"),
            "main_viewport_size": (self._main_size_spin, "spin"),
            "submenu_viewport_size": (self._submenu_size_spin, "spin"),
            "spacing": (self._spacing_spin, "spin"),
            "opacity": (self._opacity_spin, "spin"),
            "close_all_after_marking": (self._close_after_marking_check, "check"),
            "inertia_scroll_enabled": (self._inertia_check, "check"),
            "global_scale": (self._global_scale_spin, "spin"),
            "breadcrumb_collapse_enabled": (self._breadcrumb_check, "check"),   # ← 追加
        }
        
        if key == "accent_color":   # ← 追加。専用処理(スウォッチの更新)が必要なため別扱い
            self._update_accent_swatch(value)
            return
        if key == "base_color":   # ← 追加
            self._update_base_swatch(value)
            return

        entry = widget_map.get(key)
        if entry is None:
            return

        widget, kind = entry
        widget.blockSignals(True)
        try:
            if kind == "combo":
                self._set_combo_value(widget, value)
            elif kind == "spin":
                widget.setValue(value)
            elif kind == "check":
                widget.setChecked(value)
        finally:
            widget.blockSignals(False)

    def _on_orientation_changed(self, index):
        self._settings.setValue("orientation", self._orientation_combo.itemData(index))

    def _on_direction_changed(self, index):
        self._settings.setValue("submenu_direction", self._direction_combo.itemData(index))

    def _on_reset(self):
        self._settings.resetToDefaults()
        self._load_current_values()

    def _on_apply(self):
        self._resolved = True
        self._settings.apply()
        self.accept()

    def _on_cancel(self):
        self._resolved = True
        self._settings.cancel()
        self.reject()

    def closeEvent(self, event):
        # ×ボタン等、Apply/Cancel以外の方法で閉じられた場合もCancel扱いにする
        if not self._resolved:
            self._resolved = True
            self._settings.cancel()
        super(SettingsDialog, self).closeEvent(event)