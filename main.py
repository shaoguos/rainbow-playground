# -*- coding: utf-8 -*-
"""彩虹乐园 — 应用入口

用法:
    python3 main.py

操作:
    菜单: 鼠标点击选择游戏
    游戏中: 点击左上角"返回"按钮回到菜单
    退出: 右键点击 或 按 Q / ESC
"""

import cv2
import sys
import time

from camera import JetsonCamera
from renderer import Renderer
from menu import Menu
from games.air_painter import AirPainter
from games.color_hunter import ColorHunter
from games.bubble_pop import BubblePop


# 应用状态
STATE_MENU = 'menu'
STATE_GAME = 'game'

WINDOW_NAME = 'Rainbow Playground'

# 返回按钮区域 (x, y, w, h)
BACK_BUTTON = (10, 10, 120, 50)


class App:
    """应用主控"""

    def __init__(self):
        self.state = STATE_MENU
        self.current_game = None
        self.click_pos = None  # 最近一次鼠标左键点击坐标

    def on_mouse(self, event, x, y, flags, param):
        """OpenCV 鼠标回调"""
        if event == cv2.EVENT_LBUTTONDOWN:
            self.click_pos = (x, y)


def main():
    print('=' * 50)
    print('  彩虹乐园 Rainbow Playground')
    print('  鼠标点击选择游戏 | 右键/ESC 退出')
    print('=' * 50)

    # 初始化摄像头
    camera = JetsonCamera()
    if not camera.open():
        print('ERROR: 无法打开摄像头，请检查连接')
        sys.exit(1)

    # 初始化渲染器
    renderer = Renderer()

    # 初始化菜单和游戏工厂
    menu = Menu(renderer)
    game_factories = {
        0: lambda: AirPainter(renderer),
        1: lambda: ColorHunter(renderer),
        2: lambda: BubblePop(renderer),
    }

    # 创建全屏窗口
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN,
                          cv2.WINDOW_FULLSCREEN)

    app = App()
    cv2.setMouseCallback(WINDOW_NAME, app.on_mouse)

    # 帧率控制
    fps_target = 30
    frame_time = 1.0 / fps_target
    fps_display = 0
    fps_counter = 0
    fps_timer = time.time()

    try:
        while True:
            t_start = time.time()

            # 读取镜像帧
            ok, frame = camera.read_mirror()
            if not ok or frame is None:
                print('WARNING: 摄像头读取失败，重试...')
                time.sleep(0.1)
                continue

            # 消费点击事件
            click = app.click_pos
            app.click_pos = None

            # 处理帧
            if app.state == STATE_MENU:
                frame = menu.draw(frame)
                # 检查菜单点击
                if click is not None:
                    idx = menu.hit_test(click[0], click[1])
                    if idx is not None and idx in game_factories:
                        print('启动游戏: {}'.format(idx + 1))
                        app.current_game = game_factories[idx]()
                        app.state = STATE_GAME

            elif app.state == STATE_GAME and app.current_game is not None:
                frame = app.current_game.on_frame(frame)
                # 绘制返回按钮
                _draw_back_button(frame, renderer)
                # 检查返回按钮点击
                if click is not None and _hit_back_button(click[0], click[1]):
                    print('返回菜单')
                    app.state = STATE_MENU
                    app.current_game = None

            # FPS 计算
            fps_counter += 1
            if time.time() - fps_timer >= 1.0:
                fps_display = fps_counter
                fps_counter = 0
                fps_timer = time.time()
                print('FPS: {}'.format(fps_display))

            # 显示 FPS（左下角小字）
            cv2.putText(frame, 'FPS: {}'.format(fps_display),
                        (10, frame.shape[0] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                        (100, 100, 100), 1)

            # 显示
            cv2.imshow(WINDOW_NAME, frame)

            # 帧率控制
            elapsed = time.time() - t_start
            wait_ms = max(1, int((frame_time - elapsed) * 1000))
            key = cv2.waitKey(wait_ms) & 0xFF

            # 键盘事件处理（保留作为备用）
            if key == ord('q') or key == ord('Q') or key == 27:
                if app.state == STATE_GAME:
                    print('返回菜单')
                    app.state = STATE_MENU
                    app.current_game = None
                else:
                    print('退出应用')
                    break

            # 游戏内键盘事件
            if app.state == STATE_GAME and app.current_game is not None:
                app.current_game.on_key(key)

    except KeyboardInterrupt:
        print('\n键盘中断，退出')
    finally:
        camera.release()
        cv2.destroyAllWindows()
        print('已退出')


def _draw_back_button(frame, renderer):
    """在左上角绘制返回按钮"""
    bx, by, bw, bh = BACK_BUTTON
    renderer.draw_rounded_rect(frame, BACK_BUTTON,
                               (60, 60, 60), radius=12, alpha=0.7)
    # 绘制 "< 返回" 文字
    renderer.draw_text_cn(frame, '< 返回',
                          (bx + bw // 2, by + bh // 2),
                          size=22, color=(255, 255, 255),
                          center=True)


def _hit_back_button(x, y):
    """检测点击是否在返回按钮区域"""
    bx, by, bw, bh = BACK_BUTTON
    return bx <= x <= bx + bw and by <= y <= by + bh


if __name__ == '__main__':
    main()
