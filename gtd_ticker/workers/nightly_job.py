import datetime
import time
from PySide6.QtCore import QThread, Signal
from gtd_ticker.core.storage import Storage
from gtd_ticker.services.ai_review import AIReviewService
from gtd_ticker.services.wxpusher import WxPusherService
from gtd_ticker.config import ARCHIVE_DIR

class NightlyJobWorker(QThread):
    """
    深夜打更人：独立线程在每日 23:30 处理历史存档解析，连接 AI 大模型，并将精美战报推送到手机。
    """
    job_completed = Signal(str) # 当夜间复盘完成时通知主线程（如在托盘弹出小气泡提示）
    
    def __init__(self):
        super().__init__()
        self.is_running = True
        self.last_run_date = None

    def run(self):
        while self.is_running:
            now = datetime.datetime.now()
            today_str = now.strftime("%Y-%m-%d")
            
            # 定时触发器：到达 23:30 且今日尚未执行
            if now.hour == 23 and now.minute >= 30 and self.last_run_date != today_str:
                self._execute_nightly_review(today_str)
                self.last_run_date = today_str
                
            for _ in range(60):
                if not self.is_running:
                    break
                time.sleep(1)

    def _execute_nightly_review(self, today_str: str):
        now_time_precise = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 1. 提取当日日志供大模型批判
        log_file = ARCHIVE_DIR / f"{today_str}.log"
        log_content = ""
        if log_file.exists():
            with open(log_file, "r", encoding="utf-8") as f:
                log_content = f.read()
                
        # 2. 提取明日高危告警任务
        tasks = Storage.load_tasks()
        high_tasks = [t for t in tasks if t.priority == "high"]
        pending_str = "\n".join([f"- [{t.category}] {t.title} (Deadline: {t.deadline})" for t in high_tasks])
        
        # 3. 构建给大模型的数据投喂模板
        prompt = (
            f"以下是我今天（{today_str}）的待办执行归档记录：\n"
            f"{log_content if log_content else '今天一条都没做，烂透了。'}\n\n"
            f"以下是明天死线迫在眉睫的紧急高危任务：\n"
            f"{pending_str if pending_str else '暂无紧急任务。'}\n\n"
            f"请为我生成一份每日总结与明日规划。"
        )
        
        # 4. 请求大模型 (同步阻塞请求，因此必须放在 QThread 里)
        ai_reply = AIReviewService.generate_summary(prompt)
        
        # 5. 拼装推向 WxPusher 的最终 Markdown
        report = f"# 📅 极客看板每日复盘 ({today_str})\n\n"
        report += f"> ⏱️ 生成时间：{now_time_precise} (防折叠标识)\n\n"
        
        if ai_reply:
            report += f"## 🤖 AI 教练锐评\n{ai_reply}\n\n"
        else:
            report += "## 🤖 AI 教练状态异常\nAI教练今日离线，无法生成评语。\n\n"
            
        # 安全降级，确保 WxPusher 至少能把核心数量推出去
        done_count = len([x for x in log_content.split('\n') if '[状态: DONE]' in x])
        report += f"---\n**今日斩杀数量**: {done_count}\n"
        report += f"**明日高危报警**: {len(high_tasks)}\n"
        
        # 发射到手机
        WxPusherService.send_message(report, summary=f"GTD 毒舌复盘 ({now_time_precise})")
        
        # 通知主进程 UI
        self.job_completed.emit("夜间复盘已生成并发送至微信。")

    def stop(self):
        self.is_running = False
        self.wait()
