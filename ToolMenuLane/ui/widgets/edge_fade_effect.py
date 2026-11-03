# -*- coding: utf-8 -*-

try:
    from PySide6.QtWidgets import *
    from PySide6.QtGui import *
    from PySide6.QtCore import *
except ImportError:
    from PySide2.QtWidgets import *
    from PySide2.QtGui import *
    from PySide2.QtCore import *


__all__ = ["EdgeFadeEffect"]


class EdgeFadeEffect(QGraphicsEffect):

    DEFAULT_FADE_LENGTH = 24

    def __init__(self, orientation=Qt.Vertical, fade_length=DEFAULT_FADE_LENGTH, parent=None):
        super(EdgeFadeEffect, self).__init__(parent)
        self._orientation = orientation
        self._fade_length = fade_length
        self._start_fade_enabled = True 
        self._end_fade_enabled = True 

    def setOrientation(self, orientation):
        if orientation == self._orientation:
            return
        self._orientation = orientation
        self.update()

    def setFadeLength(self, length):
        self._fade_length = length
        self.update()

    def setStartFadeEnabled(self, enabled):
        if enabled == self._start_fade_enabled:
            return
        self._start_fade_enabled = enabled
        self.update()

    def setEndFadeEnabled(self, enabled): 
        if enabled == self._end_fade_enabled:
            return
        self._end_fade_enabled = enabled
        self.update()

    def draw(self, painter):
        result = self.sourcePixmap(
            Qt.LogicalCoordinates,
            mode=QGraphicsEffect.PadToEffectiveBoundingRect
        )

        if isinstance(result, tuple):
            pixmap, offset = result
        else:
            pixmap = result
            offset = self.sourceBoundingRect(Qt.LogicalCoordinates).topLeft().toPoint()

        if pixmap.isNull():
            return

        painter.save()
        painter.drawPixmap(offset, pixmap)

        width = pixmap.width()
        height = pixmap.height()
        gradient = QLinearGradient()

        if self._orientation == Qt.Vertical:
            length = height
            gradient.setStart(0, 0)
            gradient.setFinalStop(0, length)
        else:
            length = width
            gradient.setStart(0, 0)
            gradient.setFinalStop(length, 0)

        if length <= 0:
            painter.restore()
            return

        fade_fraction = min(0.49, self._fade_length / float(length))

        transparent = QColor(0, 0, 0, 0)
        opaque = QColor(0, 0, 0, 255)

        start_color = transparent if self._start_fade_enabled else opaque 
        end_color = transparent if self._end_fade_enabled else opaque  

        gradient.setColorAt(0.0, start_color)
        gradient.setColorAt(fade_fraction, opaque)
        gradient.setColorAt(1.0 - fade_fraction, opaque)
        gradient.setColorAt(1.0, end_color)

        painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        painter.fillRect(QRectF(offset, QSizeF(width, height)), QBrush(gradient))

        painter.restore()



