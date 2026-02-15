# -*- coding: utf-8 -*-
"""魔法画笔 — 手持彩色物品在摄像头前绘画"""

import cv2
import numpy as np
import random

from games.base_game import BaseGame
from utils.color_tracker import track_all_colors, COLOR_BGR, PAINT_COLORS
from renderer import Particle


class AirPainter(BaseGame):
    """追踪彩色物品轨迹，在屏幕上绘画"""

    def __init__(self, renderer):
        super().__init__(renderer)
        self._canvas = None        # 绘画层
        self._prev_points = {}     # 上一帧各颜色的位置 {color: (x,y)}
        self._sparkles = []        # 闪光粒子
        self._frame_count = 0

    def reset(self):
        super().reset()
        self._canvas = None
        self._prev_points = {}
        self._sparkles = []
        self._frame_count = 0

    def on_frame(self, frame):
        h, w = frame.shape[:2]
        self._frame_count += 1

        # 初始化画布（透明层，用 BGRA 或全黑 BGR + mask）
        if self._canvas is None:
            self._canvas = np.zeros((h, w, 3), dtype=np.uint8)
            self._canvas_mask = np.zeros((h, w), dtype=np.uint8)

        # 追踪所有颜色
        detected = track_all_colors(frame)

        for color_name, (center, area) in detected.items():
            bgr = COLOR_BGR.get(color_name, (255, 255, 255))

            # 画笔粗细随物品大小变化
            thickness = max(4, min(20, int((area / 3000.0) * 8)))

            # 连接上一帧的点
            if color_name in self._prev_points:
                prev = self._prev_points[color_name]
                # 距离过远时不连接（避免闪烁跳跃）
                dx = center[0] - prev[0]
                dy = center[1] - prev[1]
                dist = (dx * dx + dy * dy) ** 0.5
                if dist < 200:
                    cv2.line(self._canvas, prev, center, bgr,
                             thickness, cv2.LINE_AA)
                    cv2.line(self._canvas_mask, prev, center, 255,
                             thickness, cv2.LINE_AA)

            self._prev_points[color_name] = center

            # 随机生成闪光粒子
            if self._frame_count % 3 == 0:
                self._sparkles.extend(
                    self.renderer.create_sparkle(center[0], center[1], bgr, 2)
                )

        # 清除丢失颜色的上一帧位置
        for color_name in list(self._prev_points.keys()):
            if color_name not in detected:
                del self._prev_points[color_name]

        # 画布拖尾效果：逐渐淡化
        if self._frame_count % 5 == 0:
            fade = np.full_like(self._canvas_mask, 2, dtype=np.uint8)
            self._canvas_mask = cv2.subtract(self._canvas_mask, fade)
            # 更新 canvas 的透明度
            faded = self._canvas.copy()
            faded[self._canvas_mask < 10] = 0
            self._canvas = faded

        # 叠加画布到摄像头画面
        mask_3ch = cv2.merge([self._canvas_mask, self._canvas_mask,
                              self._canvas_mask])
        # 使用加权叠加
        canvas_float = self._canvas.astype(np.float32)
        mask_float = (mask_3ch.astype(np.float32) / 255.0)
        frame_float = frame.astype(np.float32)
        result = frame_float * (1 - mask_float * 0.8) + canvas_float * (mask_float * 0.8)
        np.clip(result, 0, 255, out=result)
        frame = result.astype(np.uint8)

        # 渲染闪光粒子
        self._sparkles = self.renderer.draw_particles(frame, self._sparkles)

        # 绘制已检测到的颜色指示器
        self._draw_color_indicators(frame, detected, w)

        # 顶部标题
        self.renderer.draw_text_cn(frame, '魔法画笔',
                                   (w // 2, 30), size=36,
                                   color=(255, 255, 255),
                                   shadow=True, center=True)

        # 操作提示
        self.renderer.draw_text_cn(frame, '挥动彩色物品来画画！  C=清除  ESC=返回',
                                   (w // 2, h - 30), size=20,
                                   color=(180, 180, 180), center=True)

        return frame

    def on_key(self, key):
        if key == ord('c') or key == ord('C'):
            # 清除画布
            if self._canvas is not None:
                self._canvas[:] = 0
                self._canvas_mask[:] = 0
                self._prev_points.clear()

    def _draw_color_indicators(self, frame, detected, width):
        """在左上角显示当前检测到的颜色"""
        x = 20
        y = 80
        for color_name in PAINT_COLORS:
            bgr = COLOR_BGR[color_name]
            is_active = color_name in detected

            # 圆形指示器
            r = 15 if is_active else 10
            cv2.circle(frame, (x + 15, y), r, bgr, -1, cv2.LINE_AA)
            if is_active:
                cv2.circle(frame, (x + 15, y), r + 3,
                           (255, 255, 255), 2, cv2.LINE_AA)

            y += 40
