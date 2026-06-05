#!/bin/bash
# GTD Ticker 快速启动脚本

# 进入项目根目录
cd "$(dirname "$0")"

# 如果存在 .env 文件，则加载其中的环境变量配置 (如 AI_API_KEY 等)
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# 检查虚拟环境是否已经存在
if [ -f "venv/bin/python3" ]; then
    PYTHON_CMD="venv/bin/python3"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
else
    echo "未找到 Python3，请先安装。"
    exit 1
fi

if [ ! -d "venv" ]; then
    echo "初始化虚拟环境..."
    $PYTHON_CMD -m venv venv
    source venv/bin/activate
    echo "安装依赖..."
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# 清理可能残留的旧进程，防止端口或资源被占用
echo "清理旧进程..."
pkill -f "notification_service/main.py" || true
pkill -f "gtd_ticker/main.py" || true
pkill -f "linux_tray_bridge.py" || true

# 启动通知服务 (在后台)
echo "启动本地通知公共服务..."
nohup venv/bin/python notification_service/main.py > /dev/null 2>&1 &

# 启动程序
echo "启动 GTD Ticker..."
nohup venv/bin/python gtd_ticker/main.py > /dev/null 2>&1 &
