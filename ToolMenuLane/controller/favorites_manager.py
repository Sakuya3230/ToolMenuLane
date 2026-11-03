# -*- coding: utf-8 -*-

try:
    from PySide6.QtCore import *
except ImportError:
    from PySide2.QtCore import *


__all__ = ["FavoritesManager"]


class FavoritesManager(QObject):

    MAX_FAVORITES = 8

    changed = Signal()

    def __init__(self, parent=None):
        super(FavoritesManager, self).__init__(parent)
        self._entries = []   # [{"profile_id": str, "item_id": str}, ...] 順序が並び順

    def entries(self):
        return list(self._entries)

    def isFavorite(self, profile_id, item_id):
        return any(e["profile_id"] == profile_id and e["item_id"] == item_id for e in self._entries)

    def canAdd(self):
        return len(self._entries) < self.MAX_FAVORITES

    def addFavorite(self, profile_id, item_id):
        if self.isFavorite(profile_id, item_id) or not self.canAdd():
            return False
        self._entries.append({"profile_id": profile_id, "item_id": item_id})
        self.changed.emit()
        return True

    def removeFavorite(self, profile_id, item_id):
        before = len(self._entries)
        self._entries = [
            e for e in self._entries
            if not (e["profile_id"] == profile_id and e["item_id"] == item_id)
        ]
        if len(self._entries) != before:
            self.changed.emit()
            return True
        return False

    def moveFavorite(self, from_index, to_index):
        """ラジアル上でのドラッグ入れ替え用。from_indexの要素をto_indexの位置へ移動する"""
        if not (0 <= from_index < len(self._entries)):
            return
        if not (0 <= to_index < len(self._entries)):
            return
        entry = self._entries.pop(from_index)
        self._entries.insert(to_index, entry)
        self.changed.emit()

    def swapFavorites(self, index_a, index_b):
        """ラジアル上のドラッグで2つの位置を入れ替える(移動というより交換)"""
        if not (0 <= index_a < len(self._entries)):
            return
        if not (0 <= index_b < len(self._entries)):
            return
        self._entries[index_a], self._entries[index_b] = self._entries[index_b], self._entries[index_a]
        self.changed.emit()

    def loadEntries(self, entries):
        self._entries = [
            {"profile_id": e.get("profile_id"), "item_id": e.get("item_id")}
            for e in (entries or [])
            if e.get("profile_id") and e.get("item_id")
        ][:self.MAX_FAVORITES]
        self.changed.emit()

    def toStateList(self):
        return self.entries()