# -*- coding: utf-8 -*-
"""泡泡大战 — 用手挥动戳破屏幕上的泡泡"""

import cv2
import numpy as np
import random
import math
import time

from games.base_game import BaseGame
from utils.motion_detector import MotionDetector
from renderer import Particle


class Bubble:
    """单个泡泡"""
    __slots__ = ('x', 'y', 'radius', 'color', 'speed', 'phase',
                 'alive', 'pop_particles')

    def __init__(self, x, y, radius, color, speed):
        self.x = float(x)
        self.y = float(y)
        self.radius = radius
        self.color = color
        self.speed = speed
        self.phase = random.uniform(0, 2 * math.pi)  # 左右摆动相位
        self.alive = True
        self.pop_particles = []


# 泡泡可选颜色 (BGR)
BUBBLE_COLORS = [
    (255, 100, 100),   # 浅蓝
    (100, 255, 100),   # 浅绿
    (100, 100, 255),   # 浅红
    (255, 255, 100),   # 浅青
    (255, 100, 255),   # 浅紫
    (100, 255, 255),   # 浅黄
    (200, 200, 100),   # 天蓝
    (100, 200, 255),   # 浅橙
]


class BubblePop(BaseGame):
    """泡泡大战：用运动检测戳破漂浮的泡泡"""

    MAX_BUBBLES = 7
    MIN_RADIUS = 35
    MAX_RADIUS = 70
    BASE_SPEED = 1.5
    SPEED_INCREMENT = 0.1   # 每 30 秒速度增量
    SPAWN_INTERVAL = 1.5    # 新泡泡生成间隔（秒）

    def __init__(self, renderer):
        super().__init__(renderer)
        self._motion = MotionDetector(min_area=2000, threshold=25)
        self._bubbles = []
        self._pop_particles = []
        self._score = 0
        self._start_time = time.time()
        self._last_spawn = time.time()
        self._frame_count = 0

        # 初始生成一批泡泡
        self._initial_spawn()

    def reset(self):
        super().reset()
        self._motion.reset()
        self._bubbles = []
        self._pop_particles = []
        self._score = 0
        self._start_time = time.time()
        self._last_spawn = time.time()
        self._frame_count = 0
        self._initial_spawn()

    def _initial_spawn(self):
        """初始生成泡泡"""
        for _ in range(5):
            self._spawn_bubble(random_y=True)

    def _current_speed(self):
        """根据游戏时间计算当前泡泡速度"""
        elapsed = time.time() - self._start_time
        extra = int(elapsed / 30) * self.SPEED_INCREMENT
        return self.BASE_SPEED + extra

    def _spawn_bubble(self, random_y=False):
        """在屏幕底部（或随机位置）生成新泡泡"""
        if len(self._bubbles) >= self.MAX_BUBBLES:
            return

        radius = random.randint(self.MIN_RADIUS, self.MAX_RADIUS)
        x = random.randint(radius + 20, 1260 - radius)
        if random_y:
            y = random.randint(100, 620)
        else:
            y = 720 + radius  # 从屏幕下方进入

        color = random.choice(BUBBLE_COLORS)
        speed = self._current_speed() * (0.8 + random.random() * 0.4)

        self._bubbles.append(Bubble(x, y, radius, color, speed))

    def on_frame(self, frame):
        h, w = frame.shape[:2]
        now = time.time()
        self._frame_count += 1

        # 运动检测
        motions = self._motion.detect(frame)

        # 更新泡泡位置
        alive_bubbles = []
        for bubble in self._bubbles:
            if not bubble.alive:
                continue

            # 上浮
            bubble.y -= bubble.speed

            # 左右摆动（正弦）
            bubble.phase += 0.03
            bubble.x += math.sin(bubble.phase) * 1.5

            # 超出屏幕顶部：重新放到底部
            if bubble.y < -bubble.radius:
                bubble.y = h + bubble.radius
                bubble.x = random.randint(int(bubble.radius) + 20,
                                          w - int(bubble.radius) - 20)

            # 碰撞检测：运动区域 vs 泡泡
            for (mx, my), m_area in motions:
                dx = mx - bubble.x
                dy = my - bubble.y
                dist = math.sqrt(dx * dx + dy * dy)
                # 运动区域半径估计
                motion_r = math.sqrt(m_area / math.pi)
                if dist < bubble.radius + motion_r * 0.5:
                    # 泡泡被戳破！
                    bubble.alive = False
                    self._score += 1
                    # 爆破粒子
                    self._pop_particles.extend(
                        self.renderer.create_firework(
                            int(bubble.x), int(bubble.y),
                            bubble.color, 25
                        )
                    )
                    # 扩散圆环效果
                    self._pop_particles.append(
                        Particle(bubble.x, bubble.y, bubble.color,
                                 radius=bubble.radius, life=15,
                                 vx=0, vy=0)
                    )
                    break

            if bubble.alive:
                alive_bubbles.append(bubble)

        self._bubbles = alive_bubbles

        # 定时生成新泡泡
        if now - self._last_spawn > self.SPAWN_INTERVAL:
            self._spawn_bubble()
            self._last_spawn = now

        # ── 绘制 ──

        # 绘制运动检测可视化（淡显）
        for (mx, my), m_area in motions:
            mr = int(math.sqrt(m_area / math.pi) * 0.5)
            cv2.circle(frame, (mx, my), mr, (255, 255, 255), 1, cv2.LINE_AA)

        # 绘制泡泡
        for bubble in self._bubbles:
            self.renderer.draw_bubble(frame,
                                      (int(bubble.x), int(bubble.y)),
                                      bubble.radius, bubble.color)

        # 绘制爆破粒子
        self._pop_particles = self.renderer.draw_particles(
            frame, self._pop_particles)

        # 顶部信息栏
        self.renderer.draw_rounded_rect(frame, (0, 0, w, 70),
                                        (30, 20, 40), radius=0, alpha=0.5)

        self.renderer.draw_text_cn(frame, '泡泡大战',
                                   (w // 2, 10), size=36,
                                   color=(255, 255, 255),
                                   shadow=True, center=True)

        # 分数
        score_text = '戳破: {}'.format(self._score)
        self.renderer.draw_text_cn(frame, score_text,
                                   (w - 100, 15), size=28,
                                   color=(100, 255, 255),
                                   shadow=True, center=True)

        # 操作提示
        self.renderer.draw_text_cn(frame, '挥动双手戳破泡泡！  ESC=返回',
                                   (w // 2, h - 30), size=20,
                                   color=(180, 180, 180), center=True)

        return frame
