# -*- coding: utf-8 -*-

try:
    from PySide6.QtGui import QColor
except ImportError:
    from PySide2.QtGui import QColor


__all__ = ["Theme"]


class Theme(object):

    DEFAULT_ACCENT_COLOR = "#FFD700"   # 現在の黄色(255,215,0)を16進表記で
    DEFAULT_BASE_COLOR    = "#FFFFFF"

    _accent_color = QColor(DEFAULT_ACCENT_COLOR)
    _base_color = QColor(DEFAULT_BASE_COLOR)

    @classmethod
    def setAccentColor(cls, color):   # ← 追加
        """color: QColor または "#RRGGBB" 形式の文字列"""
        if isinstance(color, QColor):
            cls._accent_color = QColor(color)
        else:
            cls._accent_color = QColor(color)

    @classmethod
    def accentColor(cls):   # ← 追加
        return QColor(cls._accent_color)


    @classmethod
    def accentColorSoft(cls):   # ← 追加。ホバー用の薄い版を自動計算
        color = cls.accentColor()
        h, s, v, a = color.getHsv()
        soft = QColor.fromHsv(h, max(0, int(s * 0.35)), min(255, int(v * 1.05) if v > 0 else 255), a)
        return soft

    @classmethod
    def accentColorText(cls):   # ← 追加
        """16進文字列("#RRGGBB")として取得。設定ダイアログの表示・保存用"""
        return cls.accentColor().name()

    @classmethod
    def setBaseColor(cls, color):   # ← 追加
        cls._base_color = QColor(color)

    @classmethod
    def baseColor(cls):   # ← 追加
        return QColor(cls._base_color)

    @classmethod
    def baseColorText(cls):   # ← 追加
        return cls.baseColor().name()

    