# -*- coding: utf-8 -*-

try:
    from PySide6.QtWidgets import *
    from PySide6.QtGui import *
    from PySide6.QtCore import *
except ImportError:
    from PySide2.QtWidgets import *
    from PySide2.QtGui import *
    from PySide2.QtCore import *

from . import donut_button
from .. import theme

class HomeButton(donut_button.DonutButton):

    DRAG_THRESHOLD          = 4

    BACKDROP_COLOR              = QColor(100, 100, 200, 100)
    PLATFORM_RING_COLOR         = QColor(255, 215, 100)
    PLATFORM_RING_WIDTH         = 2      # リングの太さ(半径方向)
    PLATFORM_RING_GAP           = 4      # 本体の外周円からの距離
    PLATFORM_RING_START_ANGLE   = 0     # ← 変更。最初のくり抜き角度
    PLATFORM_RING_STEP_ANGLE    = 45     # ← 変更。くり抜きの間隔角度
    PLATFORM_RING_NOTCH_WIDTH   = 4      # ← 追加。くり抜く部分の幅(px、周方向)

    settingsRequested = Signal()   # ← 変更。個別のRequestedシグナル群を1つに統合
    radialMenuOpened  = Signal(object)
    radialMenuUpdated = Signal(object, object)
    radialMenuClosed  = Signal(object)
    favoritesMenuOpened  = Signal(object)   # ← 追加
    favoritesMenuUpdated = Signal(object, object)   # ← 追加
    favoritesMenuClosed   = Signal(object)    # ← 追加
    favoritesEditToggleRequested = Signal() 
    menuConfigEditorRequested = Signal() 

    def __init__(self, icon=None, size_scale=1.0, parent=None):   # ← size_scale追加
        super(HomeButton, self).__init__(icon=icon, size_scale=size_scale, parent=parent)

        self._effective_ring_gap = max(1, int(round(self.PLATFORM_RING_GAP * size_scale)))       # ← 追加
        self._effective_ring_width = max(1, int(round(self.PLATFORM_RING_WIDTH * size_scale)))     # ← 追加
        self._effective_notch_width = max(1, int(round(self.PLATFORM_RING_NOTCH_WIDTH * size_scale)))   # ← 追加

        ring_margin = self._effective_ring_gap + self._effective_ring_width   # ← 変更。effective値を使用
        size = self._effective_size + ring_margin * 2   # ← 変更。DEFAULT_SIZEからeffective_sizeへ
        self.setFixedSize(size, size)

        self._has_submenu = True
        self._show_submenu_marker = False

        self._is_dragging = False
        self._drag_start_global = None
        self._window_start_pos = None

        self._is_radial_active = False
        self._radial_click_point = None

        self._is_favorites_active = False   # ← 追加
        self._favorites_click_point = None   # ← 追加
        self._is_favorites_edit_press = False       # ← 追加
        self._favorites_edit_press_pos = None
        self._favorites_edit_mode = False

    def paintEvent(self, event):
        self._paint_backdrop()
        super(HomeButton, self).paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setOpacity(self._opacity)

        self._draw_platform_ring(painter, self._donut_rect())

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            mods = event.modifiers()
            is_toggle_combo = (mods & Qt.ControlModifier) and (mods & Qt.ShiftModifier)

            if self._favorites_edit_mode and not is_toggle_combo:   # ← 変更。終了操作自体は通す
                event.accept()
                return

            if (mods & Qt.ControlModifier) and (mods & Qt.ShiftModifier):   # ← 追加。両方同時が最優先
                self._is_favorites_edit_press = True
                self._favorites_edit_press_pos = self._center_relative_pos(event)
                self._is_radial_active = False
                self._is_favorites_active = False
                self._radial_click_point = None
                self._favorites_click_point = None
            elif mods & Qt.ControlModifier:
                self._is_radial_active = True
                self._is_favorites_edit_press = False   # ← 追加
                self._favorites_click_point = None
                self._radial_click_point = self._center_relative_pos(event)
                self.radialMenuOpened.emit(self._radial_click_point)
            elif mods & Qt.ShiftModifier:
                self._is_favorites_active = True
                self._is_favorites_edit_press = False   # ← 追加
                self._radial_click_point = None
                self._favorites_click_point = self._center_relative_pos(event)
                self.favoritesMenuOpened.emit(self._favorites_click_point)
            else:
                self._is_radial_active = False
                self._is_favorites_active = False
                self._is_favorites_edit_press = False   # ← 追加
                self._radial_click_point = None
                self._favorites_click_point = None
                self._plain_right_press_global = self._get_event_global_pos(event)
            event.accept()
            return

        if event.button() == Qt.LeftButton:
            if self._favorites_edit_mode:   # ← 追加。編集モード中はドラッグ移動を無効化
                event.accept()
                return
            self._is_dragging = False
            self._drag_start_global = self._get_event_global_pos(event)
            self._window_start_pos = self.window().pos()

        super(HomeButton, self).mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.RightButton:
            if self._is_radial_active and self._radial_click_point is not None:
                current_point = self._center_relative_pos(event)
                self.radialMenuUpdated.emit(self._radial_click_point, current_point)
                return
            if self._is_favorites_active and self._favorites_click_point is not None:
                current_point = self._center_relative_pos(event)
                self.favoritesMenuUpdated.emit(self._favorites_click_point, current_point)
                return
            return   # ← 編集モードトリガー(_is_favorites_edit_press)はドラッグ自体を扱わないので、ここは何もしない

        if event.buttons() & Qt.LeftButton and self._drag_start_global is not None:
            current_global = self._get_event_global_pos(event)
            delta = current_global - self._drag_start_global

            if not self._is_dragging:
                if abs(delta.x()) >= self.DRAG_THRESHOLD or abs(delta.y()) >= self.DRAG_THRESHOLD:
                    self._is_dragging = True

            if self._is_dragging:
                self.window().move(self._window_start_pos + delta)

        super(HomeButton, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.RightButton:
            if self._is_favorites_edit_press:   # ← 追加。クリック(ドラッグなし)判定
                pos = self._center_relative_pos(event)
                start = self._favorites_edit_press_pos
                distance = 0.0
                if start is not None:
                    distance = ((pos.x() - start.x()) ** 2 + (pos.y() - start.y()) ** 2) ** 0.5
                if distance <= self.DRAG_THRESHOLD:
                    self.favoritesEditToggleRequested.emit()
            elif self._is_radial_active:
                current_point = self._center_relative_pos(event)
                self.radialMenuClosed.emit(current_point)
            elif self._is_favorites_active:
                current_point = self._center_relative_pos(event)
                self.favoritesMenuClosed.emit(current_point)
            else:
                menu_pos = self._plain_right_press_global or event.globalPos()
                self._show_context_menu(menu_pos)

            self._is_radial_active = False
            self._is_favorites_active = False
            self._is_favorites_edit_press = False   # ← 追加
            self._radial_click_point = None
            self._favorites_click_point = None
            self._favorites_edit_press_pos = None   # ← 追加
            self._plain_right_press_global = None
            event.accept()
            return

        if event.button() == Qt.LeftButton:
            if self._is_dragging:
                self._is_pressed = False
                self.update()
            else:
                super(HomeButton, self).mouseReleaseEvent(event)

            self._is_dragging = False
            self._drag_start_global = None
            self._window_start_pos = None
            return

        super(HomeButton, self).mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        # OS標準のcontextMenuEventには頼らず、mouseReleaseEvent側で
        # ドラッグの有無を見て手動でメニュー表示を判断する
        event.ignore()

    # ------------------------------
    # 
    # ------------------------------
    def setMainViewportSize(self, size):
        self._main_viewport_size = size

    def setSubmenuViewportSize(self, size):
        self._submenu_viewport_size = size

    def setWindowOpacityValue(self, opacity):
        self._remembered_window_opacity = opacity

    def setCloseAllAfterMarking(self, enabled):   # ← 追加
        self._close_all_after_marking = enabled

    def setFavoritesEditMode(self, enabled):   # ← 追加
        self._favorites_edit_mode = enabled

    # ------------------------------
    # 
    # ------------------------------
    def _show_context_menu(self, global_pos):
        menu = QMenu(self)

        settings_action = menu.addAction(u"設定...")
        config_editor_action = menu.addAction(u"メニュー構成を編集...")
        menu.addSeparator()
        close_action = menu.addAction(u"閉じる")

        settings_action.triggered.connect(self.settingsRequested.emit)
        config_editor_action.triggered.connect(self.menuConfigEditorRequested.emit)
        close_action.triggered.connect(self._on_close_requested)

        self._exec_menu(menu, global_pos)

    def _on_close_requested(self):
        self.window().close()

    def _exec_menu(self, menu, global_pos):
        if hasattr(menu, "exec"):
            menu.exec(global_pos)
        else:
            menu.exec_(global_pos)

    def _on_radial_open_timeout(self):
        self._radial_timer_elapsed = True

    def _on_set_main_viewport_size(self):
        value = self._prompt_int(u"メインメニューの長さ", self._main_viewport_size)
        if value is not None:
            self.mainViewportSizeRequested.emit(value)

    def _on_set_submenu_viewport_size(self):
        value = self._prompt_int(u"サブメニューの長さ", self._submenu_viewport_size)
        if value is not None:
            self.submenuViewportSizeRequested.emit(value)

    def _on_set_opacity(self):
        value = self._prompt_double(u"透明度 (0.2〜1.0)", self._remembered_window_opacity)
        if value is not None:
            self.opacityRequested.emit(value)

    def _on_close_after_marking_toggled(self, checked):   # ← 追加
        self._close_all_after_marking = checked   # ← 自分自身の状態も必ず更新しておく
        self.closeAfterMarkingRequested.emit(checked)

    def _prompt_int(self, label, current_value):
        value, ok = QInputDialog.getInt(self, label, label, current_value, 50, 2000, 10)
        return value if ok else None

    def _get_event_global_pos(self, event):
        if hasattr(event, "globalPosition"):
            point = event.globalPosition()
            return QPoint(int(point.x()), int(point.y()))
        return event.globalPos()

    def _center_relative_pos(self, event):
        pos = self._get_event_pos(event)
        center = QPointF(self.width() / 2.0, self.height() / 2.0)
        return QPointF(pos.x() - center.x(), pos.y() - center.y())

    def _prompt_double(self, label, current_value):
        value, ok = QInputDialog.getDouble(self, label, label, current_value, 0.2, 1.0, 2)
        return value if ok else None

    def _donut_rect(self):   # ← 変更。effective値を使用
        half_pen = self._effective_pen_width / 2.0
        offset = (self.width() - self._effective_size) / 2.0
        return QRectF(offset + half_pen, offset + half_pen,
                       self._effective_size - self._effective_pen_width,
                       self._effective_size - self._effective_pen_width)

    def _paint_backdrop(self):   # ← 追加
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setOpacity(self._opacity)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self.BACKDROP_COLOR))

        center = QPointF(self.width() / 2.0, self.height() / 2.0)
        radius = self.width() / 2.0
        painter.drawEllipse(center, radius, radius)

    def _draw_platform_ring(self, painter, donut_rect):
        center = donut_rect.center()
        inner_r = donut_rect.width() / 2.0 + self._effective_ring_gap
        outer_r = inner_r + self._effective_ring_width

        ring_path = self._build_ring_path(center, inner_r, outer_r)

        notch_count = int(round(360.0 / self.PLATFORM_RING_STEP_ANGLE))
        for i in range(notch_count):
            angle = self.PLATFORM_RING_START_ANGLE + i * self.PLATFORM_RING_STEP_ANGLE
            notch = self._build_notch_path(center, inner_r, outer_r, angle, self._effective_notch_width)
            ring_path = ring_path.subtracted(notch)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(theme.Theme.accentColor()))   # ← 変更
        painter.drawPath(ring_path)

    def _build_ring_path(self, center, inner_r, outer_r):
        """外径outer_r・内径inner_rのドーナツ形状(円環)を1つのパスとして作る。
        OddEvenFillにより「外側の円の内側 かつ 内側の円の外側」の領域だけが塗りつぶし対象になる"""
        path = QPainterPath()
        path.setFillRule(Qt.OddEvenFill)

        outer_rect = QRectF(center.x() - outer_r, center.y() - outer_r, outer_r * 2, outer_r * 2)
        inner_rect = QRectF(center.x() - inner_r, center.y() - inner_r, inner_r * 2, inner_r * 2)

        path.addEllipse(outer_rect)
        path.addEllipse(inner_rect)
        return path

    def _build_notch_path(self, center, inner_r, outer_r, angle_deg, notch_width):
        """centerを基準に、angle_deg方向・半径inner_r〜outer_rの範囲を貫通する
        細long矩形を作る。これをring_pathから引き算することで、その角度位置に
        「切れ目」を作る"""
        radial_length = (outer_r - inner_r) + 4   # リングの厚みより少し長くして確実に貫通させる

        rect = QRectF(-radial_length / 2.0, -notch_width / 2.0, radial_length, notch_width)

        transform = QTransform()
        transform.translate(center.x(), center.y())
        transform.rotate(angle_deg)
        transform.translate((inner_r + outer_r) / 2.0, 0)   # 半径方向の中心位置まで移動

        path = QPainterPath()
        path.addRect(rect)
        return transform.map(path)
    
    def _effective_scale(self):   # ← 追加
        """Homeはマーキングホバーで拡大させない。展開アニメーション用のscaleのみ有効"""
        return self._scale