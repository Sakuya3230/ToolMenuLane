# -*- coding: utf-8 -*-

try:
    from PySide6.QtCore import *
except ImportError:
    from PySide2.QtCore import *

from . import donut_button
from . import scrollable_area


__all__ = ["MainMenuArea"]


class MainMenuArea(scrollable_area.ScrollableArea):

    DEFAULT_VIEWPORT_SIZE = 220

    def __init__(self, orientation=Qt.Vertical, viewport_size=None, spacing=None,
                 button_scale=1.0, parent=None):   # ← button_scale追加
        self._button_scale = button_scale   # ← 追加
        super(MainMenuArea, self).__init__(
            orientation=orientation,
            viewport_size=viewport_size or self.DEFAULT_VIEWPORT_SIZE,
            cross_size=donut_button.DonutButton.totalSize(button_scale),   # ← 変更。scaleを渡す
            parent=parent
        )
        if spacing is not None:
            self.setSpacing(spacing)

    def addButton(self, icon=None, label="", color=None):   # ← label追加
        button = donut_button.DonutButton(
            icon, size_scale=self._button_scale, color=color, parent=self.contentWidget()   # ← color追加
        )
        button.setLabel(label)   # ← 追加
        return self.addItem(button)

    def setButtonScale(self, scale):   # ← 追加
        """次にaddButton()する時から適用される倍率を変更する。
        既に追加済みのボタンは作り直されないため、呼び出し側で
        clearItems()してから使うことを想定している"""
        self._button_scale = scale
        self.setCrossSize(donut_button.DonutButton.totalSize(scale))

