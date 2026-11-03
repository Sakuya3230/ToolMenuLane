# -*- coding: utf-8 -*-

try:
    from PySide6.QtWidgets import *
    from PySide6.QtGui import *
    from PySide6.QtCore import *
except ImportError:
    from PySide2.QtWidgets import *
    from PySide2.QtGui import *
    from PySide2.QtCore import *

from .. import theme

__all__ = ["DonutButton"]


class DonutButton(QWidget):

    DEFAULT_SIZE                = 48
    INNER_RATIO                 = 0.6
    OUTER_PEN_WIDTH             = 2
    CLICK_DRAG_TOLERANCE        = 6
    MARKING_HOVER_SCALE         = 1.25
    SUBMENU_BADGE_RADIUS        = 5

    NORMAL_COLOR                = QColor(255, 255, 255)
    HOVER_COLOR                 = QColor(180, 180, 255)
    PRESSED_DARKEN              = 150
    SUBMENU_BADGE_BORDER_COLOR  = QColor(50, 50, 50)
    SUBMENU_BADGE_BORDER_WIDTH  = 1

    MIN_SIZE_SCALE = 0.6   # ← 追加。参考値。実際のクランプは設定レイヤー側で行う
    MAX_SIZE_SCALE = 1.6   # ← 追加

    clicked = Signal()
    toggled = Signal(bool)
    markingPressed  = Signal()
    markingMoved    = Signal(object)
    markingReleased = Signal(object)
    hoverMoved       = Signal(object)
    contextMenuRequested = Signal(object)

    def __init__(self, icon=None, size_scale=1.0, color=None, parent=None):   # ← size_scale追加
        super(DonutButton, self).__init__(parent)

        self._size_scale = size_scale   # ← 追加
        self._effective_size, self._margin, total = self._compute_metrics(size_scale)   # ← 追加
        self._effective_pen_width = max(1, int(round(self.OUTER_PEN_WIDTH * size_scale)))   # ← 追加
        self._effective_badge_radius = max(2.0, self.SUBMENU_BADGE_RADIUS * size_scale)   # ← 追加
        self._effective_badge_border_width = max(   # ← 追加
            1, int(round(self.SUBMENU_BADGE_BORDER_WIDTH * size_scale))
        )

        self._icon_path = icon   # ← 変更。pixmapではなくパスを保持
        self._icon_pixmap_cache = None   # ← 追加
        self._icon_pixmap_cache_size = None   # ← 追加
        self._icon_invalid = False   # ← 追加。読み込み失敗を一度確認したら以後は都度試行しない

        self._is_hovered = False
        self._is_pressed = False
        self._is_active = False
        self._has_submenu = True
        self._show_submenu_marker = True
        self._submenu_direction = "right"
        self._opacity = 1.0
        self._scale = 1.0
        self._press_pos = None
        self._color_override = QColor(color) if color else None

        self._right_press_pos = None      # ← 追加
        self._right_is_dragging = False   # ← 追加

        self.setMouseTracking(True)
        self.setFixedSize(total, total)   # ← totalSize()の代わりに、既に計算済みのtotalを使う

    @classmethod
    def _compute_metrics(cls, scale):   # ← 追加
        """指定scaleにおける (実サイズ, 拡大用マージン, Widget全体のサイズ) を計算する"""
        effective_size = max(4, int(round(cls.DEFAULT_SIZE * scale)))
        hover_margin = (effective_size * cls.MARKING_HOVER_SCALE - effective_size) / 2.0
        extra_margin = max(2, int(round(2 * scale)))
        margin = int(hover_margin) + extra_margin
        total = effective_size + margin * 2
        return effective_size, margin, total

    @classmethod
    def totalSize(cls, scale=1.0):   # ← scale引数を追加(デフォルト1.0で後方互換)
        _, _, total = cls._compute_metrics(scale)
        return total

    def sizeScale(self):   # ← 追加
        return self._size_scale

    def isActive(self):
        return self._is_active

    def setHasSubmenu(self, has_submenu):
        self._has_submenu = has_submenu

    def setSubmenuDirection(self, direction):
        if direction == self._submenu_direction:
            return
        self._submenu_direction = direction
        self.update()

    def setLabel(self, label):   # ← 追加
        self.setToolTip(label or "")

    def setColor(self, color):   # ← 追加
        self._color_override = QColor(color) if color else None
        self.update()

    def hitTest(self, local_point):
        return "forward" if self._is_inside_circle(local_point) else None

    def setMarkingZone(self, zone):
        hovered = (zone == "forward")
        if hovered == self._is_hovered:
            return
        self._is_hovered = hovered
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setOpacity(self._opacity)

        donut_rect = self._donut_rect()
        effective_scale = self._effective_scale()

        if effective_scale != 1.0:
            center = donut_rect.center()
            painter.translate(center)
            painter.scale(effective_scale, effective_scale)
            painter.translate(-center)

        color = self._current_color()

        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(color, self._effective_pen_width))
        painter.drawEllipse(donut_rect)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(color))

        margin_x = donut_rect.width() * (1 - self.INNER_RATIO) / 2
        margin_y = donut_rect.height() * (1 - self.INNER_RATIO) / 2
        inner_rect = donut_rect.adjusted(margin_x, margin_y, -margin_x, -margin_y)
        painter.drawEllipse(inner_rect)   # ← 追加。抜けていた内側円の描画

        if self._icon_path is not None and not self._icon_invalid:
            self._draw_icon(painter, inner_rect)

        if self._has_submenu and self._show_submenu_marker:
            self._draw_submenu_badge(painter, donut_rect)

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self._right_press_pos = self._get_event_pos(event)   # ← 変更。markingPressedは即発行しない
            self._right_is_dragging = False
            event.accept()
            return

        pos = self._get_event_pos(event)
        if event.button() == Qt.LeftButton and self._is_inside_circle(pos):
            self._is_pressed = True
            self._press_pos = pos
            self.update()
        super(DonutButton, self).mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.RightButton:
            if self._right_press_pos is not None:
                pos = self._get_event_pos(event)
                distance = (
                    (pos.x() - self._right_press_pos.x()) ** 2 +
                    (pos.y() - self._right_press_pos.y()) ** 2
                ) ** 0.5

                if not self._right_is_dragging and distance > self.CLICK_DRAG_TOLERANCE:
                    self._right_is_dragging = True
                    self.markingPressed.emit()   # ← ここで初めてマーキング操作を開始する

                if self._right_is_dragging:
                    self.markingMoved.emit(self._get_event_global_pos(event))
            return

        pos = self._get_event_pos(event)
        zone = self.hitTest(pos)
        self.setMarkingZone(zone)
        self.hoverMoved.emit(self._get_event_global_pos(event))

        super(DonutButton, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.RightButton:
            if self._right_is_dragging:
                self.markingReleased.emit(self._get_event_global_pos(event))
            else:
                self.contextMenuRequested.emit(self._get_event_global_pos(event))   # ← 追加

            self._right_press_pos = None
            self._right_is_dragging = False
            event.accept()
            return

        # 以降、左クリック処理は変更なし
        was_pressed = self._is_pressed
        press_pos = self._press_pos
        self._is_pressed = False
        self._press_pos = None

        pos = self._get_event_pos(event)
        moved_too_far = False
        if press_pos is not None:
            distance = ((pos.x() - press_pos.x()) ** 2 + (pos.y() - press_pos.y()) ** 2) ** 0.5
            moved_too_far = distance > self.CLICK_DRAG_TOLERANCE

        if was_pressed and not moved_too_far and self._is_inside_circle(pos):
            if self._has_submenu:
                self.setActive(not self._is_active)
            self.clicked.emit()

        self.update()
        super(DonutButton, self).mouseReleaseEvent(event)

    def _get_event_global_pos(self, event):
        if hasattr(event, "globalPosition"):
            point = event.globalPosition()
            return QPoint(int(point.x()), int(point.y()))
        return event.globalPos()

    def setActive(self, is_active):
        if self._is_active == is_active:
            return
        self._is_active = is_active
        self.update()
        self.toggled.emit(self._is_active)

    def leaveEvent(self, event):
        self.setMarkingZone(None)
        self.hoverMoved.emit(None)
        super(DonutButton, self).leaveEvent(event)

    def _load_icon(self, icon):
        if icon is None:
            return None
        pixmap = QIcon(icon).pixmap(self._effective_size, self._effective_size)   # ← 変更。DEFAULT_SIZEから_effective_sizeへ
        if pixmap.isNull():
            return None
        return pixmap

    def _get_icon_pixmap(self, size):   # ← 追加
        """指定サイズ(正方形)のアイコンpixmapを返す。直前と同じサイズならキャッシュを再利用し、
        そうでなければQIconから改めて指定サイズぴったりで読み直す(scaled()による滲みを避けるため)"""
        if size <= 0:
            return None

        if self._icon_pixmap_cache is not None and self._icon_pixmap_cache_size == size:
            return self._icon_pixmap_cache

        pixmap = QIcon(self._icon_path).pixmap(size, size)
        if pixmap.isNull():
            self._icon_invalid = True
            return None

        self._icon_pixmap_cache = pixmap
        self._icon_pixmap_cache_size = size
        return pixmap

    def _get_event_pos(self, event):
        if hasattr(event, "position"):
            return event.position().toPoint()
        return event.pos()

    def _is_inside_circle(self, point):
        donut_rect = self._donut_rect()
        center = donut_rect.center()
        radius = (self._effective_size + self._effective_pen_width) / 2   # ← 変更
        distance = ((point.x() - center.x()) ** 2 + (point.y() - center.y()) ** 2) ** 0.5
        return distance <= radius

    def _draw_icon(self, painter, inner_rect):   # ← 変更
        size = int(round(min(inner_rect.width(), inner_rect.height())))
        pixmap = self._get_icon_pixmap(size)
        if pixmap is None:
            return

        clip_path = QPainterPath()
        clip_path.addEllipse(self._donut_rect())
        painter.setClipPath(clip_path)

        offset_x = inner_rect.x() + (inner_rect.width() - pixmap.width()) / 2
        offset_y = inner_rect.y() + (inner_rect.height() - pixmap.height()) / 2
        painter.drawPixmap(int(offset_x), int(offset_y), pixmap)

        painter.setClipping(False)

    def _draw_submenu_badge(self, painter, donut_rect):
        radius = donut_rect.width() / 2.0
        badge_r = self._effective_badge_radius

        if self._submenu_direction == "left":
            offset_x = radius - radius * 0.6
        else:
            offset_x = radius + radius * 0.6

        offset_y = radius + donut_rect.height() * 0.25
        badge_center = QPointF(donut_rect.x() + offset_x, donut_rect.y() + offset_y)

        painter.setPen(QPen(self.SUBMENU_BADGE_BORDER_COLOR, self._effective_badge_border_width))
        painter.setBrush(QBrush(theme.Theme.accentColor()))   # ← 変更
        painter.drawEllipse(badge_center, badge_r, badge_r)

    def _base_color(self):
        if self._is_active:
            return theme.Theme.accentColor()   # ← 変更
        if self._is_hovered:
            return theme.Theme.accentColorSoft() 
        if self._color_override is not None:   # ← 追加
            return self._color_override
        return theme.Theme.baseColor()

    def _current_color(self):
        color = self._base_color()
        if self._is_pressed:
            return color.darker(self.PRESSED_DARKEN)
        return color

    def _get_opacity(self):
        return self._opacity

    def _set_opacity(self, value):
        self._opacity = value
        self.update()

    opacity = Property(float, _get_opacity, _set_opacity)

    def _get_scale(self):
        return self._scale

    def _set_scale(self, value):
        self._scale = value
        self.update()

    scale = Property(float, _get_scale, _set_scale)

    def _donut_rect(self):
        half_pen = self._effective_pen_width / 2.0   # ← 変更。OUTER_PEN_WIDTHから
        return QRectF(
            self._margin + half_pen, self._margin + half_pen,
            self._effective_size - self._effective_pen_width,   # ← 変更
            self._effective_size - self._effective_pen_width     # ← 変更
        )

    def _effective_scale(self):
        return self._scale * (self.MARKING_HOVER_SCALE if self._is_hovered else 1.0)

    def layoutSize(self):
        return self._effective_size   # ← 変更。DEFAULT_SIZEから_effective_sizeへ

    def layoutOffset(self):
        return self._margin

    