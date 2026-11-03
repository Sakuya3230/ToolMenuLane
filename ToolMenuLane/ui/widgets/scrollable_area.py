# -*- coding: utf-8 -*-

import time

try:
    from PySide6.QtWidgets import *
    from PySide6.QtGui import *
    from PySide6.QtCore import *
except ImportError:
    from PySide2.QtWidgets import *
    from PySide2.QtGui import *
    from PySide2.QtCore import *

from .edge_fade_effect import EdgeFadeEffect

__all__ = ["ScrollableArea"]


class ScrollableArea(QWidget):

    DEFAULT_SPACING = 8
    WHEEL_STEP       = 40

    INERTIA_FRICTION       = 0.9    # ← 追加。1tickごとに速度をこの割合まで減衰させる
    INERTIA_MIN_VELOCITY   = 0.02     # ← 追加。この速度(px/ms)を下回ったら停止
    INERTIA_INTERVAL        = 16       # ← 追加。ミリ秒単位のタイマー間隔(約60fps)

    AUTO_SCROLL_MARGIN    = 24   # ← 追加。端からこの距離以内でオートスクロール発動
    AUTO_SCROLL_MAX_SPEED   = 12   # ← 追加。最大スクロール速度(px/tick)
    AUTO_SCROLL_INTERVAL     = 16    # ← 追加

    scrollOffsetChanged = Signal(int)
    currentIndexChanged  = Signal(int)

    def __init__(self, orientation=Qt.Vertical, viewport_size=220, cross_size=48, parent=None):
        super(ScrollableArea, self).__init__(parent)
        self._orientation = orientation
        self._requested_viewport_size = viewport_size
        self._viewport_size = viewport_size
        self._cross_size = cross_size
        self._items = []
        self._scroll_offset = 0
        self._current_index = 0
        self._spacing = self.DEFAULT_SPACING           # ← 追加
        self._inertia_enabled = True          

        self._is_dragging = False
        self._drag_start_pos = None
        self._drag_start_offset = None

        self._velocity = 0.0            
        self._last_move_time = None     
        self._last_scroll_offset = 0    

        self._inertia_timer = QTimer(self)  
        self._inertia_timer.setInterval(self.INERTIA_INTERVAL)
        self._inertia_timer.timeout.connect(self._on_inertia_tick)

        self._auto_scroll_timer = QTimer(self)   # ← 追加
        self._auto_scroll_timer.setInterval(self.AUTO_SCROLL_INTERVAL)   # ← 追加
        self._auto_scroll_timer.timeout.connect(self._on_auto_scroll_tick)   # ← 追加
        self._auto_scroll_speed = 0   # ← 追加

        self._content = self._create_content_widget()
        self._content.move(0, 0)

        self._edge_fade = EdgeFadeEffect(orientation=self._orientation) 
        self.setGraphicsEffect(self._edge_fade)       

        self._setup_fixed_size()

    def wheelEvent(self, event):
        angle = event.angleDelta().y()
        step = self.WHEEL_STEP if angle > 0 else -self.WHEEL_STEP
        self._set_scroll_offset(self._scroll_offset + step)

    def mousePressEvent(self, event):
        self._inertia_timer.stop()   # ← 追加。ドラッグを再開したら慣性は打ち切る

        self._is_dragging = True
        self._drag_start_pos = self._get_event_global_pos(event)
        self._drag_start_offset = self._scroll_offset

        self._velocity = 0.0                      # ← 追加
        self._last_move_time = time.time()          # ← 追加
        self._last_scroll_offset = self._scroll_offset   # ← 追加

        super(ScrollableArea, self).mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._is_dragging and self._drag_start_pos is not None:
            current_pos = self._get_event_global_pos(event)
            delta = current_pos - self._drag_start_pos

            if self._orientation == Qt.Vertical:
                candidate = self._drag_start_offset + delta.y()
            else:
                candidate = self._drag_start_offset + delta.x()

            self._set_scroll_offset(candidate)

            if self._inertia_enabled:   # ← 追加。無効時は速度計測自体を省略
                now = time.time()
                elapsed_ms = (now - self._last_move_time) * 1000.0 if self._last_move_time else 0
                if elapsed_ms > 0:
                    self._velocity = (self._scroll_offset - self._last_scroll_offset) / elapsed_ms
                self._last_move_time = now
                self._last_scroll_offset = self._scroll_offset

        super(ScrollableArea, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._is_dragging = False
        self._drag_start_pos = None
        self._drag_start_offset = None

        if self._inertia_enabled and abs(self._velocity) > self.INERTIA_MIN_VELOCITY:   # ← 変更
            self._inertia_timer.start()

        super(ScrollableArea, self).mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 1))

    # ------------------------------
    # 
    # ------------------------------
    def items(self):
        return list(self._items)

    def orientation(self):
        return self._orientation

    def setOrientation(self, orientation):
        if orientation == self._orientation:
            return
        self._orientation = orientation
        self._edge_fade.setOrientation(orientation)
        self._scroll_offset = 0
        self._setup_fixed_size()
        self._reflow_positions()
        self.update()

    def viewportSize(self):
        return self._requested_viewport_size

    def setViewportSize(self, size):
        if size == self._requested_viewport_size:
            return
        self._requested_viewport_size = size
        self._apply_clamped_viewport_size()

    def contentWidget(self):
        return self._content

    def addItem(self, widget):
        widget.setParent(self._content)
        widget.show()
        self._items.append(widget)
        self._reflow_positions()
        return widget

    def clearItems(self):
        for item in list(self._items):
            item.setParent(None)
            item.deleteLater()

        self._items = []
        self._scroll_offset = 0
        self._current_index = 0

        if self._orientation == Qt.Vertical:
            self._content.setFixedSize(self._cross_size, 0)
        else:
            self._content.setFixedSize(0, self._cross_size)

        self._apply_scroll_offset()
        self.currentIndexChanged.emit(self._current_index)

    def itemGeometryInArea(self, item):
        """指定したitemの、このArea自身を基準にした現在の矩形(スクロール反映済み)を返す"""
        content_pos = self._content.pos()
        local_pos = item.pos() + content_pos
        return QRect(local_pos, item.size())

    def scrollOffset(self):
        return self._scroll_offset

    def maxScrollOffset(self):
        return self._max_scroll_offset()

    def itemCount(self):
        return len(self._items)

    def currentIndex(self):
        return self._current_index

    def viewportSize(self):
        return self._viewport_size

    def setViewportSize(self, size):
        if size == self._viewport_size:
            return
        self._viewport_size = size
        self._setup_fixed_size()
        self._set_scroll_offset(self._scroll_offset)
        self.update()

    def setSpacing(self, spacing):   # ← 追加
        if spacing == self._spacing:
            return
        self._spacing = spacing
        self._reflow_positions()

    def setInertiaEnabled(self, enabled):   # ← 追加
        self._inertia_enabled = enabled
        if not enabled:
            self._stop_auto_and_inertia_for_disable()   # ← 追加。無効化した瞬間に動いていれば止める

    def _stop_auto_and_inertia_for_disable(self):   # ← 追加
        self._inertia_timer.stop()
        self._velocity = 0.0

    def reflowPositions(self):
        """現在のアイテム一覧を、決まったレイアウトルールで再配置する。
        アニメーションの中断等でpos()が本来の位置からズレている場合の、
        正しい位置への強制的な復元としても使う"""
        self._reflow_positions()

    def itemGeometryInArea(self, item):
        """指定したitemの、このArea自身を基準にした現在の矩形(スクロール反映済み)を返す"""
        content_pos = self._content.pos()
        local_pos = item.pos() + content_pos
        return QRect(local_pos, item.size())

    def setCrossSize(self, size):   # ← 追加
        if size == self._cross_size:
            return
        self._cross_size = size
        self._setup_fixed_size()
        self._reflow_positions()

    def setAutoScrollTarget(self, global_pos):   # ← 追加
        """マーキングドラッグ中のグローバル座標を渡し、端に近ければオートスクロールを開始する。
        端から離れていれば停止する。global_pos=Noneで強制停止"""
        if global_pos is None:
            self._stop_auto_scroll()
            return

        local = self.mapFromGlobal(global_pos)

        if self._orientation == Qt.Vertical:
            pos_in_axis = local.y()
            length = self.height()
        else:
            pos_in_axis = local.x()
            length = self.width()

        margin = self.AUTO_SCROLL_MARGIN

        if pos_in_axis < margin:
            fraction = (margin - pos_in_axis) / float(margin)
            self._start_auto_scroll(int(self.AUTO_SCROLL_MAX_SPEED * min(1.0, fraction)))
        elif pos_in_axis > length - margin:
            fraction = (pos_in_axis - (length - margin)) / float(margin)
            self._start_auto_scroll(-int(self.AUTO_SCROLL_MAX_SPEED * min(1.0, fraction)))
        else:
            self._stop_auto_scroll()
        
    # ------------------------------
    # 
    # ------------------------------
    def _create_content_widget(self):
        """中身用Widgetの生成方法。サブクラスでoverrideすることで、
        独自の背景描画(路線ラインなど)を持つ中身Widgetに差し替えられる"""
        return QWidget(self)

    def _setup_fixed_size(self):
        if self._orientation == Qt.Vertical:
            self.setFixedSize(self._cross_size, self._viewport_size)
        else:
            self.setFixedSize(self._viewport_size, self._cross_size)

    def _content_length(self):
        """現在の中身(全アイテム)を並べた時の、スクロール方向の全長"""
        if not self._items:
            return 0
        if self._orientation == Qt.Vertical:
            return self._content.height()
        return self._content.width()

    def _apply_clamped_viewport_size(self):
        content_length = self._content_length()
        new_size = min(self._requested_viewport_size, content_length) if content_length > 0 else self._requested_viewport_size   # ← 変更。EDGE_MARGIN関連の計算を削除

        if new_size == self._viewport_size:
            return

        self._viewport_size = new_size
        self._setup_fixed_size()

    def _setup_fixed_size(self):
        if self._orientation == Qt.Vertical:
            self.setFixedSize(self._cross_size, self._viewport_size)
        else:
            self.setFixedSize(self._viewport_size, self._cross_size)

    def _reflow_positions(self):
        if not self._items:
            self._resize_content(0)
            return

        leading_padding = max(self._item_layout_offset(item) for item in self._items)
        trailing_padding = max(
            self._item_total_length(item) - self._item_layout_offset(item) - self._item_layout_size(item)
            for item in self._items
        )

        offset = leading_padding
        for item in self._items:
            layout_size = self._item_layout_size(item)
            layout_offset = self._item_layout_offset(item)

            if self._orientation == Qt.Vertical:
                item.move(0, offset - layout_offset)
                offset += layout_size + self._spacing   # ← 変更。DEFAULT_SPACINGから_spacingへ
            else:
                item.move(offset - layout_offset, 0)
                offset += layout_size + self._spacing   # ← 変更

        total_length = offset - self._spacing + trailing_padding   # ← 変更
        self._resize_content(total_length)

    def _resize_content(self, content_length):   # ← 変更。引数名と中身を調整
        if not self._items:
            return

        if self._orientation == Qt.Vertical:
            self._content.setFixedSize(self._cross_size, content_length)   # ← 変更。減算処理を削除(既に計算済みのため)
        else:
            self._content.setFixedSize(content_length, self._cross_size)   # ← 変更

        self._apply_clamped_viewport_size()
        self._set_scroll_offset(self._scroll_offset)

    def _max_scroll_offset(self):
        if self._orientation == Qt.Vertical:
            return max(0, self._content.height() - self.height())   # ← 変更。visible_length()からself.height()へ戻す
        return max(0, self._content.width() - self.width())    

    def _set_scroll_offset(self, candidate_offset):
        previous_offset = self._scroll_offset

        max_offset = self._max_scroll_offset()
        new_offset = min(0, max(candidate_offset, -max_offset))
        offset_changed = new_offset != previous_offset

        self._scroll_offset = new_offset
        self._apply_scroll_offset()
        self._update_edge_fade()
        self._update_edge_fade_enabled(max_offset)   # ← 追加

        if offset_changed:
            self.scrollOffsetChanged.emit(self._scroll_offset)

        new_index = self._compute_current_index()
        if new_index != self._current_index:
            self._current_index = new_index
            self.currentIndexChanged.emit(self._current_index)

        return offset_changed

    def _apply_scroll_offset(self):
        if self._orientation == Qt.Vertical:
            self._content.move(0, self._scroll_offset)   # ← 変更。EDGE_MARGINを含まないシンプルな形に戻す
        else:
            self._content.move(self._scroll_offset, 0)   # ← 変更

    def _get_event_global_pos(self, event):
        if hasattr(event, "globalPosition"):
            point = event.globalPosition()
            return QPoint(int(point.x()), int(point.y()))
        return event.globalPos()

    def _compute_current_index(self):
        if not self._items:
            return 0

        max_offset = self._max_scroll_offset()
        if max_offset <= 0:
            return 0

        fraction = (-self._scroll_offset) / float(max_offset)
        index = int(round(fraction * (len(self._items) - 1)))
        return max(0, min(index, len(self._items) - 1))

    def _on_inertia_tick(self):
        before = self._scroll_offset
        candidate = int(round(self._scroll_offset + self._velocity * self.INERTIA_INTERVAL))
        changed = self._set_scroll_offset(candidate)

        if not changed and self._scroll_offset == before:
            self._inertia_timer.stop()
            self._velocity = 0.0
            return

        self._velocity *= self.INERTIA_FRICTION
        if abs(self._velocity) <= self.INERTIA_MIN_VELOCITY:
            self._inertia_timer.stop()
            self._velocity = 0.0

    def _update_edge_fade(self):
        if self._orientation == Qt.Vertical:
            viewport_length = self.height()   # ← 変更。visible_length()からself.height()へ戻す
        else:
            viewport_length = self.width()     # ← 変更

        for item in self._items:
            rect = self.itemGeometryInArea(item)

            if self._orientation == Qt.Vertical:
                item_start = rect.y()   # ← 変更。EDGE_MARGINを引く処理を削除
                item_length = rect.height()
            else:
                item_start = rect.x()   # ← 変更
                item_length = rect.width()

            item_end = item_start + item_length
            overlap = min(item_end, viewport_length) - max(item_start, 0)
            overlap = max(0, overlap)

            fraction = overlap / float(item_length) if item_length > 0 else 0.0
            item.opacity = fraction

    def _apply_content_margin_position(self):   # ← 追加
        """_contentの、余白を考慮した交差軸方向の位置を設定する。
        主軸方向(スクロールする方向)の位置は_apply_scroll_offsetが管理するので、
        ここでは交差軸方向の位置(常に固定)だけ扱う"""
        if self._orientation == Qt.Vertical:
            self._content.move(0, self._content.y())
        else:
            self._content.move(self._content.x(), 0)

    def _visible_length(self):   # ← 追加
        """余白を除いた、実際にアイテムが表示・スクロールされる領域の長さ"""
        return max(0, self._viewport_size - self.EDGE_MARGIN * 2)

    def _update_edge_fade_enabled(self, max_offset):   # ← 追加
        """スクロールが端(始点/終点)に到達している場合、その端のフェードを無効化する。
        端でない場合は有効化し、境界のアイテムが自然にグラデーションでフェードするようにする"""
        at_start = self._scroll_offset >= 0
        at_end = self._scroll_offset <= -max_offset

        self._edge_fade.setStartFadeEnabled(not at_start)
        self._edge_fade.setEndFadeEnabled(not at_end)

    def _start_auto_scroll(self, speed):   # ← 追加
        self._auto_scroll_speed = speed
        if not self._auto_scroll_timer.isActive():
            self._auto_scroll_timer.start()

    def _stop_auto_scroll(self):   # ← 追加
        self._auto_scroll_timer.stop()
        self._auto_scroll_speed = 0

    def _on_auto_scroll_tick(self):   # ← 追加
        self._set_scroll_offset(self._scroll_offset + self._auto_scroll_speed)

    def _item_layout_size(self, item):   # ← 追加
        """レイアウト計算(間隔)に使う、アイテムの"見た目上のサイズ"。
        アイテムがlayoutSize()を持っていればそれを使い、無ければ実際のWidgetサイズを使う"""
        getter = getattr(item, "layoutSize", None)
        if callable(getter):
            return getter()
        return item.height() if self._orientation == Qt.Vertical else item.width()

    def _item_layout_offset(self, item):   # ← 追加
        """アイテムの実際のWidget原点から、"見た目のサイズ"が始まる位置までのオフセット。
        アイテムがlayoutOffset()を持っていればそれを使い、無ければ0(オフセットなし)"""
        getter = getattr(item, "layoutOffset", None)
        if callable(getter):
            return getter()
        return 0

    def _item_total_length(self, item):   # ← 追加。アイテムの実際のWidgetサイズ(余白込み)
        return item.height() if self._orientation == Qt.Vertical else item.width()











    