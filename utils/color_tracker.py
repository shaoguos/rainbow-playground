# -*- coding: utf-8 -*-
"""HSV 颜色追踪模块 — 预定义颜色范围，追踪指定颜色物体"""

import cv2
import numpy as np


# HSV 颜色范围表（每种颜色可能有多个范围，如红色跨越 0/180 边界）
# 格式: color_name -> [(lower, upper), ...]
COLOR_RANGES = {
    'red': [
        (np.array([0, 120, 70]),   np.array([10, 255, 255])),
        (np.array([170, 120, 70]), np.array([180, 255, 255])),
    ],
    'blue': [
        (np.array([100, 120, 70]), np.array([130, 255, 255])),
    ],
    'green': [
        (np.array([35, 80, 70]),  np.array([85, 255, 255])),
    ],
    'yellow': [
        (np.array([20, 100, 100]), np.array([35, 255, 255])),
    ],
    'orange': [
        (np.array([10, 120, 100]), np.array([20, 255, 255])),
    ],
    'purple': [
        (np.array([130, 80, 70]), np.array([170, 255, 255])),
    ],
}

# 颜色对应的 BGR 显示色值
COLOR_BGR = {
    'red':    (0, 0, 255),
    'blue':   (255, 100, 0),
    'green':  (0, 200, 0),
    'yellow': (0, 255, 255),
    'orange': (0, 140, 255),
    'purple': (200, 50, 200),
}

# 颜色中文名
COLOR_CN = {
    'red':    '红色',
    'blue':   '蓝色',
    'green':  '绿色',
    'yellow': '黄色',
    'orange': '橙色',
    'purple': '紫色',
}

# 可用颜色名列表
ALL_COLORS = list(COLOR_RANGES.keys())
# 魔法画笔使用的基础颜色（排除不易获取的）
PAINT_COLORS = ['red', 'blue', 'green', 'yellow']

# 最小轮廓面积（像素），过滤噪声
MIN_CONTOUR_AREA = 800


def _create_mask(hsv, color_name):
    """为指定颜色创建二值掩膜"""
    ranges = COLOR_RANGES.get(color_name, [])
    if not ranges:
        return None

    mask = None
    for lower, upper in ranges:
        m = cv2.inRange(hsv, lower, upper)
        mask = m if mask is None else cv2.bitwise_or(mask, m)

    # 形态学处理，去噪
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.erode(mask, kernel, iterations=1)
    mask = cv2.dilate(mask, kernel, iterations=2)
    return mask


def track_color(frame, color_name):
    """追踪指定颜色的最大物体

    Args:
        frame: BGR 图像
        color_name: 颜色名（如 'red'）

    Returns:
        (center, area): 中心点 (x,y) 和面积；未检测到则返回 (None, 0)
    """
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = _create_mask(hsv, color_name)
    if mask is None:
        return None, 0

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None, 0

    # 找最大轮廓
    largest = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(largest)
    if area < MIN_CONTOUR_AREA:
        return None, 0

    M = cv2.moments(largest)
    if M['m00'] == 0:
        return None, 0
    cx = int(M['m10'] / M['m00'])
    cy = int(M['m01'] / M['m00'])
    return (cx, cy), area


def track_all_colors(frame):
    """同时追踪所有画笔颜色

    Returns:
        dict: {color_name: (center, area)} 仅包含检测到的颜色
    """
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    results = {}

    for color_name in PAINT_COLORS:
        mask = _create_mask(hsv, color_name)
        if mask is None:
            continue

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            continue

        largest = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest)
        if area < MIN_CONTOUR_AREA:
            continue

        M = cv2.moments(largest)
        if M['m00'] == 0:
            continue
        cx = int(M['m10'] / M['m00'])
        cy = int(M['m01'] / M['m00'])
        results[color_name] = ((cx, cy), area)

    return results


def detect_color_ratio(frame, roi, color_name):
    """检测指定区域内目标颜色的像素占比

    Args:
        frame: BGR 图像
        roi: (x, y, w, h) 检测区域
        color_name: 目标颜色

    Returns:
        float: 颜色占比 0.0 ~ 1.0
    """
    x, y, w, h = roi
    region = frame[y:y+h, x:x+w]
    if region.size == 0:
        return 0.0

    hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
    mask = _create_mask(hsv, color_name)
    if mask is None:
        return 0.0

    total_pixels = w * h
    color_pixels = cv2.countNonZero(mask)
    return color_pixels / float(total_pixels)
