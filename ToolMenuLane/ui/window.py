# -*- coding: utf-8 -*-

import os

import maya.cmds as cmds
import maya.OpenMayaUI as omui
import maya.api.OpenMaya as om2
import maya.api.OpenMayaUI as omui2

try:
    from PySide6.QtWidgets import *
    from PySide6.QtGui import *
    from PySide6.QtCore import *
    from shiboken6 import wrapInstance
except ImportError:
    from PySide2.QtWidgets import *
    from PySide2.QtGui import *
    from PySide2.QtCore import *
    from shiboken2 import wrapInstance

from .widgets import main_menu_area
from .widgets import home_button
from .widgets import sub_menu_panel
from .widgets import sub_menu_row
from ..controller import launcher_controller
from ..core import config as config_module
from ..controller import launcher_controller
from .widgets import indicator as indicator_module
from ..core import state as state_module
from .widgets import radial_menu as radial_menu_module
from .widgets import pointer_overlay as pointer_overlay_module
from .anim import stagger
from .widgets import settings_dialog
from ..controller import settings_manager as settings_manager_module
from ..core import models as models_module
from ..ui import theme
from ..controller import favorites_manager as favorites_manager_module
from .widgets import favorites_radial_menu as favorites_radial_menu_module
from .widgets import menu_config_editor

class ToolMenuLane(QWidget):

    TOOL_TITLE_NAME = "Tool Menu Lane"
    TOOL_OBJECT_NAME = "ToolMenuLane_MainWindow"

    MENU_SPACING = 8

    def __init__(self, parent=None):
        super(ToolMenuLane, self).__init__(parent)
        self.setWindowTitle(self.TOOL_TITLE_NAME)
        self.setObjectName(self.TOOL_OBJECT_NAME)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._config_path = os.path.join(   # ← 変更。ローカル変数からインスタンス変数へ
            os.path.dirname(__file__), "..", "resources", "default_config.json"
        )
        self._config = config_module.loadConfig(self._config_path)   # ← 変更
        self._current_profile_id = self._config.profiles[0].profile_id

        self._settings = settings_manager_module.SettingsManager(
            self._build_initial_settings(),
            defaults=self._build_default_settings()   # ← 追加
        )
        self._settings.valueChanged.connect(self._on_setting_changed)

        self._pending_submenu_reveal = None   # ← 追加
        self._active_anims = {}     

        self._setup_ui()
        self._apply_saved_state()
        self._connect_signals()
        self._relayout()

    def closeEvent(self, event):
        self._radial_menu.close()   # ← 追加
        self._favorites_radial_menu.close()   # ← 追加
        self._pointer_overlay.close()   # ← 追加
        
        state_module.saveState(self._current_state())
        QWidget.closeEvent(self, event)

    # ------------------------------
    # 
    # ------------------------------
    def _setup_ui(self):
        profile = self._config.profiles[0]
        self._submenu_direction = self._settings.get("submenu_direction")
        theme.Theme.setAccentColor(self._settings.get("accent_color", "#FFD700"))
        theme.Theme.setBaseColor(self._settings.get("base_color", "#FFFFFF"))

        global_scale = self._settings.clampScale(self._settings.get("global_scale", 1.0))
        self._home_button = home_button.HomeButton(
            icon=self._config.settings.home_icon, size_scale=global_scale, parent=self
        )
        self._home_button.setLabel(u"クリックでメニュー開閉 / 右クリックで設定")

        orientation = Qt.Horizontal if self._settings.get("orientation") == "horizontal" else Qt.Vertical
        main_scale = self._settings.effectiveMainScale()
        submenu_scale = self._settings.effectiveSubmenuScale()

        self._menu_area = main_menu_area.MainMenuArea(
            orientation=orientation,
            viewport_size=self._settings.get("main_viewport_size"),
            spacing=self._settings.get("spacing"),
            button_scale=main_scale,
            parent=self
        )
        self._menu_area.setInertiaEnabled(self._settings.get("inertia_scroll_enabled"))
        self._menu_area.setVisible(False)

        self._indicator = indicator_module.Indicator(
            orientation=orientation, dot_scale=main_scale, parent=self
        )
        self._indicator.setVisible(False)

        self._controller = launcher_controller.LauncherController(
            window=self,
            menu_area=self._menu_area,
            top_level_items=[],   # ← 変更。空で生成し、直後にrebuild経由でボタンごと構築する
            submenu_viewport_size=self._settings.get("submenu_viewport_size"),
            submenu_direction=self._submenu_direction,
            close_all_after_marking=self._settings.get("close_all_after_marking"),
            spacing=self._settings.get("spacing"),
            inertia_enabled=self._settings.get("inertia_scroll_enabled"),
            row_scale=submenu_scale,
            breadcrumb_collapse_enabled=self._settings.get("breadcrumb_collapse_enabled")
        )

        self._current_profile_items = profile.items
        self._rebuild_main_menu_buttons(profile.items)   # ← 変更。共通ヘルパー経由に統一(contextMenuRequestedもここで接続される)

        self._favorites = favorites_manager_module.FavoritesManager(parent=self)
        self._favorites_edit_mode = False   # ← 追加

        self._favorites_radial_menu = favorites_radial_menu_module.FavoritesRadialMenu(parent=self.parent())
        self._favorites_radial_menu.setVisible(False)

        self._radial_menu = radial_menu_module.RadialMenu(parent=self.parent())
        self._radial_menu.setVisible(False)

        self._pointer_overlay = pointer_overlay_module.PointerOverlay(parent=self.parent())

        self.setWindowOpacity(self._settings.get("opacity"))

    def _connect_signals(self):
        self._connect_home_signals()   # ← 変更。home関連の接続を専用メソッドに切り出し
        self._controller.layoutInvalidated.connect(self._relayout)
        self._controller.submenuOpened.connect(self._on_submenu_opened)
        self._controller.submenuClosing.connect(self._on_submenu_closing)
        self._controller.rowContextMenuRequested.connect(self._show_favorite_context_menu)
        self._menu_area.currentIndexChanged.connect(self._indicator.setCurrentIndex)
        self._favorites_radial_menu.reorderRequested.connect(self._on_favorites_reorder_requested)   # ← 追加
        self._favorites_radial_menu.removeRequested.connect(self._on_favorites_remove_requested) 

    def _connect_home_signals(self):   # ← 追加
        """Home関連のSignal接続。Homeボタンをsize_scale変更で作り直す際、
        新しいインスタンスに対して再接続するために独立したメソッドにしている"""
        self._home_button.toggled.connect(self._on_home_toggled)
        self._home_button.settingsRequested.connect(self._open_settings_dialog)
        self._home_button.menuConfigEditorRequested.connect(self._open_menu_config_editor)
        self._home_button.radialMenuOpened.connect(self._on_radial_menu_opened)
        self._home_button.radialMenuUpdated.connect(self._on_radial_menu_updated)
        self._home_button.radialMenuClosed.connect(self._on_radial_menu_closed)
        self._home_button.favoritesMenuOpened.connect(self._on_favorites_menu_opened)   # ← 追加
        self._home_button.favoritesMenuUpdated.connect(self._on_favorites_menu_updated)   # ← 追加
        self._home_button.favoritesMenuClosed.connect(self._on_favorites_menu_closed)   # ← 追加
        self._home_button.favoritesEditToggleRequested.connect(self._on_favorites_edit_toggle_requested) 

    def _on_home_toggled(self, is_expanded):
        if is_expanded:
            self._menu_area.setVisible(True)
            self._indicator.setVisible(True)
            self._relayout()
            self._start_menu_reveal_animation()
        else:
            self._stop_anim("menu")   # ← 追加。閉じる時も明示的に停止する
            self._controller.closeAll()
            self._menu_area.setVisible(False)
            self._indicator.setVisible(False)
            self._relayout()

    def _on_radial_menu_opened(self, click_point):
        self._radial_menu.setProfiles(self._config.profiles, self._current_profile_id)
        self._radial_menu.setHoverPoint(click_point)
        self._position_radial_menu()
        self._radial_menu.show()
        self._radial_menu.raise_()

        self._show_pointer_overlay()
        self._update_pointer_line(click_point, click_point)

    def _on_radial_menu_updated(self, click_point, current_point):
        self._radial_menu.setHoverPoint(current_point)
        self._update_pointer_line(click_point, current_point)

    def _on_radial_menu_closed(self, current_point):
        profile_id = self._radial_menu.sectorAt(current_point)

        self._radial_menu.setVisible(False)
        self._radial_menu.setHoverPoint(None)

        self._pointer_overlay.clearAndHide()   # ← setPointer(None,None) + setVisible(False) をまとめて置き換え

        if profile_id is not None:
            self._switch_profile(profile_id)
            self._relayout()

    def _on_submenu_opened(self, owner, panel):
        self._pending_submenu_reveal = (owner, panel)

    def _on_submenu_closing(self, owner, panel):   # ← 追加
        self._stop_anim(id(panel))

    def _on_setting_changed(self, key, value):
        if key == "orientation":
            orientation = Qt.Horizontal if value == "horizontal" else Qt.Vertical
            self._menu_area.setOrientation(orientation)
            self._indicator.setOrientation(orientation)
            self._relayout()
        elif key == "submenu_direction":
            self._submenu_direction = value
            self._controller.setSubmenuDirection(value)
            self._relayout()
        elif key == "main_viewport_size":
            self._menu_area.setViewportSize(value)
            self._relayout()
        elif key == "submenu_viewport_size":
            self._controller.setSubmenuViewportSize(value)
        elif key == "spacing":
            self._menu_area.setSpacing(value)
            self._controller.setSpacing(value)
            self._relayout()
        elif key == "opacity":
            self.setWindowOpacity(value)
        elif key == "close_all_after_marking":
            self._controller.setCloseAllAfterMarking(value)
        elif key == "inertia_scroll_enabled":
            self._menu_area.setInertiaEnabled(value)
            self._controller.setInertiaEnabled(value)
        elif key == "global_scale":   # ← 追加。Homeの再構築もここで行う
            self._apply_scale_settings()
            self._rebuild_home_button(self._settings.clampScale(value))
            self._relayout()
        elif key in ("main_scale", "submenu_scale"):   # ← 変更。global_scaleと分離
            self._apply_scale_settings()
        elif key == "accent_color":   # ← 追加
            theme.Theme.setAccentColor(value)
            self._repaint_all()   # ← 追加
        elif key == "base_color":   # ← 追加
            theme.Theme.setBaseColor(value)
            self._repaint_all()
        elif key == "breadcrumb_collapse_enabled":   # ← 追加
            self._controller.setBreadcrumbCollapseEnabled(value)
            self._relayout()

    def _relayout(self):
        self.setUpdatesEnabled(False)
        try:
            home_global = self.pos() + self._home_button.pos()

            home_rect = QRect(0, 0, self._home_button.width(), self._home_button.height())
            rects = {"home": home_rect}

            if self._menu_area.isVisible():
                rects["menu"] = self._desired_menu_area_rect(home_rect)
                rects["indicator"] = self._desired_indicator_rect(rects["menu"])

            submenu_rects = []
            stack = self._controller.submenuStack()

            if "menu" in rects:
                prev_area_rect = rects["menu"]
                prev_area_widget = self._menu_area
                for depth, entry in enumerate(stack):
                    rect = self._desired_submenu_rect(
                        prev_area_rect, prev_area_widget, entry["owner"], entry["panel"], depth
                    )
                    submenu_rects.append(rect)
                    prev_area_rect = rect
                    prev_area_widget = entry["panel"]

            all_rects = list(rects.values()) + submenu_rects

            min_x = min(r.x() for r in all_rects)
            min_y = min(r.y() for r in all_rects)
            max_x = max(r.x() + r.width() for r in all_rects)
            max_y = max(r.y() + r.height() for r in all_rects)

            offset = QPoint(-min_x, -min_y)
            new_size = QSize(max_x - min_x, max_y - min_y)

            home_new_local = home_rect.topLeft() + offset
            new_window_pos = home_global - home_new_local

            new_window_pos = self._clamp_window_pos(new_window_pos, new_size)   # ← 追加

            self._home_button.move(home_new_local)
            if "menu" in rects:
                self._menu_area.move(rects["menu"].topLeft() + offset)
            if "indicator" in rects:
                self._indicator.move(rects["indicator"].topLeft() + offset)
            for rect, entry in zip(submenu_rects, stack):
                entry["panel"].move(rect.topLeft() + offset)

            self.setGeometry(new_window_pos.x(), new_window_pos.y(), new_size.width(), new_size.height())
        finally:
            self.setUpdatesEnabled(True)

        if self._pending_submenu_reveal is not None:
            owner, panel = self._pending_submenu_reveal
            self._pending_submenu_reveal = None
            self._start_submenu_reveal_animation(owner, panel)

    def _clamp_window_pos(self, pos, size):   # ← 追加
        """ウィンドウ全体(Home+展開中のメニュー全て)が、Mayaメインウィンドウの
        可視範囲内に収まるよう、必要であればpos(左上座標)を補正する"""
        maya_main_window = self.parent()
        if maya_main_window is None:
            return pos

        bounds_top_left = maya_main_window.mapToGlobal(QPoint(0, 0))
        bounds_rect = QRect(bounds_top_left, maya_main_window.size())

        x = pos.x()
        y = pos.y()

        if size.width() <= bounds_rect.width():
            x = max(bounds_rect.left(), min(x, bounds_rect.right() - size.width()))
        if size.height() <= bounds_rect.height():
            y = max(bounds_rect.top(), min(y, bounds_rect.bottom() - size.height()))

        return QPoint(x, y)

    def _desired_radial_rect(self, home_rect):
        menu = self._radial_menu
        home_center = QPoint(
            home_rect.x() + home_rect.width() // 2,
            home_rect.y() + home_rect.height() // 2
        )
        offset = menu.centerOffset()
        return QRect(home_center.x() - offset.x(), home_center.y() - offset.y(), menu.width(), menu.height())
    
    def _desired_menu_area_rect(self, home_rect):
        area = self._menu_area
        if area.orientation() == Qt.Vertical:
            x = home_rect.x() + (home_rect.width() - area.width()) // 2
            y = home_rect.y() + home_rect.height() + self.MENU_SPACING
        else:
            x = home_rect.x() + home_rect.width() + self.MENU_SPACING
            y = home_rect.y() + (home_rect.height() - area.height()) // 2
        return QRect(x, y, area.width(), area.height())

    def _desired_submenu_rect(self, area_rect, area_widget, owner, panel, depth):
        owner_local = area_widget.itemGeometryInArea(owner)
        owner_rect = QRect(area_rect.topLeft() + owner_local.topLeft(), owner_local.size())

        first_row_height = panel.rowHeight()   # ← 変更。実際にスケールされた高さを使う
        use_horizontal_layout = (depth == 0 and self._menu_area.orientation() == Qt.Horizontal)

        if use_horizontal_layout:
            x = owner_rect.x()
            y = owner_rect.y() + owner_rect.height() + self.MENU_SPACING
        else:
            y = owner_rect.y() + owner_rect.height() // 2 - first_row_height // 2
            if self._submenu_direction == "left":
                x = owner_rect.x() - panel.width() - self.MENU_SPACING
            else:
                x = owner_rect.x() + owner_rect.width() + self.MENU_SPACING

        return QRect(x, y, panel.width(), panel.height())

    def _desired_indicator_rect(self, menu_rect):
        ind = self._indicator

        if self._menu_area.orientation() == Qt.Vertical:
            y = menu_rect.y() + (menu_rect.height() - ind.height()) // 2
            if self._submenu_direction == "right":
                x = menu_rect.x() - ind.width() - self.MENU_SPACING
            else:
                x = menu_rect.x() + menu_rect.width() + self.MENU_SPACING
        else:
            x = menu_rect.x() + (menu_rect.width() - ind.width()) // 2
            y = menu_rect.y() - ind.height() - self.MENU_SPACING

        return QRect(x, y, ind.width(), ind.height())

    def _apply_saved_state(self):
        saved = state_module.loadState()

        if saved:
            for key in ("orientation", "submenu_direction", "main_viewport_size",
                        "submenu_viewport_size", "spacing", "opacity",
                        "close_all_after_marking", "inertia_scroll_enabled",
                        "global_scale", "main_scale", "submenu_scale",
                        "accent_color", "base_color", "breadcrumb_collapse_enabled"):
                if key in saved:
                    self._settings.setValue(key, saved[key])

            self._favorites.loadEntries(saved.get("favorites"))   # ← 追加

            saved_profile_id = saved.get("active_profile_id")
            if saved_profile_id and self._config.getProfile(saved_profile_id):
                self._switch_profile(saved_profile_id)

        window_x = saved.get("window_x") if saved else None
        window_y = saved.get("window_y") if saved else None

        if window_x is not None and window_y is not None:
            self.move(window_x, window_y)
        else:
            self._center_home_on_maya()

    def _center_home_on_maya(self):
        maya_main_window = self.parent()
        if maya_main_window is None:
            return

        maya_center = maya_main_window.geometry().center()
        home_size = self._home_button.size()
        self.move(
            maya_center.x() - home_size.width() // 2,
            maya_center.y() - home_size.height() // 2
        )

    def _current_state(self):
        state = self._settings.values()
        state["window_x"] = self.pos().x()
        state["window_y"] = self.pos().y()
        state["active_profile_id"] = self._current_profile_id
        state["favorites"] = self._favorites.toStateList()   # ← 追加
        return state

    def _switch_profile(self, profile_id):
        if profile_id == self._current_profile_id:
            return

        profile = self._config.getProfile(profile_id)
        if profile is None:
            return

        self._controller.closeAll()
        self._rebuild_main_menu_buttons(profile.items)   # ← 変更。共通ヘルパー経由に統一
        self._current_profile_id = profile_id
        self._current_profile_items = profile.items

    def _show_pointer_overlay(self):
        maya_win = self.parent()
        top_left = maya_win.mapToGlobal(QPoint(0, 0))
        self._pointer_overlay.setGeometry(top_left.x(), top_left.y(), maya_win.width(), maya_win.height())
        self._pointer_overlay.show()
        self._pointer_overlay.raise_()

    def _update_pointer_line(self, start_relative, current_relative):
        """start_relative/current_relativeはHomeボタン中心を基準にしたQPointF。
        これをオーバーレイ自身のローカル座標に変換する"""
        home_center_global = self._home_button.mapToGlobal(self._home_button.rect().center())
        overlay_top_left = self._pointer_overlay.pos()

        start_global = home_center_global + QPoint(int(start_relative.x()), int(start_relative.y()))
        current_global = home_center_global + QPoint(int(current_relative.x()), int(current_relative.y()))

        self._pointer_overlay.setPointer(start_global - overlay_top_left, current_global - overlay_top_left)

    def _position_radial_menu(self):
        home_center_global = self._home_button.mapToGlobal(self._home_button.rect().center())
        offset = self._radial_menu.centerOffset()
        self._radial_menu.move(home_center_global.x() - offset.x(), home_center_global.y() - offset.y())

    def _start_menu_reveal_animation(self):
        self._stop_anim("menu")
        self._menu_area.reflowPositions()
        self._menu_area.contentWidget().updateGeometry()   # ← 追加
        QApplication.processEvents()   # ← 追加。保留中のジオメトリ更新を即座に反映させる

        content = self._menu_area.contentWidget()
        origin_global = self._home_button.mapToGlobal(QPoint(0, 0))
        origin_in_content = content.mapFromGlobal(origin_global)

        self.setUpdatesEnabled(False)
        anim = stagger.build_cascade_group(self._menu_area.items(), origin_in_content)
        self.setUpdatesEnabled(True)

        self._active_anims["menu"] = anim
        anim.start()

    def _start_submenu_reveal_animation(self, owner, panel):
        self._stop_anim(id(panel))
        panel.reflowPositions()   # ← 追加

        content = panel.contentWidget()
        origin_global = owner.mapToGlobal(QPoint(0, 0))
        origin_in_content = content.mapFromGlobal(origin_global)

        self.setUpdatesEnabled(False)
        anim = stagger.build_cascade_group(panel.items(), origin_in_content)
        self.setUpdatesEnabled(True)

        self._active_anims[id(panel)] = anim
        anim.start()

    def _stop_anim(self, key):
        """指定キーのアニメーションが実行中なら停止する。存在しなければ何もしない"""
        anim = self._active_anims.pop(key, None)
        if anim is not None and anim.state() == QAbstractAnimation.Running:
            anim.stop()

    def _build_initial_settings(self):
        s = self._config.settings
        return {
            "orientation": s.orientation,
            "submenu_direction": s.submenu_direction,
            "main_viewport_size": s.main_viewport_size,
            "submenu_viewport_size": s.submenu_viewport_size,
            "spacing": s.spacing,
            "opacity": s.opacity,
            "close_all_after_marking": s.close_all_after_marking,
            "inertia_scroll_enabled": s.inertia_scroll_enabled,
            "global_scale": s.global_scale,     # ← 追加
            "main_scale": s.main_scale,           # ← 追加
            "submenu_scale": s.submenu_scale,       # ← 追加
            "accent_color": s.accent_color,
            "base_color": s.base_color,   # ← 追加
            "breadcrumb_collapse_enabled": s.breadcrumb_collapse_enabled,
        }

    def _build_default_settings(self):
        d = models_module.Settings.DEFAULTS
        return {
            "orientation": d["orientation"],
            "submenu_direction": d["submenu_direction"],
            "main_viewport_size": d["main_viewport_size"],
            "submenu_viewport_size": d["submenu_viewport_size"],
            "spacing": d["spacing"],
            "opacity": d["opacity"],
            "close_all_after_marking": d["close_all_after_marking"],
            "inertia_scroll_enabled": d["inertia_scroll_enabled"],
            "global_scale": d["global_scale"],     # ← 追加
            "main_scale": d["main_scale"],           # ← 追加
            "submenu_scale": d["submenu_scale"],       # ← 追加
            "accent_color": d["accent_color"],
            "base_color": d["base_color"],   # ← 追加
            "breadcrumb_collapse_enabled": d["breadcrumb_collapse_enabled"],
        }

    def _apply_scale_settings(self):
        open_path = self._controller.capturePath()   # ← 追加。作り直す前に記録

        self._controller.closeAll()

        main_scale = self._settings.effectiveMainScale()
        submenu_scale = self._settings.effectiveSubmenuScale()

        self._menu_area.setButtonScale(main_scale)
        self._controller.setRowScale(submenu_scale)
        self._rebuild_main_menu_buttons(self._current_profile_items)

        self._indicator.setDotScale(main_scale)

        self._controller.reopenPath(open_path)   # ← 追加。新しいowner群に対して同じ経路を開き直す

        self._relayout()

    def _repaint_all(self):   # ← 追加
        """アクセントカラー変更時、既存Widgetの再描画をまとめて要求する。
        Theme側の値はグローバルなクラス変数のため、各Widgetのupdate()を
        明示的に呼ばないと、変更後すぐには画面に反映されない"""
        self._home_button.update()
        self._menu_area.update()
        for item in self._menu_area.items():
            item.update()
        self._indicator.update()
        for entry in self._controller.submenuStack():
            entry["panel"].update()
            for row in entry["panel"].items():
                row.update()

    def _rebuild_home_button(self, size_scale):
        old_top_left_global = self._home_button.mapToGlobal(QPoint(0, 0))

        new_button = home_button.HomeButton(
            icon=self._config.settings.home_icon, size_scale=size_scale, parent=self
        )
        new_button.move(0, 0)
        new_button.show()   # ← 追加

        old_button = self._home_button
        self._home_button = new_button
        self._connect_home_signals()

        self.move(old_top_left_global.x(), old_top_left_global.y())

        old_button.setParent(None)
        old_button.deleteLater()

    def _rebuild_main_menu_buttons(self, items):
        self._menu_area.clearItems()
        for item in items:
            button = self._menu_area.addButton(icon=item.icon, label=item.label, color=item.color)
            button.contextMenuRequested.connect(   # ← 追加
                lambda pos, it=item: self._show_favorite_context_menu(it, pos)
            )
        self._controller.rebuild(items)
        self._indicator.setCount(len(items))

    def _open_settings_dialog(self):
        if getattr(self, "_settings_dialog", None) is not None:   # ← 追加。既に開いていれば前面に出すだけ
            self._settings_dialog.raise_()
            self._settings_dialog.activateWindow()
            return

        dialog = settings_dialog.SettingsDialog(self._settings, parent=self)
        dialog.finished.connect(self._on_settings_dialog_finished)   # ← 追加
        self._settings_dialog = dialog   # ← 追加。参照を保持してガベージコレクトされないようにする
        dialog.show()   # ← 変更。exec()/exec_()からshow()へ

    def _on_settings_dialog_finished(self, result):   # ← 追加
        self._settings_dialog = None

    def _show_favorite_context_menu(self, item, global_pos):   # ← 追加
        menu = QMenu(self)

        if item.hasSubmenu() or not item.action:
            info_action = menu.addAction(u"(実行アクションのない項目はお気に入りに登録できません)")
            info_action.setEnabled(False)
        else:
            is_fav = self._favorites.isFavorite(self._current_profile_id, item.item_id)
            if is_fav:
                action = menu.addAction(u"お気に入りから削除")
                action.triggered.connect(
                    lambda: self._favorites.removeFavorite(self._current_profile_id, item.item_id)
                )
            else:
                action = menu.addAction(u"お気に入りに登録")
                action.setEnabled(self._favorites.canAdd())
                action.triggered.connect(
                    lambda: self._favorites.addFavorite(self._current_profile_id, item.item_id)
                )

        if hasattr(menu, "exec"):
            menu.exec(global_pos)
        else:
            menu.exec_(global_pos)

    def _resolve_favorite_items(self):   # ← 追加
        """FavoritesManagerが持つ識別子(profile_id, item_id)を、
        現在のconfigから実際のMenuItemに解決し、FavoritesRadialMenuに渡す形式に変換する"""
        resolved = []
        for entry in self._favorites.entries():
            item = self._config.findItem(entry["profile_id"], entry["item_id"])
            if item is None:
                continue   # 項目が削除された等で見つからない場合はスキップ
            resolved.append({
                "profile_id": entry["profile_id"],
                "item_id": entry["item_id"],
                "icon": item.icon,
                "color": item.color,
                "item": item,
            })
        return resolved

    def _on_favorites_menu_opened(self, click_point):
        if self._favorites_edit_mode:   # ← 追加。編集モード中は選択操作を無視する
            return

        self._main_menu_was_visible_before_favorites = self._menu_area.isVisible()
        if self._main_menu_was_visible_before_favorites:
            self._menu_area.setVisible(False)
            self._indicator.setVisible(False)
            self._relayout()

        resolved = self._resolve_favorite_items()
        self._favorites_radial_menu.setFavorites(resolved)
        self._position_favorites_radial_menu()
        self._favorites_radial_menu.show()
        self._favorites_radial_menu.raise_()

        self._show_pointer_overlay()
        self._update_pointer_line(click_point, click_point)

    def _on_favorites_menu_updated(self, click_point, current_point):
        if self._favorites_edit_mode:   # ← 追加
            return
        local_point = self._favorites_radial_menu.mapFromGlobal(
            self._home_button.mapToGlobal(QPoint(
                int(current_point.x() + self._home_button.width() / 2.0),
                int(current_point.y() + self._home_button.height() / 2.0)
            ))
        )
        self._favorites_radial_menu.setHoverPoint(local_point)
        self._update_pointer_line(click_point, current_point)

    def _on_favorites_menu_closed(self, current_point):
        if self._favorites_edit_mode:   # ← 追加
            return

        local_point = self._favorites_radial_menu.mapFromGlobal(
            self._home_button.mapToGlobal(QPoint(
                int(current_point.x() + self._home_button.width() / 2.0),
                int(current_point.y() + self._home_button.height() / 2.0)
            ))
        )
        entry = self._favorites_radial_menu.entryAt(local_point)

        self._favorites_radial_menu.setVisible(False)
        self._favorites_radial_menu.setHoverPoint(None)
        self._pointer_overlay.clearAndHide()

        if entry is not None:
            item = self._config.findItem(entry["profile_id"], entry["item_id"])
            if item is not None and item.action:
                self._execute_favorite_item(item)

        if getattr(self, "_main_menu_was_visible_before_favorites", False):
            self._menu_area.setVisible(True)
            self._indicator.setVisible(True)
            self._relayout()
            self._main_menu_was_visible_before_favorites = False

    def _execute_favorite_item(self, item):   # ← 追加
        from ..core import registry as registry_module
        try:
            registry_module.call_action(item.action, *item.args, **item.kwargs)
        except registry_module.ActionResolveError as e:
            print(u"[ToolMenuLane] お気に入り実行エラー '{0}': {1}".format(item.item_id, e))
        except Exception as e:
            print(u"[ToolMenuLane] お気に入り実行中にエラーが発生しました '{0}': {1}".format(item.item_id, e))

    def _position_favorites_radial_menu(self):   # ← 追加
        home_center_global = self._home_button.mapToGlobal(self._home_button.rect().center())
        offset = self._favorites_radial_menu.centerOffset()
        self._favorites_radial_menu.move(
            home_center_global.x() - offset.x(), home_center_global.y() - offset.y()
        )

    def _on_favorites_edit_toggle_requested(self):   # ← 追加
        if self._favorites_edit_mode:
            self._close_favorites_edit_mode()
        else:
            self._open_favorites_edit_mode()

    def _open_favorites_edit_mode(self):   # ← 追加
        self._favorites_edit_mode = True
        self._home_button.setFavoritesEditMode(True)

        self._main_menu_was_visible_before_favorites = self._menu_area.isVisible()
        if self._main_menu_was_visible_before_favorites:
            self._menu_area.setVisible(False)
            self._indicator.setVisible(False)
            self._relayout()

        self._refresh_favorites_radial()
        self._favorites_radial_menu.setEditMode(True)
        self._position_favorites_radial_menu()
        self._favorites_radial_menu.show()
        self._favorites_radial_menu.raise_()

    def _close_favorites_edit_mode(self):   # ← 追加
        self._favorites_edit_mode = False
        self._home_button.setFavoritesEditMode(False)
        self._favorites_radial_menu.setEditMode(False)
        self._favorites_radial_menu.setVisible(False)

        if getattr(self, "_main_menu_was_visible_before_favorites", False):
            self._menu_area.setVisible(True)
            self._indicator.setVisible(True)
            self._relayout()
            self._main_menu_was_visible_before_favorites = False

    def _refresh_favorites_radial(self):   # ← 追加
        resolved = self._resolve_favorite_items()
        self._favorites_radial_menu.setFavorites(resolved)
        if self._favorites_edit_mode:
            self._favorites_radial_menu.setEditMode(True)

    def _on_favorites_reorder_requested(self, from_index, to_index):   # ← 追加
        self._favorites.swapFavorites(from_index, to_index)
        self._refresh_favorites_radial()

    def _on_favorites_remove_requested(self, profile_id, item_id):   # ← 追加
        self._favorites.removeFavorite(profile_id, item_id)
        self._refresh_favorites_radial()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            if getattr(self, "_favorites_edit_mode", False):   # ← 追加
                self._close_favorites_edit_mode()
            self._controller.closeAll()
        QWidget.keyPressEvent(self, event)

    def _open_menu_config_editor(self):
        if getattr(self, "_config_editor_dialog", None) is not None:
            self._config_editor_dialog.raise_()
            self._config_editor_dialog.activateWindow()
            return

        dialog = menu_config_editor.MenuConfigEditor(initial_path=self._config_path, parent=self)
        dialog.finished.connect(self._on_config_editor_finished)
        dialog.savedToPath.connect(self._on_config_editor_saved)   # ← 追加
        self._config_editor_dialog = dialog
        dialog.show()

    def _on_config_editor_finished(self, result):   # ← 追加
        self._config_editor_dialog = None

    def _on_config_editor_saved(self, saved_path):   # ← 追加
        if os.path.normpath(saved_path) != os.path.normpath(self._config_path):
            return   # 別ファイルとして保存された場合は、今のツールには反映しない

        self._reload_config_and_rebuild()

    def _reload_config_and_rebuild(self):   # ← 追加
        try:
            new_config = config_module.loadConfig(self._config_path)
        except config_module.ConfigError as e:
            print(u"[ToolMenuLane] 設定ファイルの再読み込みに失敗しました: {0}".format(e))
            return

        self._config = new_config

        profile = self._config.getProfile(self._current_profile_id)
        if profile is None:
            # 編集で現在のプロファイル自体が削除・IDが変わった場合は、先頭のプロファイルにフォールバックする
            profile = self._config.profiles[0] if self._config.profiles else None
            if profile is None:
                print(u"[ToolMenuLane] 設定ファイルにプロファイルが1つもありません。")
                return
            self._current_profile_id = profile.profile_id

        self._controller.closeAll()
        self._rebuild_main_menu_buttons(profile.items)
        self._current_profile_items = profile.items

        self._home_button.setLabel(u"クリックでメニュー開閉 / 右クリックで設定")

        if self._config.settings.home_icon != self._home_button._icon_path:   # ← Homeアイコンが変わっていれば作り直す
            global_scale = self._settings.effectiveMainScale()   # 現状のスケールは維持する
            self._rebuild_home_button(self._settings.clampScale(self._settings.get("global_scale", 1.0)))

        self._relayout()
            
def _get_maya_main_window():
    main_window_ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(int(main_window_ptr), QWidget)

def show_window():
    maya_main_window = _get_maya_main_window()
    this_win = maya_main_window.findChild(QWidget, ToolMenuLane.TOOL_OBJECT_NAME)
    if this_win:
        this_win.close()
        this_win.deleteLater()

    win = ToolMenuLane(maya_main_window)
    win.show()
    return win

