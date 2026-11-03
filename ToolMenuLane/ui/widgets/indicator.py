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

__all__ = ["Indicator"]


class Indicator(QWidget):

    DOT_DIAMETER  = 6
    DOT_SPACING   = 6
    NORMAL_COLOR  = QColor(255, 255, 255, 120)
    ACTIVE_COLOR  = QColor(255, 215, 0)

    def __init__(self, orientation=Qt.Vertical, dot_scale=1.0, parent=None):   # ← dot_scale追加
        super(Indicator, self).__init__(parent)
        self._orientation = orientation
        self._dot_scale = dot_scale   # ← 追加
        self._effective_diameter = max(2, int(round(self.DOT_DIAMETER * dot_scale)))   # ← 追加
        self._effective_spacing = max(1, int(round(self.DOT_SPACING * dot_scale)))     # ← 追加
        self._count = 0
        self._current_index = 0
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._update_fixed_size()

    def setDotScale(self, scale):   # ← 追加
        if scale == self._dot_scale:
            return
        self._dot_scale = scale
        self._effective_diameter = max(2, int(round(self.DOT_DIAMETER * scale)))
        self._effective_spacing = max(1, int(round(self.DOT_SPACING * scale)))
        self._update_fixed_size()
        self.update()

    def setOrientation(self, orientation):
        if orientation == self._orientation:
            return
        self._orientation = orientation
        self._update_fixed_size()
        self.update()

    def setCount(self, count):
        if count == self._count:
            return
        self._count = count
        self._current_index = min(self._current_index, max(0, count - 1))
        self._update_fixed_size()
        self.update()

    def setCurrentIndex(self, index):
        if self._count == 0:
            return
        clamped = max(0, min(index, self._count - 1))
        if clamped != self._current_index:
            self._current_index = clamped
            self.update()

    def _update_fixed_size(self):
        d = self._effective_diameter   # ← 変更。DOT_DIAMETERから
        s = self._effective_spacing     # ← 変更。DOT_SPACINGから
        length = self._count * d + max(0, self._count - 1) * s
        length = max(length, d)

        if self._orientation == Qt.Vertical:
            self.setFixedSize(d, length)
        else:
            self.setFixedSize(length, d)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)

        d = self._effective_diameter   # ← 変更
        s = self._effective_spacing     # ← 変更

        offset = 0
        for i in range(self._count):
            color = theme.Theme.accentColor() if i == self._current_index else self.NORMAL_COLOR
            painter.setBrush(QBrush(color))

            if self._orientation == Qt.Vertical:
                rect = QRect(0, offset, d, d)
            else:
                rect = QRect(offset, 0, d, d)

            painter.drawEllipse(rect)
            offset += d + s

            