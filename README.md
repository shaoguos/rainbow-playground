# 🌈 彩虹乐园 Rainbow Playground

基于摄像头交互的儿童益智游戏应用，专为 **4 岁左右幼儿** 设计。运行在 Jetson Nano 上，通过 HDMI 连接电视，利用 IMX219 摄像头实现体感互动，**完全离线运行**。

## 🎮 三个小游戏

| 游戏 | 玩法 | 锻炼能力 |
|------|------|---------|
| 🎨 **魔法画笔** | 手持彩色物品在摄像头前挥舞，空中画出彩色轨迹 | 手眼协调、创造力、颜色认知 |
| 🌈 **颜色猎人** | 根据屏幕提示找到对应颜色的物品展示给摄像头 | 颜色辨识、探索能力、成就感 |
| 🫧 **泡泡大战** | 挥动双手戳破屏幕上飘浮的彩色泡泡 | 反应速度、肢体运动、数数 |

## 🖥️ 运行环境

- **硬件**: Jetson Nano (4GB) + IMX219 摄像头 + HDMI 电视
- **系统**: JetPack 4.6.1 (L4T R32.7.1)
- **Python**: 3.6.9
- **依赖**: OpenCV 4.1.1, NumPy, Pillow

## 🚀 快速开始

### 1. 安装依赖（首次）

```bash
./deploy.sh install
```

### 2. 部署并运行

```bash
./deploy.sh run
```

单独同步代码（不运行）:

```bash
./deploy.sh sync
```

### 3. 直接在 Jetson 上运行

```bash
ssh jetson@192.168.1.19
export DISPLAY=:0
cd ~/rainbow_playground
python3 main.py
```

## 🎯 操作方式

- **选择游戏**: 鼠标点击屏幕上的游戏图标
- **返回菜单**: 点击左上角"返回"按钮 或按 `ESC`
- **退出应用**: 在菜单界面按 `Q` 或 `ESC`

## 🏗️ 项目结构

```
├── main.py              # 应用入口
├── camera.py            # 摄像头管理 (GStreamer / V4L2)
├── renderer.py          # UI 渲染引擎 (中文文字、形状、粒子动画)
├── menu.py              # 主菜单界面
├── deploy.sh            # 一键部署脚本
├── games/
│   ├── base_game.py     # 游戏基类
│   ├── air_painter.py   # 🎨 魔法画笔
│   ├── color_hunter.py  # 🌈 颜色猎人
│   └── bubble_pop.py    # 🫧 泡泡大战
└── utils/
    ├── color_tracker.py # HSV 颜色追踪
    └── motion_detector.py # 帧差运动检测
```

## 🔧 核心技术

- **摄像头读取**: GStreamer + nvarguscamerasrc（Jetson 硬件加速），支持 fallback 到 V4L2
- **颜色追踪**: HSV 色彩空间 + 形态学处理，追踪红/蓝/绿/黄/橙/紫 6 种颜色
- **运动检测**: 帧差法 + 高斯模糊 + 轮廓分析
- **中文渲染**: Pillow + Noto Sans CJK 字体
- **全屏显示**: OpenCV HighGUI 全屏窗口，画面水平镜像

## 📝 配置

部署目标在 `deploy.sh` 中配置:

```bash
REMOTE="jetson@192.168.1.19"    # Jetson Nano SSH 地址
REMOTE_DIR="~/rainbow_playground" # 远程部署目录
```
