#!/bin/bash
# deploy.sh — 部署彩虹乐园到 Jetson Nano
#
# 用法: ./deploy.sh [run|sync|install]
#   sync    — 仅同步代码
#   install — 安装依赖
#   run     — 同步并运行（默认）

set -e

REMOTE="jetson@192.168.1.19"
REMOTE_DIR="~/rainbow_playground"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

sync_code() {
    echo "📦 同步代码到 ${REMOTE}:${REMOTE_DIR} ..."
    rsync -avz --delete \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='.DS_Store' \
        --exclude='.git' \
        --exclude='.spec-workflow' \
        --exclude='.gitignore' \
        --exclude='README.md' \
        "${SCRIPT_DIR}/" "${REMOTE}:${REMOTE_DIR}/"
    echo "✅ 同步完成"
}

install_deps() {
    echo "📥 安装依赖..."
    ssh "${REMOTE}" "pip3 install Pillow"
    echo "✅ 依赖安装完成"
}

run_app() {
    echo "🚀 启动彩虹乐园..."
    ssh -t "${REMOTE}" "export DISPLAY=:0 && cd ${REMOTE_DIR} && python3 main.py"
}

ACTION="${1:-run}"

case "${ACTION}" in
    sync)
        sync_code
        ;;
    install)
        install_deps
        ;;
    run)
        sync_code
        run_app
        ;;
    *)
        echo "用法: $0 [run|sync|install]"
        exit 1
        ;;
esac
