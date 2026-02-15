# -*- coding: utf-8 -*-
"""颜色猎人 — 找到指定颜色的物品展示给摄像头"""

import cv2
import random
import time

from games.base_game import BaseGame
from utils.color_tracker import (ALL_COLORS, COLOR_BGR, COLOR_CN,
                                  detect_color_ratio)
from renderer import Particle


class ColorHunter(BaseGame):
    """颜色识别游戏：显示目标颜色，孩子找到对应颜色物品"""

    TOTAL_ROUNDS = 8
    MATCH_THRESHOLD = 0.15    # 颜色匹配占比阈值
    HOLD_DURATION = 1.0       # 需持续识别的秒数
    SUCCESS_DELAY = 2.5       # 成功后的展示时间

    def __init__(self, renderer):
        super().__init__(renderer)
        self._round = 0
        self._score = 0
        self._target_color = None
        self._match_start = None    # 开始匹配的时间
        self._success_time = None   # 成功的时间
        self._particles = []
        self._used_colors = []
        self._game_over = False
        self._next_round()

    def reset(self):
        super().reset()
        self._round = 0
        self._score = 0
        self._target_color = None
        self._match_start = None
        self._success_time = None
        self._particles = []
        self._used_colors = []
        self._game_over = False
        self._next_round()

    def _next_round(self):
        """进入下一轮"""
        self._round += 1
        if self._round > self.TOTAL_ROUNDS:
            self._game_over = True
            return

        # 不连续重复颜色
        available = [c for c in ALL_COLORS if c != self._target_color]
        self._target_color = random.choice(available)
        self._used_colors.append(self._target_color)
        self._match_start = None
        self._success_time = None

    def on_frame(self, frame):
        h, w = frame.shape[:2]
        now = time.time()

        if self._game_over:
            return self._draw_game_over(frame, w, h)

        # 检测区域：画面中央 40%
        roi_w = int(w * 0.4)
        roi_h = int(h * 0.4)
        roi_x = (w - roi_w) // 2
        roi_y = (h - roi_h) // 2
        roi = (roi_x, roi_y, roi_w, roi_h)

        # 成功展示阶段
        if self._success_time is not None:
            frame = self._draw_success(frame, w, h)
            if now - self._success_time > self.SUCCESS_DELAY:
                self._next_round()
            return frame

        # 颜色检测
        ratio = detect_color_ratio(frame, roi, self._target_color)

        if ratio >= self.MATCH_THRESHOLD:
            if self._match_start is None:
                self._match_start = now
            elapsed = now - self._match_start
            if elapsed >= self.HOLD_DURATION:
                # 匹配成功！
                self._score += 1
                self._success_time = now
                # 创建烟花
                for _ in range(3):
                    fx = random.randint(w // 4, w * 3 // 4)
                    fy = random.randint(h // 4, h * 3 // 4)
                    color = COLOR_BGR[self._target_color]
                    self._particles.extend(
                        self.renderer.create_firework(fx, fy, color, 40)
                    )
        else:
            self._match_start = None

        # ── 绘制界面 ──

        # 半透明顶部栏
        self.renderer.draw_rounded_rect(frame, (0, 0, w, 100),
                                        (30, 20, 40), radius=0, alpha=0.6)

        # 顶部标题
        self.renderer.draw_text_cn(frame, '颜色猎人',
                                   (w // 2, 15), size=36,
                                   color=(255, 255, 255),
                                   shadow=True, center=True)

        # 进度和分数
        progress_text = '第 {}/{} 轮'.format(self._round, self.TOTAL_ROUNDS)
        self.renderer.draw_text_cn(frame, progress_text,
                                   (w // 2, 60), size=22,
                                   color=(200, 200, 200), center=True)

        # 进度条
        bar_w = 200
        bar_x = (w - bar_w) // 2
        progress = (self._round - 1) / float(self.TOTAL_ROUNDS)
        self.renderer.draw_progress_bar(frame, progress,
                                        (bar_x, 85), (bar_w, 12))

        # 分数
        self.renderer.draw_text_cn(frame, '得分: {}'.format(self._score),
                                   (w - 100, 15), size=28,
                                   color=(0, 255, 200), shadow=True,
                                   center=True)

        # 目标颜色展示
        target_bgr = COLOR_BGR[self._target_color]
        target_cn = COLOR_CN[self._target_color]

        # 大色块圆形
        circle_r = 60
        circle_cx = w // 2
        circle_cy = h // 2 - 80
        cv2.circle(frame, (circle_cx, circle_cy), circle_r,
                   target_bgr, -1, cv2.LINE_AA)
        cv2.circle(frame, (circle_cx, circle_cy), circle_r + 3,
                   (255, 255, 255), 3, cv2.LINE_AA)

        # 提示文字
        prompt = '找一个{}的东西！'.format(target_cn)
        self.renderer.draw_text_cn(frame, prompt,
                                   (w // 2, h // 2 + 10),
                                   size=44, color=target_bgr,
                                   shadow=True, center=True)

        # 虚线检测框
        self.renderer.draw_dashed_rect(frame, roi, (255, 255, 255), 2, 15)

        # 检测进度指示
        if self._match_start is not None:
            elapsed = now - self._match_start
            fill = min(1.0, elapsed / self.HOLD_DURATION)
            bar_y = roi_y + roi_h + 10
            self.renderer.draw_progress_bar(
                frame, fill,
                (roi_x, bar_y), (roi_w, 16),
                bg_color=(80, 80, 80), fg_color=target_bgr
            )

        # 提示
        hint = '把{}物品放到框里！'.format(target_cn)
        self.renderer.draw_text_cn(frame, hint,
                                   (w // 2, h - 40), size=22,
                                   color=(180, 180, 180), center=True)

        # 渲染粒子
        self._particles = self.renderer.draw_particles(frame, self._particles)

        return frame

    def _draw_success(self, frame, w, h):
        """绘制成功画面"""
        target_bgr = COLOR_BGR[self._target_color]
        target_cn = COLOR_CN[self._target_color]

        # 大号对勾
        self.renderer.draw_checkmark(frame, (w // 2, h // 2 - 40), 60,
                                     color=(0, 255, 100), thickness=8)

        # 成功文字
        self.renderer.draw_text_cn(frame, '太棒了！',
                                   (w // 2, h // 2 + 50),
                                   size=56, color=(0, 255, 200),
                                   shadow=True, center=True)

        self.renderer.draw_text_cn(frame, '找到了{}！'.format(target_cn),
                                   (w // 2, h // 2 + 120),
                                   size=32, color=target_bgr,
                                   shadow=True, center=True)

        # 渲染粒子
        self._particles = self.renderer.draw_particles(frame, self._particles)

        return frame

    def _draw_game_over(self, frame, w, h):
        """绘制游戏结束画面"""
        self.renderer.draw_overlay(frame, alpha=0.5, color=(20, 10, 30))

        self.renderer.draw_text_cn(frame, '游戏结束！',
                                   (w // 2, h // 3),
                                   size=56, color=(255, 255, 100),
                                   shadow=True, center=True)

        score_text = '得分: {} / {}'.format(self._score, self.TOTAL_ROUNDS)
        self.renderer.draw_text_cn(frame, score_text,
                                   (w // 2, h // 2),
                                   size=44, color=(255, 255, 255),
                                   shadow=True, center=True)

        # 星星评价
        stars = min(5, max(1, int(self._score * 5.0 / self.TOTAL_ROUNDS + 0.5)))
        star_y = h // 2 + 80
        star_spacing = 60
        start_x = w // 2 - (stars - 1) * star_spacing // 2

        for i in range(stars):
            sx = start_x + i * star_spacing
            self.renderer.draw_star(frame, (sx, star_y), 22,
                                    (0, 220, 255), -1)

        self.renderer.draw_text_cn(frame, '按 ESC 返回菜单',
                                   (w // 2, h - 60), size=24,
                                   color=(160, 160, 160), center=True)

        # 渲染残余粒子
        self._particles = self.renderer.draw_particles(frame, self._particles)

        return frame
