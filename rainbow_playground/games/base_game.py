# -*- coding: utf-8 -*-
"""游戏抽象基类"""


class BaseGame:
    """所有游戏的公共接口"""

    def __init__(self, renderer):
        """
        Args:
            renderer: Renderer 实例，用于 UI 绘制
        """
        self.renderer = renderer
        self._finished = False

    def on_frame(self, frame):
        """处理每一帧，返回渲染后的帧

        Args:
            frame: BGR 镜像摄像头画面

        Returns:
            frame: 处理后的帧
        """
        raise NotImplementedError

    def on_key(self, key):
        """处理键盘事件

        Args:
            key: 按键 ASCII 码
        """
        pass

    def is_finished(self):
        """游戏是否结束"""
        return self._finished

    def reset(self):
        """重置游戏状态"""
        self._finished = False
