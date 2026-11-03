# -*- coding: utf-8 -*-

import math

try:
    from PySide6.QtCore import *
except ImportError:
    from PySide2.QtCore import *


__all__ = ["build_cascade_group"]

DEFAULT_SPEED             = 1.4
DEFAULT_OPACITY_DURATION  = 120
DEFAULT_SCALE_DURATION    = 180   # ← 追加
DEFAULT_MIN_DURATION      = 80
DEFAULT_ORIGIN_EXAGGERATION = 1.6   # ← 追加。原点からの距離をこの倍率で誇張する
DEFAULT_MIN_EXTRA_DISTANCE  = 40     # ← 追加。距離が0に近い場合でも最低限これだけ誇張する
DEFAULT_START_SCALE        = 0.4     # ← 追加。開始時の縮小率
DEFAULT_POS_EASING         = QEasingCurve.InOutCubic
DEFAULT_OPACITY_EASING     = QEasingCurve.OutCubic
DEFAULT_SCALE_EASING       = QEasingCurve.OutBack   # ← 追加。少しオーバーシュートさせて弾む印象を出す


def _exaggerate_origin(origin_point, final_pos, exaggeration=DEFAULT_ORIGIN_EXAGGERATION,
                        min_extra=DEFAULT_MIN_EXTRA_DISTANCE):
    """origin_point(Homeの位置)から見て、final_posと反対方向にさらに離れた
    「誇張された開始地点」を計算する。最終的な到達点(final_pos)は変えず、
    出発点だけを遠ざけることで、近距離のアイテムでも移動量を確保する"""
    dx = final_pos.x() - origin_point.x()
    dy = final_pos.y() - origin_point.y()
    distance = math.hypot(dx, dy)

    if distance < 1e-6:
        # 完全に同じ位置の場合、方向が定まらないため、単純に真上へ誇張する
        return QPoint(origin_point.x(), origin_point.y() - min_extra)

    extra = max(min_extra, distance * (exaggeration - 1.0))
    ux, uy = dx / distance, dy / distance   # final方向への単位ベクトル

    # origin_pointから見て、final方向と「反対」に extra だけ押し戻した地点
    return QPoint(
        int(origin_point.x() - ux * extra),
        int(origin_point.y() - uy * extra)
    )


def build_cascade_group(widgets, origin_point, speed=DEFAULT_SPEED,
                         opacity_duration=DEFAULT_OPACITY_DURATION,
                         scale_duration=DEFAULT_SCALE_DURATION,
                         pos_easing=DEFAULT_POS_EASING,
                         opacity_easing=DEFAULT_OPACITY_EASING,
                         scale_easing=DEFAULT_SCALE_EASING):

    entries = []
    for widget in widgets:
        final_pos = widget.pos()
        exaggerated_origin = _exaggerate_origin(origin_point, final_pos)
        distance = math.hypot(final_pos.x() - exaggerated_origin.x(), final_pos.y() - exaggerated_origin.y())
        duration = max(DEFAULT_MIN_DURATION, int(distance / speed))
        entries.append({
            "widget": widget, "final_pos": final_pos,
            "start_pos": exaggerated_origin, "duration": duration
        })

    entries.sort(key=lambda e: e["duration"])

    group = QParallelAnimationGroup()
    previous_duration = 0

    for entry in entries:
        widget = entry["widget"]
        final_pos = entry["final_pos"]
        start_pos = entry["start_pos"]
        duration = entry["duration"]
        opacity_delay = previous_duration

        widget.move(start_pos)
        widget.opacity = 0.0
        widget.scale = DEFAULT_START_SCALE   # ← 追加
        widget.show()

        pos_anim = QPropertyAnimation(widget, b"pos")
        pos_anim.setDuration(duration)
        pos_anim.setStartValue(start_pos)
        pos_anim.setEndValue(final_pos)
        pos_anim.setEasingCurve(pos_easing)

        remaining = max(40, duration - opacity_delay)
        actual_opacity_duration = min(opacity_duration, remaining)
        actual_scale_duration = min(scale_duration, remaining)   # ← 追加

        opacity_anim = QPropertyAnimation(widget, b"opacity")
        opacity_anim.setDuration(actual_opacity_duration)
        opacity_anim.setStartValue(0.0)
        opacity_anim.setEndValue(1.0)
        opacity_anim.setEasingCurve(opacity_easing)

        scale_anim = QPropertyAnimation(widget, b"scale")   # ← 追加
        scale_anim.setDuration(actual_scale_duration)
        scale_anim.setStartValue(DEFAULT_START_SCALE)
        scale_anim.setEndValue(1.0)
        scale_anim.setEasingCurve(scale_easing)

        fade_in_part = QParallelAnimationGroup()   # ← opacityとscaleをまとめる
        fade_in_part.addAnimation(opacity_anim)
        fade_in_part.addAnimation(scale_anim)

        if opacity_delay > 0:
            delayed_part = QSequentialAnimationGroup()
            delayed_part.addPause(opacity_delay)
            delayed_part.addAnimation(fade_in_part)
            fade_in_part = delayed_part

        item_group = QParallelAnimationGroup()
        item_group.addAnimation(pos_anim)
        item_group.addAnimation(fade_in_part)
        group.addAnimation(item_group)

        previous_duration = duration

    return group