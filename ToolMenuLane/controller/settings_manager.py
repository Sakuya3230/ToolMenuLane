# -*- coding: utf-8 -*-

try:
    from PySide6.QtCore import *
except ImportError:
    from PySide2.QtCore import *


__all__ = ["SettingsManager"]


class SettingsManager(QObject):

    MIN_SCALE = 0.6   # ← 追加
    MAX_SCALE = 1.6   # ← 追加

    valueChanged = Signal(str, object)

    def __init__(self, initial_values, defaults=None, parent=None):
        super(SettingsManager, self).__init__(parent)
        self._values = dict(initial_values)
        self._defaults = dict(defaults) if defaults else dict(initial_values)
        self._snapshot = None

    def get(self, key, default=None):
        return self._values.get(key, default)

    def values(self):
        return dict(self._values)

    def defaultValue(self, key):
        return self._defaults.get(key)

    def setValue(self, key, value, emit=True):
        if self._values.get(key) == value:
            return
        self._values[key] = value
        if emit:
            self.valueChanged.emit(key, value)

    def clampScale(self, value):   # ← 追加
        return max(self.MIN_SCALE, min(self.MAX_SCALE, value))

    def effectiveMainScale(self):   # ← 追加
        override = self._values.get("main_scale")
        base = override if override is not None else self._values.get("global_scale", 1.0)
        return self.clampScale(base)

    def effectiveSubmenuScale(self):   # ← 追加
        override = self._values.get("submenu_scale")
        base = override if override is not None else self._values.get("global_scale", 1.0)
        return self.clampScale(base)

    def beginEdit(self):
        self._snapshot = dict(self._values)

    def apply(self):
        self._snapshot = None

    def cancel(self):
        if self._snapshot is None:
            return

        before = dict(self._values)
        self._values = dict(self._snapshot)
        self._snapshot = None

        for key, value in self._values.items():
            if before.get(key) != value:
                self.valueChanged.emit(key, value)

    def resetToDefaults(self):
        for key, value in self._defaults.items():
            self.setValue(key, value)

            