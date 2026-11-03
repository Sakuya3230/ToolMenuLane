# -*- coding: utf-8 -*-

try:
    from PySide6.QtWidgets import *
    from PySide6.QtGui import *
    from PySide6.QtCore import *
except ImportError:
    from PySide2.QtWidgets import *
    from PySide2.QtGui import *
    from PySide2.QtCore import *


__all__ = ["SubMenuRow"]

from .. import theme

class SubMenuRow(QWidget):

    ROW_HEIGHT       = 36
    RAIL_ZONE_WIDTH  = 26
    CONTENT_WIDTH    = 200
    STACK_PEEK_WIDTH  = 8
    ROW_WIDTH        = RAIL_ZONE_WIDTH + CONTENT_WIDTH + STACK_PEEK_WIDTH
    CORNER_RADIUS     = 8
    ICON_SIZE          = 20
    ICON_MARGIN         = 8
    ICON_CHIP_COLOR       = QColor(0, 0, 0, 35)
    CLICK_DRAG_TOLERANCE   = 6
    MARKING_HOVER_SCALE      = 1.08

    STACK_INSET_TOP  = 4
    STACK_ALPHA        = 130

    RAIL_DOT_RADIUS         = 4
    RAIL_DOT_BORDER_WIDTH     = 1
    RAIL_DOT_BORDER_COLOR       = QColor(50, 50, 50)
    RAIL_DOT_NORMAL_COLOR         = QColor(210, 210, 210)
    RAIL_DOT_HOVER_COLOR            = QColor(255, 255, 200)

    NORMAL_COLOR   = QColor(255, 255, 255)
    HOVER_COLOR    = QColor(255, 255, 180)
    TEXT_COLOR     = QColor(30, 30, 30)
    PRESSED_DARKEN = 150

    MIN_SIZE_SCALE = 0.6   # ← 追加。参考値
    MAX_SIZE_SCALE = 1.6   # ← 追加

    clicked = Signal()
    toggled = Signal(bool)
    markingPressed  = Signal()
    markingMoved    = Signal(object)
    markingReleased = Signal(object)
    hoverMoved       = Signal(object)
    contextMenuRequested = Signal(object)

    def __init__(self, icon=None, label="", has_submenu=False, size_scale=1.0, color=None, parent=None):   # ← size_scale追加
        super(SubMenuRow, self).__init__(parent)

        self._size_scale = size_scale   # ← 追加
        metrics = self._compute_metrics(size_scale)   # ← 追加
        self._m = metrics   # ← 追加。以降 self._m["xxx"] で参照する

        self.setFixedSize(metrics["row_width"], metrics["row_height"])   # ← 変更
        self.setMouseTracking(True)

        self._icon_pixmap = self._load_icon(icon)
        self._label = label
        self._has_submenu = has_submenu
        self._submenu_direction = "right"
        self._compact = False

        self._is_hovered = False
        self._rail_hovered = False
        self._is_pressed = False
        self._is_active = False
        self._opacity = 1.0
        self._scale = 1.0
        self._press_pos = None
        self._color_override = QColor(color) if color else None

        self._right_press_pos = None      # ← 追加
        self._right_is_dragging = False   # ← 追加

    @classmethod
    def _compute_metrics(cls, scale):   # ← 追加
        row_height = max(20, int(round(cls.ROW_HEIGHT * scale)))
        rail_zone_width = max(12, int(round(cls.RAIL_ZONE_WIDTH * scale)))
        content_width = max(80, int(round(cls.CONTENT_WIDTH * scale)))
        stack_peek_width = max(2, int(round(cls.STACK_PEEK_WIDTH * scale)))
        icon_size = max(10, int(round(cls.ICON_SIZE * scale)))
        icon_margin = max(2, int(round(cls.ICON_MARGIN * scale)))
        corner_radius = max(2, int(round(cls.CORNER_RADIUS * scale)))
        stack_inset_top = max(1, int(round(cls.STACK_INSET_TOP * scale)))
        rail_dot_radius = max(2.0, cls.RAIL_DOT_RADIUS * scale)
        rail_dot_border_width = max(1, int(round(cls.RAIL_DOT_BORDER_WIDTH * scale)))
        icon_chip_radius = icon_size / 2.0 + max(2, int(round(5 * scale)))
        row_width = rail_zone_width + content_width + stack_peek_width

        return {
            "row_height": row_height,
            "rail_zone_width": rail_zone_width,
            "content_width": content_width,
            "stack_peek_width": stack_peek_width,
            "icon_size": icon_size,
            "icon_margin": icon_margin,
            "corner_radius": corner_radius,
            "stack_inset_top": stack_inset_top,
            "rail_dot_radius": rail_dot_radius,
            "rail_dot_border_width": rail_dot_border_width,
            "icon_chip_radius": icon_chip_radius,
            "row_width": row_width,
        }

    @classmethod
    def rowWidth(cls, scale=1.0):   # ← 追加
        return cls._compute_metrics(scale)["row_width"]

    @classmethod
    def rowHeight(cls, scale=1.0):   # ← 追加
        return cls._compute_metrics(scale)["row_height"]

    @classmethod
    def railZoneWidth(cls, scale=1.0):   # ← 追加。SubMenuPanelの路線ライン描画で必要
        return cls._compute_metrics(scale)["rail_zone_width"]

    def sizeScale(self):   # ← 追加
        return self._size_scale

    def setSubmenuDirection(self, direction):
        if direction == self._submenu_direction:
            return
        self._submenu_direction = direction
        self.update()

    def _content_rect(self):
        m = self._m
        return QRect(m["rail_zone_width"], 0, m["content_width"], m["row_height"])

    def _rail_rect(self):
        m = self._m
        return QRect(0, 0, m["rail_zone_width"], m["row_height"])

    def hitTest(self, local_point):
        if self._compact:
            return "back" if self.rect().contains(local_point) else None
        if self._rail_rect().contains(local_point):
            return "back"
        if self._content_rect().contains(local_point):
            return "forward"
        return None

    def setMarkingZone(self, zone):
        self._apply_zone_state(zone)

    def setColor(self, color):   # ← 追加
        self._color_override = QColor(color) if color else None
        self.update()

    def _apply_zone_state(self, zone):
        card_hover = (zone == "forward")
        rail_hover = (zone == "back")
        changed = (card_hover != self._is_hovered) or (rail_hover != self._rail_hovered)
        self._is_hovered = card_hover
        self._rail_hovered = rail_hover
        if changed:
            self.update()

    def _effective_scale(self):
        return self._scale * (self.MARKING_HOVER_SCALE if self._is_hovered else 1.0)

    def setCompact(self, compact):
        if compact == self._compact:
            return
        self._compact = compact

        width = self._m["rail_zone_width"] if compact else self._m["row_width"]
        self.setFixedSize(width, self._m["row_height"])

        self.setAttribute(Qt.WA_TransparentForMouseEvents, compact)
        self.update()

    def leaveEvent(self, event):
        self._apply_zone_state(None)
        self.hoverMoved.emit(None)
        super(SubMenuRow, self).leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self._right_press_pos = event.pos()   # ← 変更
            self._right_is_dragging = False
            event.accept()
            return

        if self._content_rect().contains(event.pos()):
            self._is_pressed = True
            self._press_pos = event.pos()
        self.update()
        super(SubMenuRow, self).mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.RightButton:
            if self._right_press_pos is not None:
                pos = event.pos()
                delta = pos - self._right_press_pos
                distance = (delta.x() ** 2 + delta.y() ** 2) ** 0.5

                if not self._right_is_dragging and distance > self.CLICK_DRAG_TOLERANCE:
                    self._right_is_dragging = True
                    self.markingPressed.emit()

                if self._right_is_dragging:
                    self.markingMoved.emit(self._get_event_global_pos(event))
            return

        zone = self.hitTest(event.pos())
        self._apply_zone_state(zone)
        self.hoverMoved.emit(self._get_event_global_pos(event))
        super(SubMenuRow, self).mouseMoveEvent(event)

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

        moved_too_far = False
        if press_pos is not None:
            delta = event.pos() - press_pos
            distance = (delta.x() ** 2 + delta.y() ** 2) ** 0.5
            moved_too_far = distance > self.CLICK_DRAG_TOLERANCE

        if was_pressed and not moved_too_far and self._content_rect().contains(event.pos()):
            if self._has_submenu:
                self.setActive(not self._is_active)
            self.clicked.emit()

        self.update()
        super(SubMenuRow, self).mouseReleaseEvent(event)
        
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

    def isActive(self):
        return self._is_active

    def _load_icon(self, icon):
        if icon is None:
            return None
        size = self._m["icon_size"]   # ← 変更。ICON_SIZEから
        pixmap = QIcon(icon).pixmap(size, size)
        if pixmap.isNull():
            return None
        return pixmap

    def _base_color(self):
        if self._is_active:
            return theme.Theme.accentColor()   # ← 変更
        if self._is_hovered:
            return theme.Theme.accentColorSoft() 
        if self._color_override is not None:   # ← 追加
            return self._color_override
        return theme.Theme.baseColor()   # ← 変更

    def _current_color(self):
        color = self._base_color()
        if self._is_pressed:
            return color.darker(self.PRESSED_DARKEN)
        return color

    def _rail_dot_color(self):
        if self._is_active:
            return theme.Theme.accentColor()   # ← 変更
        if self._rail_hovered:
            return theme.Theme.accentColorSoft() 
        return self.RAIL_DOT_NORMAL_COLOR

    def paintEvent(self, event):
        m = self._m
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setOpacity(self._opacity)

        if self._compact:
            self._draw_rail_dot(painter)
            return

        content_rect = self._content_rect()
        effective_scale = self._effective_scale()

        if effective_scale != 1.0:
            painter.save()
            center = content_rect.center()
            painter.translate(center)
            painter.scale(effective_scale, effective_scale)
            painter.translate(-center)

        if self._has_submenu:
            self._draw_stack_peek(painter, content_rect)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self._current_color()))
        painter.drawRoundedRect(content_rect, m["corner_radius"], m["corner_radius"])   # ← 変更

        icon_rect = QRect(
            content_rect.x() + m["icon_margin"],
            content_rect.y() + (m["row_height"] - m["icon_size"]) // 2,
            m["icon_size"],
            m["icon_size"]
        )

        if self._icon_pixmap is not None:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(self.ICON_CHIP_COLOR))
            painter.drawEllipse(QPointF(icon_rect.center()), m["icon_chip_radius"], m["icon_chip_radius"])

            offset_x = icon_rect.x() + (icon_rect.width() - self._icon_pixmap.width()) / 2    # ← 追加
            offset_y = icon_rect.y() + (icon_rect.height() - self._icon_pixmap.height()) / 2   # ← 追加
            painter.drawPixmap(int(offset_x), int(offset_y), self._icon_pixmap)   # ← 変更。中心揃えの座標を使う

        text_right_margin = m["icon_margin"]
        if self._has_submenu:
            text_right_margin = m["icon_margin"] + m["stack_peek_width"]

        text_rect = content_rect.adjusted(
            m["icon_margin"] * 2 + m["icon_size"], 0, -text_right_margin, 0
        )
        painter.setPen(self.TEXT_COLOR)
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, self._label)

        if effective_scale != 1.0:
            painter.restore()

        self._draw_rail_dot(painter)

    def _draw_stack_peek(self, painter, content_rect):
        m = self._m
        peek_color = QColor(self._current_color())
        peek_color.setAlpha(self.STACK_ALPHA)

        top = content_rect.y() + m["stack_inset_top"]
        height = content_rect.height() - m["stack_inset_top"] * 2

        if self._submenu_direction == "left":
            peek_rect = QRect(
                content_rect.x() - m["stack_peek_width"],
                top,
                m["corner_radius"] + m["stack_peek_width"],
                height
            )
        else:
            peek_rect = QRect(
                content_rect.right() - m["corner_radius"],
                top,
                m["corner_radius"] + m["stack_peek_width"],
                height
            )

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(peek_color))
        painter.drawRoundedRect(peek_rect, m["corner_radius"], m["corner_radius"])

    def _draw_rail_dot(self, painter):
        m = self._m
        x = m["rail_zone_width"] / 2.0
        y = m["row_height"] / 2.0

        painter.setPen(QPen(self.RAIL_DOT_BORDER_COLOR, m["rail_dot_border_width"]))
        painter.setBrush(QBrush(self._rail_dot_color()))
        painter.drawEllipse(QPointF(x, y), m["rail_dot_radius"], m["rail_dot_radius"])

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

    