# -*- coding: utf-8 -*-

import math

try:
    from PySide6.QtWidgets import *
    from PySide6.QtCore import *
except ImportError:
    from PySide2.QtWidgets import *
    from PySide2.QtCore import *

from . import donut_button


__all__ = ["FavoritesRadialMenu"]


class FavoritesRadialMenu(QWidget):

    RING_RADIUS = 100
    START_ANGLE = -math.pi / 2

    reorderRequested = Signal(int, int)   # ← 追加。from_index, to_index (入れ替え)
    removeRequested   = Signal(str, str)    # ← 追加。profile_id, item_id

    def __init__(self, parent=None):
        super(FavoritesRadialMenu, self).__init__(parent)
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        self._entries = []
        self._hovered_index = None
        self._edit_mode = False   # ← 追加

        self._drag_index = None                # ← 追加
        self._drag_start_global = None          # ← 追加
        self._drag_button_start_pos = None       # ← 追加

        button_diameter = donut_button.DonutButton.totalSize()
        diameter = int(self.RING_RADIUS * 2 + button_diameter)
        self.setFixedSize(diameter, diameter)

    def centerOffset(self):
        return QPoint(self.width() // 2, self.height() // 2)

    def setEditMode(self, enabled):   # ← 追加
        self._edit_mode = enabled
        self.setAttribute(Qt.WA_TransparentForMouseEvents, not enabled)   # ← 編集中はWidget自体もイベントを受け取る

        for entry in self._entries:
            button = entry["button"]
            button.setAttribute(Qt.WA_TransparentForMouseEvents, not enabled)
            if enabled:
                button.installEventFilter(self)
            else:
                button.removeEventFilter(self)

    def setFavorites(self, resolved_items):
        for entry in self._entries:
            entry["button"].removeEventFilter(self)   # ← 追加。作り直す前に必ず解除する
            entry["button"].setParent(None)
            entry["button"].deleteLater()
        self._entries = []
        self._hovered_index = None
        self._drag_index = None

        count = len(resolved_items)
        if count == 0:
            return

        center = self.centerOffset()
        angle_step = (2 * math.pi) / count

        for i, data in enumerate(resolved_items):
            button = donut_button.DonutButton(
                icon=data.get("icon"), color=data.get("color"), parent=self
            )
            button.setHasSubmenu(False)
            button.setAttribute(Qt.WA_TransparentForMouseEvents, not self._edit_mode)   # ← 変更
            if self._edit_mode:   # ← 追加
                button.installEventFilter(self)

            angle = self.START_ANGLE + i * angle_step
            x = center.x() + self.RING_RADIUS * math.cos(angle) - button.width() / 2.0
            y = center.y() + self.RING_RADIUS * math.sin(angle) - button.height() / 2.0
            button.move(int(x), int(y))
            button.show()

            self._entries.append({
                "profile_id": data.get("profile_id"),
                "item_id": data.get("item_id"),
                "button": button
            })

    def setHoverPoint(self, local_point):
        new_index = self._index_at(local_point) if local_point is not None else None

        if new_index == self._hovered_index:
            return

        if self._hovered_index is not None:
            self._entries[self._hovered_index]["button"].setMarkingZone(None)

        self._hovered_index = new_index

        if new_index is not None:
            self._entries[new_index]["button"].setMarkingZone("forward")

    def entryAt(self, local_point):
        index = self._index_at(local_point)
        if index is None:
            return None
        return self._entries[index]

    def _index_at(self, local_point):
        if local_point is None or not self._entries:
            return None

        button_radius = donut_button.DonutButton.totalSize() / 2.0
        best_index = None
        best_distance = None

        for i, entry in enumerate(self._entries):
            button = entry["button"]
            center = QPoint(button.x() + button.width() // 2, button.y() + button.height() // 2)
            dx = local_point.x() - center.x()
            dy = local_point.y() - center.y()
            distance = math.hypot(dx, dy)

            if distance <= button_radius:
                if best_distance is None or distance < best_distance:
                    best_distance = distance
                    best_index = i

        return best_index

    def eventFilter(self, obj, event):   # ← 追加
        if not self._edit_mode:
            return False

        index = self._button_index(obj)
        if index is None:
            return False

        event_type = event.type()

        if event_type == QEvent.MouseButtonPress:
            if event.button() == Qt.RightButton:
                entry = self._entries[index]
                self.removeRequested.emit(entry["profile_id"], entry["item_id"])
                return True
            if event.button() == Qt.LeftButton:
                self._drag_index = index
                self._drag_start_global = self._global_pos(event)
                self._drag_button_start_pos = obj.pos()
                obj.raise_()
                return True
            return False

        if event_type == QEvent.MouseMove:
            if self._drag_index == index and (event.buttons() & Qt.LeftButton):
                current_global = self._global_pos(event)
                delta = current_global - self._drag_start_global
                obj.move(self._drag_button_start_pos + delta)
                self._highlight_drop_target(obj)
                return True
            return False

        if event_type == QEvent.MouseButtonRelease:
            if event.button() == Qt.LeftButton and self._drag_index == index:
                target_index = self._nearest_slot_index(obj)
                self._clear_highlight()

                if target_index is not None and target_index != index:
                    self.reorderRequested.emit(index, target_index)
                else:
                    obj.move(self._drag_button_start_pos)

                self._drag_index = None
                self._drag_start_global = None
                self._drag_button_start_pos = None
                return True
            return False

        return False

    def _button_index(self, obj):   # ← 追加
        for i, entry in enumerate(self._entries):
            if entry["button"] is obj:
                return i
        return None

    def _nearest_slot_index(self, dragged_button):   # ← 追加
        dragged_center = dragged_button.geometry().center()
        best_index = None
        best_distance = None

        for i, entry in enumerate(self._entries):
            if entry["button"] is dragged_button:
                continue
            center = entry["button"].geometry().center()
            dx = center.x() - dragged_center.x()
            dy = center.y() - dragged_center.y()
            distance = math.hypot(dx, dy)

            if best_distance is None or distance < best_distance:
                best_distance = distance
                best_index = i

        return best_index

    def _highlight_drop_target(self, dragged_button):   # ← 追加
        target_index = self._nearest_slot_index(dragged_button)
        for i, entry in enumerate(self._entries):
            entry["button"].setMarkingZone("forward" if i == target_index else None)

    def _clear_highlight(self):   # ← 追加
        for entry in self._entries:
            entry["button"].setMarkingZone(None)

    def _global_pos(self, event):   # ← 追加
        if hasattr(event, "globalPosition"):
            point = event.globalPosition()
            return QPoint(int(point.x()), int(point.y()))
        return event.globalPos()

    