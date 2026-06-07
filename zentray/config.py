import os
import sys
from pathlib import Path
from platformdirs import user_data_dir

APP_NAME = "ZenTray"
APP_AUTHOR = "Zen-Geek"

# 跨平台标准数据目录
DATA_DIR = Path(user_data_dir(APP_NAME, APP_AUTHOR))
ACTIVE_TASKS_FILE = DATA_DIR / "active_tasks.json"
PERIODIC_TEMPLATES_FILE = DATA_DIR / "periodic_templates.json"
ARCHIVE_DIR = DATA_DIR / "archive"

# WxPusher 默认配置
WXPUSHER_APP_TOKEN = os.getenv("WXPUSHER_APP_TOKEN", "AT_83wUvfSiTgLS0DXzQDY1mcoQA4ykKfeF")
WXPUSHER_UID = os.getenv("WXPUSHER_UID", "UID_InpmBp9KOuVg4C7to5K8CgfhKfRC")

# LLM AI 配置 (用于 Nightly Job)
AI_API_BASE_URL = os.getenv("AI_API_BASE_URL", "https://api.openai.com/v1")
AI_API_KEY = os.getenv("AI_API_KEY", "")
AI_MODEL_NAME = os.getenv("AI_MODEL_NAME", "gpt-4o")

# UI 与调度设置
POLLING_INTERVAL_MS = 30000  # 托盘轮播间隔 (30秒)
POMODORO_MINUTES = 25        # 番茄钟专注时长
HOTKEY_QUICK_ADD = "<cmd>+<alt>+t" if sys.platform == 'darwin' else "<ctrl>+<alt>+t"

# 确保核心目录存在
os.makedirs(ARCHIVE_DIR, exist_ok=True)
