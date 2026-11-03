# -*- coding: utf-8 -*-

try:
    from PySide6.QtCore import *
except ImportError:
    from PySide2.QtCore import *

from ..core import registry
from ..ui.widgets import sub_menu_panel


__all__ = ["LauncherController"]


class LauncherController(QObject):

    layoutInvalidated = Signal()
    submenuOpened      = Signal(object, object)
    submenuClosing      = Signal(object, object)
    rowContextMenuRequested = Signal(object, object) 

    def __init__(self, window, menu_area, top_level_items,
                submenu_viewport_size=None, submenu_direction="right",
                close_all_after_marking=False, spacing=None, inertia_enabled=True,
                row_scale=1.0, breadcrumb_collapse_enabled=True, parent=None):
        super(LauncherController, self).__init__(parent)
        self._window = window
        self._menu_area = menu_area
        self._stack = []
        self._item_map = {}   # owner(widget) -> MenuItem
        self._depth_map = {}
        self._submenu_viewport_size = submenu_viewport_size
        self._submenu_direction = submenu_direction
        self._close_all_after_marking = close_all_after_marking
        self._spacing = spacing   # ← 追加
        self._inertia_enabled = inertia_enabled   # ← 追加
        self._row_scale = row_scale
        self._breadcrumb_collapse_enabled = breadcrumb_collapse_enabled

        self._marking_active = False        # ← 追加
        self._marking_hover_state = (None, None)

        self._menu_area.scrollOffsetChanged.connect(self._on_menu_scrolled)

        buttons = self._menu_area.items()
        for button, item in zip(buttons, top_level_items):
            button.setHasSubmenu(item.hasSubmenu())
            button.setSubmenuDirection(self._submenu_direction)
            self._register_owner(button, depth=0, item=item)

    def setSubmenuViewportSize(self, size):
        self._submenu_viewport_size = size
        for entry in self._stack:
            entry["panel"].setViewportSize(size)
        self.layoutInvalidated.emit()

    def setSubmenuDirection(self, direction):
        self._submenu_direction = direction
        for owner in self._item_map.keys():
            owner.setSubmenuDirection(direction)

    def setCloseAllAfterMarking(self, enabled):   # ← 追加
        self._close_all_after_marking = enabled

    def setSpacing(self, spacing):   # ← 追加
        self._spacing = spacing
        self._menu_area.setSpacing(spacing)
        for entry in self._stack:
            entry["panel"].setSpacing(spacing)
        self.layoutInvalidated.emit()

    def setInertiaEnabled(self, enabled):   # ← 追加
        self._inertia_enabled = enabled
        self._menu_area.setInertiaEnabled(enabled)
        for entry in self._stack:
            entry["panel"].setInertiaEnabled(enabled)

    def setRowScale(self, scale):   # ← 追加
        """次に開くサブメニューから適用される倍率を変更する。
        既に開いているサブメニューは対象外のため、呼び出し側で
        closeAll()してから使うことを想定している"""
        self._row_scale = scale

    def setBreadcrumbCollapseEnabled(self, enabled):   # ← 追加
        self._breadcrumb_collapse_enabled = enabled
        self._update_panel_collapse_states()

    def submenuStack(self):
        return list(self._stack)

    def closeAll(self):
        self._close_stack_from(0)
        self.layoutInvalidated.emit()

    def rebuild(self, top_level_items):
        self.closeAll()
        self._item_map = {}
        self._depth_map = {}

        buttons = self._menu_area.items()
        for button, item in zip(buttons, top_level_items):
            button.setHasSubmenu(item.hasSubmenu())
            button.setSubmenuDirection(self._submenu_direction)
            self._register_owner(button, depth=0, item=item)

    def capturePath(self):   # ← 追加
        """現在開いている階層を、MenuItemのitem_idの並びとして記録する。
        ボタン/行のWidgetインスタンス自体は作り直されてしまうため、
        Widgetではなく不変のitem_idで経路を表現する"""
        path = []
        for entry in self._stack:
            item = self._item_map.get(entry["owner"])
            if item is None:
                break
            path.append(item.item_id)
        return path

    def reopenPath(self, path):   # ← 追加
        """capturePath()で記録した経路を、現在のowner群から辿って再度開く。
        途中でitem_idが見つからない(項目が削除された等)場合は、そこで打ち切る"""
        if not path:
            return

        candidates = self._menu_area.items()
        depth = 0

        for item_id in path:
            owner = None
            for candidate in candidates:
                item = self._item_map.get(candidate)
                if item is not None and item.item_id == item_id:
                    owner = candidate
                    break

            if owner is None:
                break

            item = self._item_map.get(owner)
            if item is None or not item.hasSubmenu():
                break

            owner.setActive(True)
            self._activate_submenu(owner, depth, item)

            depth += 1
            candidates = self._stack[-1]["panel"].items()

    def _register_owner(self, owner, depth, item):
        self._item_map[owner] = item
        self._depth_map[owner] = depth
        owner.clicked.connect(
            lambda checked=False, o=owner, d=depth: self._on_owner_clicked(o, d)
        )
        owner.markingPressed.connect(lambda o=owner: self._on_marking_pressed(o))   # ← 追加
        owner.markingMoved.connect(self._on_marking_moved)   # ← 追加
        owner.markingReleased.connect(self._on_marking_released)   # ← 追加
        owner.hoverMoved.connect(self._on_hover_moved)

    def _on_menu_scrolled(self, offset):
        self._check_visibility(0, self._menu_area)

    def _on_panel_scrolled(self, panel_index, offset): 
        """深さpanel_indexにあるパネル自身がスクロールされた時、
        そのパネルの中で開いている子(深さpanel_index+1)の親ownerが
        まだ見えているか確認する"""
        if panel_index >= len(self._stack):
            return
        panel = self._stack[panel_index]["panel"]
        self._check_visibility(panel_index + 1, panel)

    def _check_visibility(self, depth, area):  
        """depth番目に開いている階層のownerが、areaの可視範囲内にまだ収まっているか判定する。
        収まっていなければ、depth番目より深い階層を全部閉じる"""
        if depth >= len(self._stack):
            return

        owner = self._stack[depth]["owner"]
        if not self._is_owner_visible_in_area(owner, area):
            self._close_stack_from(depth)
            self.layoutInvalidated.emit()

    def _is_owner_visible_in_area(self, owner, area): 
        item_rect = area.itemGeometryInArea(owner)
        viewport_rect = QRect(0, 0, area.width(), area.height())
        return viewport_rect.intersects(item_rect)

    def _on_owner_clicked(self, owner, depth):
        item = self._item_map.get(owner)

        if owner.isActive():
            self._activate_submenu(owner, depth, item)
        else:
            self._close_stack_from(depth)

        if item is not None and not item.hasSubmenu() and item.action:
            self._execute_action(item)

        self.layoutInvalidated.emit()

    def _execute_action(self, item):
        try:
            registry.call_action(item.action, *item.args, **item.kwargs)
        except registry.ActionResolveError as e:
            print(u"[ToolMenuLane] action '{0}' の解決に失敗しました: {1}".format(item.item_id, e))
        except Exception as e:
            print(u"[ToolMenuLane] action '{0}' の実行中にエラーが発生しました: {1}".format(item.item_id, e))

    def _activate_submenu(self, owner, depth, item):
        self._close_stack_from(depth)

        children = item.submenu if item else []
        if not children:
            return

        panel = sub_menu_panel.SubMenuPanel(
            viewport_size=self._submenu_viewport_size, spacing=self._spacing,
            row_scale=self._row_scale, parent=self._window
        )
        panel.setInertiaEnabled(self._inertia_enabled)
        panel.collapsedActivated.connect(self._on_panel_collapsed_activated)

        panel_index = len(self._stack)
        panel.scrollOffsetChanged.connect(
            lambda offset, idx=panel_index: self._on_panel_scrolled(idx, offset)
        )

        for child_item in children:
            row = panel.addRow(
                icon=child_item.icon, label=child_item.label,
                has_submenu=child_item.hasSubmenu(), color=child_item.color
            )
            row.setSubmenuDirection(self._submenu_direction)
            row.contextMenuRequested.connect(   # ← 追加
                lambda pos, it=child_item: self.rowContextMenuRequested.emit(it, pos)
            )
            self._register_owner(row, depth + 1, child_item)

        panel.setVisible(True)
        self._stack.append({"owner": owner, "panel": panel})
        self.submenuOpened.emit(owner, panel)
        self._update_panel_collapse_states()
        
    def _close_stack_from(self, depth):
        while len(self._stack) > depth:
            entry = self._stack.pop()
            self.submenuClosing.emit(entry["owner"], entry["panel"]) 
            entry["panel"].setVisible(False)
            self._remove_panel_owners(entry["panel"])
            entry["panel"].deleteLater()
            if entry["owner"].isActive():
                entry["owner"].setActive(False)
        self._update_panel_collapse_states()

    def _remove_panel_owners(self, panel):
        """畳んだpanel配下のSubMenuRow(将来削除される予定のWidget)を、
        _item_mapから確実に取り除く。多階層の子孫も含めて再帰的に辿る必要はなく、
        畳む処理自体がstackを深い方から順にpopしていくため、
        このpanel直属の行だけ取り除けば十分"""
        for row in panel.items():
            self._item_map.pop(row, None)
            self._depth_map.pop(row, None)

    def _on_panel_collapsed_activated(self, panel):
        """折りたたまれた帯がクリックされた時、そのパネルより深い階層を全部閉じ、
        クリックされたパネル自身を最深部(展開状態)に戻す"""
        for i, entry in enumerate(self._stack):
            if entry["panel"] is panel:
                self._close_stack_from(i + 1)
                self.layoutInvalidated.emit()
                break

    def _update_panel_collapse_states(self):
        """スタックの中で一番深い(最後に開いた)パネルだけを展開状態にし、
        それより浅い階層は全て帯だけに折りたたむ"""
        last_index = len(self._stack) - 1
        for i, entry in enumerate(self._stack):
            entry["panel"].setCollapsed(i != last_index)

    def _on_marking_pressed(self, owner):
        self._marking_active = True
        self._marking_hover_state = (None, None)
        self._marking_set_hover(owner, "forward")

    def _on_marking_moved(self, global_pos):
        if not self._marking_active:
            return
        hit, zone = self._hit_test_owner(global_pos)   # ← 変更
        self._marking_set_hover(hit, zone)   # ← 変更
        self._update_auto_scroll(global_pos)

    def _on_marking_released(self, global_pos):
        if not self._marking_active:
            return

        hit, zone = self._hit_test_owner(global_pos)
        self._marking_set_hover(None, None)
        self._marking_active = False
        self._menu_area.setAutoScrollTarget(None)
        for entry in self._stack:
            entry["panel"].setAutoScrollTarget(None)

        if hit is not None and zone == "forward":
            item = self._item_map.get(hit)
            if item is not None and not item.hasSubmenu() and item.action:
                self._execute_action(item)
                if self._close_all_after_marking:   # ← 追加
                    self.closeAll()   # ← 追加。実行後、設定が有効なら全部閉じる
                    return   # ← 追加。closeAll内でlayoutInvalidatedが発行されるため、下の重複呼び出しを避ける

        self.layoutInvalidated.emit()

    def _hit_test_owner(self, global_pos):
        for owner in self._item_map.keys():
            local = owner.mapFromGlobal(global_pos)
            if not owner.rect().contains(local):
                continue
            if not owner.visibleRegion().contains(local):
                continue

            zone = owner.hitTest(local)   # ← 変更。bool判定から文字列判定へ
            if zone is not None:
                return owner, zone   # ← 変更。ownerと合わせて、どちらの判定領域かも返す

        return None, None   # ← 変更

    def _marking_set_hover(self, new_owner, zone):
        new_state = (new_owner, zone)
        if new_state == self._marking_hover_state:   # ← 変更。owner+zoneのペアで比較
            return

        prev_owner, _ = self._marking_hover_state
        if prev_owner is not None and prev_owner is not new_owner:
            prev_owner.setMarkingZone(None)   # ← 変更

        self._marking_hover_state = new_state

        if new_owner is None:
            return

        new_owner.setMarkingZone(zone)   # ← 変更

        item = self._item_map.get(new_owner)
        depth = self._depth_map.get(new_owner, 0)
        if item is None:
            return

        if zone == "back":
            self._close_stack_from(depth)   # ← 変更。depth+1からdepthへ。このownerが開いたパネル自体を閉じる
        elif item.hasSubmenu():
            if new_owner.isActive():
                self._close_stack_from(depth + 1)   # 既に開いている祖先への再訪問。孫だけ畳む(据え置き)
            else:
                new_owner.setActive(True)
                self._activate_submenu(new_owner, depth, item)
        else:
            self._close_stack_from(depth)

        self.layoutInvalidated.emit()

    def _update_auto_scroll(self, global_pos):   # ← 追加
        """マーキングドラッグ中、カーソルがメインメニュー/各サブメニューパネルの
        どのエリアの範囲内にいるかを判定し、そのエリアだけオートスクロール判定を行う。
        範囲外のエリアは念のため停止しておく"""
        areas = [self._menu_area] + [entry["panel"] for entry in self._stack]

        for area in areas:
            local = area.mapFromGlobal(global_pos)
            if area.rect().contains(local):
                area.setAutoScrollTarget(global_pos)
            else:
                area.setAutoScrollTarget(None)

    def _update_panel_collapse_states(self):
        if not self._breadcrumb_collapse_enabled:   # ← 追加。無効時は常に全展開
            for entry in self._stack:
                entry["panel"].setCollapsed(False)
            return

        last_index = len(self._stack) - 1
        for i, entry in enumerate(self._stack):
            entry["panel"].setCollapsed(i != last_index)

    def _on_hover_moved(self, global_pos):   # ← 追加
        """マーキングドラッグ中でなくても、通常のホバーでオートスクロールを機能させる。
        ドラッグ中は_on_marking_moved側で既に呼ばれているため、ここでは
        ドラッグ中でない場合だけ処理する(二重駆動を避ける)"""
        if self._marking_active:
            return

        if global_pos is None:
            self._menu_area.setAutoScrollTarget(None)
            for entry in self._stack:
                entry["panel"].setAutoScrollTarget(None)
            return

        self._update_auto_scroll(global_pos)