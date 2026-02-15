# -*- coding: utf-8 -*-
"""UI 渲染引擎 — 中文文字、形状、粒子动画（性能优化版）"""

import cv2
import numpy as np
import math
import random
import os

try:
    from PIL import Image, ImageDraw, ImageFont
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False
    print('[Renderer] WARNING: Pillow not installed, Chinese text disabled')


class Particle:
    """粒子对象"""
    __slots__ = ('x', 'y', 'vx', 'vy', 'color', 'radius', 'life', 'max_life')

    def __init__(self, x, y, color, radius=4, life=30, vx=None, vy=None):
        self.x = float(x)
        self.y = float(y)
        self.color = color
        self.radius = radius
        self.life = life
        self.max_life = life
        self.vx = vx if vx is not None else random.uniform(-4, 4)
        self.vy = vy if vy is not None else random.uniform(-6, -1)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.15
        self.life -= 1

    @property
    def alive(self):
        return self.life > 0


class Renderer:
    """封装所有 UI 绘制操作（性能优化：文字贴图缓存）"""

    _FONT_PATHS = [
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc',
        '/System/Library/Fonts/PingFang.ttc',
        '/System/Library/Fonts/STHeiti Light.ttc',
        '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
    ]

    def __init__(self):
        self._font_cache = {}
        self._text_cache = {}       # 文字贴图缓存: key -> (bgr_patch, alpha_mask)
        self._text_cache_limit = 200
        self._font_path = self._find_font()
        if self._font_path:
            print('[Renderer] Font: {}'.format(self._font_path))
        else:
            print('[Renderer] WARNING: No CJK font found')

    def _find_font(self):
        for p in self._FONT_PATHS:
            if os.path.exists(p):
                return p
        return None

    def _get_font(self, size):
        if not _HAS_PIL or not self._font_path:
            return None
        if size not in self._font_cache:
            self._font_cache[size] = ImageFont.truetype(self._font_path, size)
        return self._font_cache[size]

    # ── 文字贴图生成与缓存 ──────────────────────────────────

    def _render_text_patch(self, text, size, color, shadow):
        """预渲染文字为 BGRA 小贴图，返回 (bgr_patch, alpha_mask, tw, th)"""
        cache_key = (text, size, color, shadow)
        if cache_key in self._text_cache:
            return self._text_cache[cache_key]

        font = self._get_font(size)
        if font is None:
            return None

        # 计算文字尺寸
        tw, th = font.getsize(text)
        # 加 padding（阴影 + 抗锯齿边距）
        pad = 4 if shadow else 2
        pw, ph = tw + pad * 2, th + pad * 2

        # 在透明背景上绘制
        pil_img = Image.new('RGBA', (pw, ph), (0, 0, 0, 0))
        draw = ImageDraw.Draw(pil_img)
        rgb_color = (color[2], color[1], color[0])

        if shadow:
            draw.text((pad + 2, pad + 2), text, font=font, fill=(0, 0, 0, 200))

        draw.text((pad, pad), text, font=font, fill=rgb_color + (255,))

        # 转为 numpy
        rgba = np.array(pil_img)
        bgr_patch = cv2.cvtColor(rgba[:, :, :3], cv2.COLOR_RGB2BGR)
        alpha_mask = rgba[:, :, 3].astype(np.float32) / 255.0

        result = (bgr_patch, alpha_mask, tw, th, pad)

        # 缓存管理
        if len(self._text_cache) >= self._text_cache_limit:
            # 清除一半缓存
            keys = list(self._text_cache.keys())
            for k in keys[:len(keys) // 2]:
                del self._text_cache[k]
        self._text_cache[cache_key] = result
        return result

    # ── 文字渲染 ──────────────────────────────────────────────

    def draw_text_cn(self, frame, text, pos, size=32, color=(255, 255, 255),
                     shadow=False, center=False):
        """在 OpenCV 帧上渲染中文文字（缓存贴图，局部混合）"""
        font = self._get_font(size)
        if font is None:
            scale = size / 30.0
            thickness = max(1, int(size / 15))
            cv2.putText(frame, text, pos, cv2.FONT_HERSHEY_SIMPLEX,
                        scale, color, thickness, cv2.LINE_AA)
            return

        patch_data = self._render_text_patch(text, size, color, shadow)
        if patch_data is None:
            return

        bgr_patch, alpha_mask, tw, th, pad = patch_data
        ph, pw = bgr_patch.shape[:2]

        x, y = pos
        if center:
            x = x - tw // 2 - pad
            y = y - th // 2 - pad
        else:
            x = x - pad
            y = y - pad

        # 边界裁剪
        fh, fw = frame.shape[:2]
        # 贴图在帧上的区域
        x1 = max(0, x)
        y1 = max(0, y)
        x2 = min(fw, x + pw)
        y2 = min(fh, y + ph)
        if x1 >= x2 or y1 >= y2:
            return

        # 贴图自身的对应区域
        px1 = x1 - x
        py1 = y1 - y
        px2 = px1 + (x2 - x1)
        py2 = py1 + (y2 - y1)

        # 局部 alpha 混合
        roi = frame[y1:y2, x1:x2]
        patch_roi = bgr_patch[py1:py2, px1:px2]
        alpha_roi = alpha_mask[py1:py2, px1:px2]

        # 向量化混合
        a3 = alpha_roi[:, :, np.newaxis]
        blended = (patch_roi.astype(np.float32) * a3 +
                   roi.astype(np.float32) * (1.0 - a3))
        frame[y1:y2, x1:x2] = blended.astype(np.uint8)

    def text_size_cn(self, text, size=32):
        """计算中文文字的像素宽高"""
        font = self._get_font(size)
        if font is None:
            scale = size / 30.0
            (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX,
                                          scale, max(1, int(size / 15)))
            return tw, th
        tw, th = font.getsize(text)
        return tw, th

    # ── 形状绘制 ──────────────────────────────────────────────

    def draw_rounded_rect(self, frame, rect, color, radius=20, thickness=-1,
                          alpha=1.0):
        """绘制圆角矩形"""
        x, y, w, h = rect
        r = min(radius, w // 2, h // 2)

        if alpha < 1.0:
            overlay = frame.copy()
            self._draw_rounded_rect_solid(overlay, x, y, w, h, r, color, thickness)
            cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
        else:
            self._draw_rounded_rect_solid(frame, x, y, w, h, r, color, thickness)

    def _draw_rounded_rect_solid(self, img, x, y, w, h, r, color, thickness):
        cv2.ellipse(img, (x + r, y + r), (r, r), 180, 0, 90, color, thickness)
        cv2.ellipse(img, (x + w - r, y + r), (r, r), 270, 0, 90, color, thickness)
        cv2.ellipse(img, (x + w - r, y + h - r), (r, r), 0, 0, 90, color, thickness)
        cv2.ellipse(img, (x + r, y + h - r), (r, r), 90, 0, 90, color, thickness)

        if thickness == -1:
            cv2.rectangle(img, (x + r, y), (x + w - r, y + h), color, -1)
            cv2.rectangle(img, (x, y + r), (x + w, y + h - r), color, -1)
        else:
            cv2.line(img, (x + r, y), (x + w - r, y), color, thickness)
            cv2.line(img, (x + r, y + h), (x + w - r, y + h), color, thickness)
            cv2.line(img, (x, y + r), (x, y + h - r), color, thickness)
            cv2.line(img, (x + w, y + r), (x + w, y + h - r), color, thickness)

    def draw_bubble(self, frame, center, radius, color):
        """绘制带光泽的泡泡（ROI 局部混合，避免全帧 copy）"""
        cx, cy = center
        r = int(radius)
        fh, fw = frame.shape[:2]

        # ROI 区域
        x1 = max(0, cx - r - 2)
        y1 = max(0, cy - r - 2)
        x2 = min(fw, cx + r + 3)
        y2 = min(fh, cy + r + 3)
        if x1 >= x2 or y1 >= y2:
            return

        # 局部 overlay
        roi = frame[y1:y2, x1:x2].copy()
        local_cx = cx - x1
        local_cy = cy - y1

        cv2.circle(roi, (local_cx, local_cy), r, color, -1, cv2.LINE_AA)
        # 混合回去（40% 泡泡色）
        cv2.addWeighted(roi, 0.4, frame[y1:y2, x1:x2], 0.6, 0,
                        frame[y1:y2, x1:x2])

        # 外圈
        cv2.circle(frame, (cx, cy), r, color, 2, cv2.LINE_AA)

        # 高光
        hx = cx - r // 3
        hy = cy - r // 3
        hr = max(r // 5, 3)
        cv2.circle(frame, (hx, hy), hr, (255, 255, 255), -1, cv2.LINE_AA)

        hx2 = cx - r // 5
        hy2 = cy - r // 2
        hr2 = max(r // 8, 2)
        cv2.circle(frame, (hx2, hy2), hr2, (255, 255, 255), -1, cv2.LINE_AA)

    def draw_particles(self, frame, particles):
        """渲染粒子列表"""
        alive = []
        for p in particles:
            p.update()
            if not p.alive:
                continue
            alpha = p.life / p.max_life
            r = max(1, int(p.radius * alpha))
            cv2.circle(frame, (int(p.x), int(p.y)), r, p.color, -1, cv2.LINE_AA)
            alive.append(p)
        return alive

    def draw_progress_bar(self, frame, progress, pos, size=(300, 24),
                          bg_color=(80, 80, 80), fg_color=(0, 220, 100)):
        x, y = pos
        w, h = size
        progress = max(0.0, min(1.0, progress))
        cv2.rectangle(frame, (x, y), (x + w, y + h), bg_color, -1)
        fw = int(w * progress)
        if fw > 0:
            cv2.rectangle(frame, (x, y), (x + fw, y + h), fg_color, -1)
        cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 255, 255), 1)

    def draw_dashed_rect(self, frame, rect, color=(255, 255, 255),
                         thickness=2, dash_len=15):
        x, y, w, h = rect
        pts = [
            ((x, y), (x + w, y)),
            ((x + w, y), (x + w, y + h)),
            ((x + w, y + h), (x, y + h)),
            ((x, y + h), (x, y)),
        ]
        for (x1, y1), (x2, y2) in pts:
            self._draw_dashed_line(frame, (x1, y1), (x2, y2),
                                   color, thickness, dash_len)

    def _draw_dashed_line(self, frame, pt1, pt2, color, thickness, dash_len):
        x1, y1 = pt1
        x2, y2 = pt2
        dx = x2 - x1
        dy = y2 - y1
        length = math.sqrt(dx * dx + dy * dy)
        if length < 1:
            return
        dx /= length
        dy /= length
        i = 0
        draw = True
        while i < length:
            end = min(i + dash_len, length)
            if draw:
                sx = int(x1 + dx * i)
                sy = int(y1 + dy * i)
                ex = int(x1 + dx * end)
                ey = int(y1 + dy * end)
                cv2.line(frame, (sx, sy), (ex, ey), color, thickness)
            draw = not draw
            i = end

    # ── 特效 ──────────────────────────────────────────────────

    def create_firework(self, cx, cy, color=None, count=30):
        particles = []
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(2, 8)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            c = color or (random.randint(100, 255),
                          random.randint(100, 255),
                          random.randint(100, 255))
            particles.append(Particle(cx, cy, c,
                                      radius=random.randint(3, 6),
                                      life=random.randint(20, 40),
                                      vx=vx, vy=vy))
        return particles

    def create_sparkle(self, cx, cy, color=(255, 255, 200), count=5):
        particles = []
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(0.5, 2)
            particles.append(Particle(
                cx + random.randint(-10, 10),
                cy + random.randint(-10, 10),
                color,
                radius=random.randint(1, 3),
                life=random.randint(10, 20),
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed
            ))
        return particles

    def draw_star(self, frame, center, size, color, thickness=-1):
        cx, cy = center
        pts = []
        for i in range(5):
            angle = math.radians(-90 + i * 72)
            pts.append((int(cx + size * math.cos(angle)),
                        int(cy + size * math.sin(angle))))
            angle2 = math.radians(-90 + i * 72 + 36)
            inner = size * 0.4
            pts.append((int(cx + inner * math.cos(angle2)),
                        int(cy + inner * math.sin(angle2))))
        pts_np = np.array(pts, dtype=np.int32)
        if thickness == -1:
            cv2.fillPoly(frame, [pts_np], color, cv2.LINE_AA)
        else:
            cv2.polylines(frame, [pts_np], True, color, thickness, cv2.LINE_AA)

    def draw_overlay(self, frame, alpha=0.5, color=(0, 0, 0)):
        """绘制半透明遮罩"""
        beta = 1.0 - alpha
        # 就地缩放帧亮度
        cv2.convertScaleAbs(frame, dst=frame, alpha=beta)
        # 叠加颜色分量（兼容 OpenCV 4.1）
        b = int(color[0] * alpha)
        g = int(color[1] * alpha)
        r = int(color[2] * alpha)
        if b or g or r:
            cv2.add(frame, (b, g, r, 0), dst=frame)

    def draw_checkmark(self, frame, center, size, color=(0, 220, 0), thickness=6):
        cx, cy = center
        s = size
        pt1 = (cx - s, cy)
        pt2 = (cx - s // 3, cy + s * 2 // 3)
        pt3 = (cx + s, cy - s * 2 // 3)
        cv2.line(frame, pt1, pt2, color, thickness, cv2.LINE_AA)
        cv2.line(frame, pt2, pt3, color, thickness, cv2.LINE_AA)
