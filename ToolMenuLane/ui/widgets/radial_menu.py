# -*- coding: utf-8 -*-

import math

try:
    from PySide6.QtWidgets import *
    from PySide6.QtGui import *
    from PySide6.QtCore import *
except ImportError:
    from PySide2.QtWidgets import *
    from PySide2.QtGui import *
    from PySide2.QtCore import *

from .. import theme

__all__ = ["RadialMenu"]


class RadialMenu(QWidget):

    INNER_RADIUS   = 55
    OUTER_RADIUS   = 110
    SECTOR_GAP_WIDTH = 5
    CENTER_HOLE_GAP  = 6
    CENTER_CIRCLE_COLOR = QColor(50, 50, 55, 255)   # ← 変更
    CENTER_TEXT_COLOR      = QColor(230, 230, 230)
    SECTOR_ALPHA_MULTIPLIER = 1.0   # ← 変更
    ICON_LABEL_GAP = 0   # ← 追加

    DEFAULT_COLOR  = QColor(90, 90, 90)
    HOVER_BRIGHTEN = 40
    ACTIVE_BORDER_WIDTH = 8
    TEXT_COLOR     = QColor(255, 255, 255)
    ICON_SIZE      = 24

    def __init__(self, parent=None):
        super(RadialMenu, self).__init__(parent)
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        self._sectors = []
        self._start_offset = -math.pi / 2
        self._sector_angle = 0.0
        self._hovered_profile_id = None
        self._active_profile_id = None

        margin = self.ACTIVE_BORDER_WIDTH
        diameter = int(self.OUTER_RADIUS * 2 + margin * 2)
        self.setFixedSize(diameter, diameter)

    def centerOffset(self):
        return QPoint(self.width() // 2, self.height() // 2)

    def setProfiles(self, profiles, current_profile_id=None):
        self._sectors = []
        self._active_profile_id = current_profile_id
        self._hovered_profile_id = None

        count = len(profiles)
        if count == 0:
            self._sector_angle = 0.0
            self.update()
            return

        self._sector_angle = (2 * math.pi) / count
        base_offset = self._start_offset - (self._sector_angle / 2.0)

        for i, profile in enumerate(profiles):
            start = base_offset + i * self._sector_angle
            end = start + self._sector_angle
            self._sectors.append({
                "profile_id": profile.profile_id,
                "label": profile.label,
                "icon": self._load_icon(profile.icon),
                "color": QColor(profile.color) if profile.color else QColor(self.DEFAULT_COLOR),
                "start": start,
                "end": end,
            })

        self.update()

    def _load_icon(self, icon_path):
        if not icon_path:
            return None
        pixmap = QIcon(icon_path).pixmap(self.ICON_SIZE, self.ICON_SIZE)
        return None if pixmap.isNull() else pixmap

    def setHoverPoint(self, point):
        self._hovered_profile_id = self.sectorAt(point) if point is not None else None
        self.update()

    def sectorAt(self, local_point):
        if local_point is None or not self._sectors:
            return None

        dx = local_point.x()
        dy = local_point.y()
        r = math.hypot(dx, dy)
        if r < self.INNER_RADIUS:   # ← 変更後のINNER_RADIUSがそのまま使われる(拡大された中心の穴)
            return None

        angle = math.atan2(dy, dx)
        two_pi = 2 * math.pi
        base_offset = self._start_offset - (self._sector_angle / 2.0)
        rel = (angle - base_offset) % two_pi

        index = int(rel // self._sector_angle)
        index = max(0, min(index, len(self._sectors) - 1))
        return self._sectors[index]["profile_id"]

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        center = QPointF(self.width() / 2.0, self.height() / 2.0)
        painter.translate(center)

        for sector in self._sectors:
            self._paint_sector(painter, sector)

        self._paint_center(painter)

    def _sector_gap_angle(self, radius):   # ← 追加
        """SECTOR_GAP_WIDTH(px)を、指定半径における角度(ラジアン)に変換する。
        半径によって同じpx幅が異なる角度になるため、外周基準で計算する"""
        if radius <= 0:
            return 0.0
        return self.SECTOR_GAP_WIDTH / radius

    def _paint_sector(self, painter, sector):
        inner_radius = self.INNER_RADIUS + self.CENTER_HOLE_GAP

        # 隙間なしのフルサイズでパスを作る
        path = self._build_sector_path(sector["start"], sector["end"], inner_radius)   # ← 変更。half_gap無し

        # 開始角・終了角それぞれの境界に、半径方向へ伸びる矩形を減算して隙間を作る
        path = path.subtracted(self._build_gap_notch(sector["start"], inner_radius))   # ← 追加
        path = path.subtracted(self._build_gap_notch(sector["end"], inner_radius))   # ← 追加

        color = QColor(sector["color"])
        if sector["profile_id"] == self._hovered_profile_id:
            color = color.lighter(100 + self.HOVER_BRIGHTEN)
        color.setAlpha(int(255 * self.SECTOR_ALPHA_MULTIPLIER))

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(color))
        painter.drawPath(path)

        painter.save()
        painter.setClipPath(path)
        self._paint_sector_content(painter, sector, inner_radius)
        painter.restore()

        if sector["profile_id"] == self._active_profile_id:
            self._paint_active_outer_border(painter, sector)

    def _paint_active_outer_border(self, painter, sector):
        rect = QRectF(-self.OUTER_RADIUS, -self.OUTER_RADIUS, self.OUTER_RADIUS * 2, self.OUTER_RADIUS * 2)

        gap_angle = self._sector_gap_angle(self.OUTER_RADIUS)
        half_gap = gap_angle / 2.0

        start_deg = -math.degrees(sector["end"] - half_gap)
        span_deg = math.degrees((sector["end"] - half_gap) - (sector["start"] + half_gap))

        pen = QPen(theme.Theme.accentColor(), self.ACTIVE_BORDER_WIDTH)
        pen.setCapStyle(Qt.FlatCap)   # ← 追加。端を延長せず、ぴったり終わらせる

        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawArc(rect, int(start_deg * 16), int(span_deg * 16))

    def _sector_gap_angle(self, radius):   # ← 追加。px幅を角度に変換するヘルパー
        if radius <= 0:
            return 0.0
        return self.SECTOR_GAP_WIDTH / radius

    def _build_gap_notch(self, angle_rad, inner_radius):   # ← 追加
        """指定角度(セクターの境界線)を中心に、半径方向(inner_radius〜OUTER_RADIUS)に
        伸びる、周方向の幅が常にSECTOR_GAP_WIDTH(px)一定の矩形を作る。
        これをセクターのパスから減算することで、内側/外側で均等な隙間を作る"""
        radial_length = (self.OUTER_RADIUS - inner_radius) + 4   # 確実に貫通させるための余裕

        rect = QRectF(
            -self.SECTOR_GAP_WIDTH / 2.0, -radial_length / 2.0,
            self.SECTOR_GAP_WIDTH, radial_length
        )

        transform = QTransform()
        transform.rotate(math.degrees(angle_rad) + 90)   # ← +90。矩形のローカル座標が「縦方向」を基準にしているため補正
        transform.translate(0, -(inner_radius + self.OUTER_RADIUS) / 2.0)

        path = QPainterPath()
        path.addRect(rect)
        return transform.map(path)

    def _build_sector_path(self, start_angle, end_angle, inner_radius, segments=24):   # ← inner_radius引数化
        def pt(r, a):
            return QPointF(r * math.cos(a), r * math.sin(a))

        path = QPainterPath()
        path.moveTo(pt(inner_radius, start_angle))
        path.lineTo(pt(self.OUTER_RADIUS, start_angle))

        for i in range(1, segments + 1):
            a = start_angle + (end_angle - start_angle) * i / segments
            path.lineTo(pt(self.OUTER_RADIUS, a))

        path.lineTo(pt(inner_radius, end_angle))

        for i in range(1, segments + 1):
            a = end_angle - (end_angle - start_angle) * i / segments
            path.lineTo(pt(inner_radius, a))

        path.closeSubpath()
        return path

    def _paint_sector_content(self, painter, sector, inner_radius):
        mid_angle = (sector["start"] + sector["end"]) / 2.0
        mid_radius = (inner_radius + self.OUTER_RADIUS) / 2.0
        center_x = mid_radius * math.cos(mid_angle)
        center_y = mid_radius * math.sin(mid_angle)

        chord_length = 2 * mid_radius * math.sin(self._sector_angle / 2.0)
        max_text_width = max(10, int(chord_length * 0.8))

        icon = sector["icon"]
        text_offset_y = 0

        if icon is not None:
            icon_rect = QRect(
                int(center_x - self.ICON_SIZE / 2.0),
                int(center_y - self.ICON_SIZE - self.ICON_LABEL_GAP / 2.0),   # ← 変更。固定10からICON_LABEL_GAP基準へ
                self.ICON_SIZE,
                self.ICON_SIZE
            )
            painter.drawPixmap(icon_rect, icon)
            text_offset_y = self.ICON_LABEL_GAP / 2.0   # ← 変更

        painter.setPen(self.TEXT_COLOR)
        elided = painter.fontMetrics().elidedText(sector["label"], Qt.ElideRight, max_text_width)

        text_rect = QRect(
            int(center_x - max_text_width / 2.0),
            int(center_y + text_offset_y),   # ← 変更。-8を削除しICON_LABEL_GAP基準の位置へ
            max_text_width,
            16
        )
        painter.drawText(text_rect, Qt.AlignCenter, elided)

    def _paint_center(self, painter):
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self.CENTER_CIRCLE_COLOR))
        painter.drawEllipse(QPointF(0, 0), self.INNER_RADIUS, self.INNER_RADIUS)

        painter.setPen(self.CENTER_TEXT_COLOR)
        text_rect = QRect(
            int(-self.INNER_RADIUS), int(-self.INNER_RADIUS),
            int(self.INNER_RADIUS * 2), int(self.INNER_RADIUS * 2)
        )
        painter.drawText(text_rect, Qt.AlignCenter, u"Profile")

        