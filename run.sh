#!/bin/bash
# GTD Ticker 快速启动脚本

# 进入项目根目录
cd "$(dirname "$0")"

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

# 启动程序
echo "启动 GTD Ticker..."
python gtd_ticker/main.py &
