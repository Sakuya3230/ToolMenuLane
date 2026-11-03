# -*- coding: utf-8 -*-

try:
    from PySide6.QtWidgets import *
    from PySide6.QtGui import *
    from PySide6.QtCore import *
except ImportError:
    from PySide2.QtWidgets import *
    from PySide2.QtGui import *
    from PySide2.QtCore import *


__all__ = ["PointerOverlay"]


class PointerOverlay(QWidget):

    POINTER_COLOR = QColor(255, 215, 0)
    DOT_RADIUS    = 4
    LINE_WIDTH    = 2

    def __init__(self, parent=None):
        super(PointerOverlay, self).__init__(parent)
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        self._start = None
        self._current = None

    def setPointer(self, start_local, current_local):
        self._start = start_local
        self._current = current_local
        self.update()

    def clearAndHide(self):
        """バッキングストアに古いラインが残ったまま非表示になるのを防ぐため、
        同期的に空の状態を描画してから隠す"""
        self._start = None
        self._current = None
        self.repaint()   # ← updateではなくrepaint。ここで即座に「何も描かれていない」状態を確定させる
        self.setVisible(False)

    def paintEvent(self, event):
        if self._start is None or self._current is None:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.setPen(QPen(self.POINTER_COLOR, self.LINE_WIDTH))
        painter.drawLine(self._start, self._current)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self.POINTER_COLOR))
        painter.drawEllipse(self._start, self.DOT_RADIUS, self.DOT_RADIUS)