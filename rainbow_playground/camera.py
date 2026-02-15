# -*- coding: utf-8 -*-
"""摄像头管理模块 — 支持 Jetson Nano IMX219 和 USB 摄像头 fallback"""

import cv2


class JetsonCamera:
    """封装 GStreamer pipeline，提供镜像帧读取"""

    # IMX219 GStreamer pipeline（Jetson Nano 专用）
    GST_PIPELINE = (
        'nvarguscamerasrc ! '
        'video/x-raw(memory:NVMM), width=1280, height=720, '
        'format=NV12, framerate=30/1 ! '
        'nvvidconv flip-method=0 ! '
        'video/x-raw, width=1280, height=720, format=BGRx ! '
        'videoconvert ! video/x-raw, format=BGR ! appsink'
    )

    def __init__(self):
        self._cap = None
        self._using_gst = False

    def open(self):
        """打开摄像头，优先尝试 GStreamer pipeline，失败则 fallback 到 USB 摄像头"""
        # 尝试 GStreamer（Jetson Nano）
        self._cap = cv2.VideoCapture(self.GST_PIPELINE, cv2.CAP_GSTREAMER)
        if self._cap.isOpened():
            self._using_gst = True
            print('[Camera] GStreamer pipeline opened (IMX219)')
            return True

        # Fallback: USB / 内置摄像头
        self._cap = cv2.VideoCapture(0)
        if self._cap.isOpened():
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            self._using_gst = False
            print('[Camera] USB camera opened (fallback)')
            return True

        print('[Camera] ERROR: No camera available')
        return False

    def read(self):
        """读取一帧原始画面，返回 (success, frame)"""
        if self._cap is None:
            return False, None
        return self._cap.read()

    def read_mirror(self):
        """读取水平镜像帧（镜面效果），返回 (success, frame)"""
        ok, frame = self.read()
        if ok and frame is not None:
            frame = cv2.flip(frame, 1)
        return ok, frame

    def release(self):
        """释放摄像头资源"""
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    @property
    def is_opened(self):
        return self._cap is not None and self._cap.isOpened()

    def __del__(self):
        self.release()
