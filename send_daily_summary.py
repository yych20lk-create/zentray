#!/usr/bin/env python3
import os
import json
import requests
import re
from datetime import datetime

# ================= 配置区 =================
# 填入你刚刚在 WxPusher 后台获取的凭证
APP_TOKEN = "AT_83wUvfSiTgLS0DXzQDY1mcoQA4ykKfeF"
MY_UID = "UID_InpmBp9KOuVg4C7to5K8CgfhKfRC"
# ==========================================

BASE_DIR = os.path.expanduser("~/.local/share/my_todo_ticker/")
ACTIVE_FILE = os.path.join(BASE_DIR, "active_tasks.json")
TODAY_STR = datetime.now().strftime("%Y-%m-%d")
LOG_FILE = os.path.join(BASE_DIR, f"archive/{TODAY_STR}.log")

def get_stats():
    done_tasks = []
    discard_tasks = []
    
    # 1. 解析今日归档日志 (完成与废弃)
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                # 匹配格式: [2026-05-24 10:00:00] [状态: DONE] [分类: 工作] [HIGH] 任务标题 - 任务详情 (附件数: X)
                m = re.match(r'\[.*?\]\s+\[状态:\s*(.*?)\]\s+\[分类:\s*(.*?)\]\s+\[(.*?)\]\s+(.*?)\s+-', line)
                if m:
                    status, category, priority, title = m.groups()
                    task_info = f"[{category}] {title}"
                    if status == "DONE":
                        done_tasks.append(task_info)
                    elif status == "DISCARD":
                        discard_tasks.append(task_info)

    # 2. 解析明日待办与逾期警告
    overdue_tasks = []
    pending_tasks = {"high": [], "medium": [], "low": []}
    
    if os.path.exists(ACTIVE_FILE):
        try:
            with open(ACTIVE_FILE, 'r', encoding='utf-8') as f:
                tasks = json.load(f)
                for t in tasks:
                    cat = t.get("category", "无")
                    title = t.get("title", "未命名")
                    dl = t.get("deadline", "")
                    pri = t.get("priority", "low")
                    
                    # 判断今日是否被逾期惩罚器捕捉过
                    if t.get("overdue_penalty_date") == TODAY_STR:
                        overdue_tasks.append(f"[{cat}] {title}")
                    
                    dl_str = f" (截至: {dl})" if dl else ""
                    task_info = f"[{cat}] {title}{dl_str}"
                    
                    if pri in pending_tasks:
                        pending_tasks[pri].append(task_info)
        except Exception:
            pass

    return done_tasks, discard_tasks, overdue_tasks, pending_tasks

def send_wechat_msg_dynamic(markdown_content, now_time):
    url = "https://wxpusher.zjiecode.com/api/send/message"
    payload = {
        "appToken": APP_TOKEN,
        "content": markdown_content,
        "summary": f"📅 GTD复盘 ({now_time})",
        "contentType": 3,
        "uids": [MY_UID]
    }
    response = requests.post(url, json=payload)
    return response.json()

if __name__ == "__main__":
    done_tasks, discard_tasks, overdue_tasks, pending_tasks = get_stats()
    now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 组装精细化 Markdown 战报
    report = f"# 📅 GTD 每日复盘 ({TODAY_STR})\n\n"
    report += f"> ⏱️ 生成时间：{now_time}\n\n"
    
    # 【🚨 逾期惩罚警告】分区
    if overdue_tasks:
        report += "## 🚨 逾期惩罚警告\n"
        report += "> 以下任务已逾期，系统已自动顺延截止日期并**强制提高优先级**！\n"
        for t in overdue_tasks:
            report += f"- ⚠️ {t}\n"
        report += "\n"
        
    # 【🏆 今日战果】分区
    report += "## 🏆 今日战果\n"
    report += f"**✅ 完成任务 ({len(done_tasks)} 项)**\n"
    for t in done_tasks:
        report += f"- {t}\n"
    if not done_tasks: report += "- 无\n"
    
    report += f"\n**🗑️ 废弃任务 ({len(discard_tasks)} 项)**\n"
    for t in discard_tasks:
        report += f"- {t}\n"
    if not discard_tasks: report += "- 无\n"
    
    # 【⏳ 明日待办清册】分区
    total_pending = sum(len(x) for x in pending_tasks.values())
    report += f"\n## ⏳ 明日待办清册 (共 {total_pending} 项)\n"
    
    report += f"\n**🔴 紧急高危 ({len(pending_tasks['high'])} 项)**\n"
    for t in pending_tasks["high"]: report += f"- {t}\n"
    if not pending_tasks['high']: report += "- 无\n"
    
    report += f"\n**🟡 中等优先级 ({len(pending_tasks['medium'])} 项)**\n"
    for t in pending_tasks["medium"]: report += f"- {t}\n"
    if not pending_tasks['medium']: report += "- 无\n"
    
    report += f"\n**🟢 低优先级 ({len(pending_tasks['low'])} 项)**\n"
    for t in pending_tasks["low"]: report += f"- {t}\n"
    if not pending_tasks['low']: report += "- 无\n"
    
    report += "\n> 💡 *“种一棵树最好的时间是十年前，其次是现在。”*\n"
    
    # 发送请求
    res = send_wechat_msg_dynamic(report, now_time)
    if res.get("code") == 1000:
        print("✅ 微信推送成功！(已加入时间戳防拦截)")
    else:
        print(f"❌ 推送失败: {res}")