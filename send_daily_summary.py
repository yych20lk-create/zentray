#!/usr/bin/env python3
import sys
import os
import datetime

# 将项目根目录加入系统路径以支持模块导入
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from zentray.workers.nightly_job import execute_nightly_review

def main():
    print("🚀 正在手动触发生成并发送今日 ZenTray 禅定日报...")
    
    # 获取今天日期字符串并立即执行复盘逻辑
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    try:
        execute_nightly_review(today_str)
        print("✅ 发送指令已执行完毕！请检查您的微信 WxPusher 提醒。")
    except Exception as e:
        print(f"❌ 发送失败，错误信息: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
