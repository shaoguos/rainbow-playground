# -*- coding: utf-8 -*-
"""帧差法运动检测模块"""

import cv2
import numpy as np


class MotionDetector:
    """使用帧差法检测画面中的运动区域"""

    def __init__(self, min_area=1500, threshold=30):
        """
        Args:
            min_area: 最小运动区域面积（像素），过滤噪声
            threshold: 帧差二值化阈值
        """
        self._prev_gray = None
        self._min_area = min_area
        self._threshold = threshold

    def detect(self, frame):
        """检测运动区域

        Args:
            frame: BGR 图像

        Returns:
            list of (center, area): 运动区域中心点和面积
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if self._prev_gray is None:
            self._prev_gray = gray
            return []

        # 计算帧差
        diff = cv2.absdiff(self._prev_gray, gray)
        self._prev_gray = gray

        # 二值化
        _, thresh = cv2.threshold(diff, self._threshold, 255, cv2.THRESH_BINARY)

        # 膨胀，连接相邻区域
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        thresh = cv2.dilate(thresh, kernel, iterations=2)

        # 查找轮廓
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)

        results = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < self._min_area:
                continue
            M = cv2.moments(cnt)
            if M['m00'] == 0:
                continue
            cx = int(M['m10'] / M['m00'])
            cy = int(M['m01'] / M['m00'])
            results.append(((cx, cy), area))

        return results

    def reset(self):
        """重置状态（切换场景时调用）"""
        self._prev_gray = None
