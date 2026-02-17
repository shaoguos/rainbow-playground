# -*- coding: utf-8 -*-
"""主菜单界面 — 摄像头背景 + 3 个可点击游戏图标"""

import cv2
import math


class Menu:
    """主菜单：显示 3 个游戏选项供鼠标点击选择"""

    # 游戏信息
    GAMES = [
        {'icon': 'brush',   'name': '魔法画笔',
         'color': (0, 100, 255)},    # 橙红
        {'icon': 'rainbow', 'name': '颜色猎人',
         'color': (0, 200, 255)},    # 黄色
        {'icon': 'bubble',  'name': '泡泡大战',
         'color': (255, 180, 0)},    # 天蓝
    ]

    ICON_RADIUS = 80  # 图标基础半径

    def __init__(self, renderer):
        self.renderer = renderer
        self._anim_t = 0
        # 缓存各图标中心坐标，用于 hit_test
        self._icon_centers = []
        self._icon_radius = self.ICON_RADIUS

    def draw(self, frame):
        """在摄像头帧上绘制菜单界面"""
        h, w = frame.shape[:2]
        self._anim_t += 1

        # 半透明深色遮罩
        self.renderer.draw_overlay(frame, alpha=0.45, color=(30, 20, 40))

        # 标题
        self.renderer.draw_text_cn(frame, '彩虹乐园',
                                   (w // 2, h // 6),
                                   size=72, color=(100, 255, 255),
                                   shadow=True, center=True)

        # 副标题
        self.renderer.draw_text_cn(frame, 'Rainbow Playground',
                                   (w // 2, h // 6 + 80),
                                   size=28, color=(200, 200, 200),
                                   center=True)

        # 三个游戏图标，横排排列
        spacing = w // 4
        cy = h // 2 + 10
        self._icon_centers = []

        for i, game in enumerate(self.GAMES):
            cx = spacing * (i + 1)
            self._icon_centers.append((cx, cy))

            # 呼吸动画
            breath = math.sin(self._anim_t * 0.05 + i * 1.2) * 5
            r = int(self.ICON_RADIUS + breath)

            # 圆形背景（ROI 局部混合，避免全帧 copy）
            color = game['color']
            fh, fw = frame.shape[:2]
            rx1 = max(0, cx - r - 2)
            ry1 = max(0, cy - r - 2)
            rx2 = min(fw, cx + r + 3)
            ry2 = min(fh, cy + r + 3)
            roi = frame[ry1:ry2, rx1:rx2].copy()
            cv2.circle(roi, (cx - rx1, cy - ry1), r, color, -1, cv2.LINE_AA)
            cv2.addWeighted(roi, 0.7, frame[ry1:ry2, rx1:rx2], 0.3, 0,
                            frame[ry1:ry2, rx1:rx2])
            cv2.circle(frame, (cx, cy), r, (255, 255, 255), 3, cv2.LINE_AA)

            # 图标内容
            self._draw_icon(frame, game['icon'], cx, cy, r)

            # 游戏名称
            self.renderer.draw_text_cn(frame, game['name'],
                                       (cx, cy + r + 30),
                                       size=32, color=(255, 255, 255),
                                       shadow=True, center=True)

            # 点击提示
            self.renderer.draw_text_cn(frame, '点击开始',
                                       (cx, cy + r + 70),
                                       size=22, color=(180, 180, 180),
                                       center=True)

        # 底部操作提示
        self.renderer.draw_text_cn(frame, '点击图标选择游戏  |  ESC 退出',
                                   (w // 2, h - 50),
                                   size=24, color=(160, 160, 160),
                                   center=True)

        return frame

    def hit_test(self, x, y):
        """检测鼠标点击命中了哪个游戏图标

        Returns:
            int or None: 图标索引 (0/1/2) 或 None
        """
        r = self.ICON_RADIUS + 10  # 额外容差
        for i, (cx, cy) in enumerate(self._icon_centers):
            dx = x - cx
            dy = y - cy
            if dx * dx + dy * dy <= r * r:
                return i
        return None

    def _draw_icon(self, frame, icon_type, cx, cy, r):
        """在圆形内绘制简易图标"""
        s = r // 2

        if icon_type == 'brush':
            pt1 = (cx - s, cy - s)
            pt2 = (cx + s // 2, cy + s // 2)
            cv2.line(frame, pt1, pt2, (255, 255, 255), 4, cv2.LINE_AA)
            cv2.circle(frame, pt2, 6, (255, 200, 0), -1, cv2.LINE_AA)
            cv2.circle(frame, (cx + s // 4, cy - s // 3), 5,
                       (0, 0, 255), -1, cv2.LINE_AA)
            cv2.circle(frame, (cx - s // 3, cy + s // 4), 4,
                       (0, 255, 0), -1, cv2.LINE_AA)

        elif icon_type == 'rainbow':
            colors = [(0, 0, 255), (0, 200, 255), (0, 255, 0)]
            for j, c in enumerate(colors):
                ar = s - j * 8
                if ar > 5:
                    cv2.ellipse(frame, (cx, cy + 10), (ar, ar),
                                0, 180, 360, c, 3, cv2.LINE_AA)

        elif icon_type == 'bubble':
            positions = [(-s//3, -s//4, s//2),
                         (s//4, s//5, s//3),
                         (-s//6, s//3, s//4)]
            for dx, dy, br in positions:
                cv2.circle(frame, (cx + dx, cy + dy), br,
                           (255, 255, 255), 2, cv2.LINE_AA)
                cv2.circle(frame, (cx + dx - br//3, cy + dy - br//3),
                           max(br//4, 2), (255, 255, 255), -1, cv2.LINE_AA)
