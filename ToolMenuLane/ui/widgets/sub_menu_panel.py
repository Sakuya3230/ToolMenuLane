# -*- coding: utf-8 -*-

try:
    from PySide6.QtWidgets import *
    from PySide6.QtGui import *
    from PySide6.QtCore import *
except ImportError:
    from PySide2.QtWidgets import *
    from PySide2.QtGui import *
    from PySide2.QtCore import *

from . import sub_menu_row
from . import scrollable_area


__all__ = ["SubMenuPanel"]


class _RailContent(QWidget):

    RAIL_COLOR = QColor(255, 255, 255, 70)
    RAIL_WIDTH = 2

    def __init__(self, row_scale=1.0, parent=None):   # ← row_scale追加
        super(_RailContent, self).__init__(parent)
        self._row_scale = row_scale   # ← 追加

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        x = sub_menu_row.SubMenuRow.railZoneWidth(self._row_scale) / 2.0   # ← 変更

        pen = QPen(self.RAIL_COLOR, self.RAIL_WIDTH)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.drawLine(QPointF(x, 0), QPointF(x, self.height()))


class SubMenuPanel(scrollable_area.ScrollableArea):

    DEFAULT_VIEWPORT_SIZE = 240
    CLICK_DRAG_TOLERANCE = 6

    collapsedActivated = Signal(object)

    def __init__(self, viewport_size=None, spacing=None, row_scale=1.0, parent=None):   # ← row_scale追加
        self._row_scale = row_scale   # ← 追加。_create_content_widgetより前に必要
        super(SubMenuPanel, self).__init__(
            orientation=Qt.Vertical,
            viewport_size=viewport_size or self.DEFAULT_VIEWPORT_SIZE,
            cross_size=sub_menu_row.SubMenuRow.rowWidth(row_scale),   # ← 変更
            parent=parent
        )
        self._collapsed = False
        self._collapsed_press_pos = None

        if spacing is not None:
            self.setSpacing(spacing)

    def _create_content_widget(self):
        return _RailContent(row_scale=self._row_scale, parent=self)   # ← 変更

    def addRow(self, icon=None, label="", has_submenu=False, color=None):   # ← color追加
        row = sub_menu_row.SubMenuRow(
            icon, label, has_submenu, size_scale=self._row_scale, color=color, parent=self.contentWidget()   # ← color追加
        )
        return self.addItem(row)

    def isCollapsed(self):
        return self._collapsed

    def setCollapsed(self, collapsed):
        if collapsed == self._collapsed:
            return
        self._collapsed = collapsed

        target_width = (
            sub_menu_row.SubMenuRow.railZoneWidth(self._row_scale) if collapsed   # ← 変更
            else sub_menu_row.SubMenuRow.rowWidth(self._row_scale)                # ← 変更
        )
        self.setCrossSize(target_width)

        for row in self.items():
            row.setCompact(collapsed)

        self.update()

    def mousePressEvent(self, event):
        if self._collapsed:
            self._collapsed_press_pos = self._get_event_global_pos(event)
        super(SubMenuPanel, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self._collapsed and self._collapsed_press_pos is not None:
            current = self._get_event_global_pos(event)
            delta = current - self._collapsed_press_pos
            distance = (delta.x() ** 2 + delta.y() ** 2) ** 0.5
            if distance <= self.CLICK_DRAG_TOLERANCE:
                self.collapsedActivated.emit(self)

        self._collapsed_press_pos = None
        super(SubMenuPanel, self).mouseReleaseEvent(event)

    def rowHeight(self):
        return sub_menu_row.SubMenuRow.rowHeight(self._row_scale)