@echo off
REM GTD Ticker 快速启动脚本 (Windows)

cd /d "%~dp0"

IF NOT EXIST "venv" (
    echo 初始化虚拟环境...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo 安装依赖...
    pip install -r requirements.txt
) ELSE (
    call venv\Scripts\activate.bat
)

echo 启动 GTD Ticker...
start pythonw gtd_ticker/main.py
