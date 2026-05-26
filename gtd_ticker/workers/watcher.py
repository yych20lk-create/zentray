import datetime
import uuid
import time
from PySide6.QtCore import QThread, Signal
from gtd_ticker.core.models import Task
from gtd_ticker.core.storage import Storage

class WatcherWorker(QThread):
    """
    后台守护线程：每分钟扫描一次活动任务的超时情况以及周期任务的派发。
    严禁阻塞主线程，完全基于 Qt Signal 抛出事件。
    """
    tasks_updated = Signal()       # 通知 UI 层数据已在后台更新，需要重新读取和轮播
    task_overdue = Signal(object)  # 将被惩罚的 Task 对象抛给主线程去弹系统警告框

    def __init__(self):
        super().__init__()
        self.is_running = True

    def run(self):
        while self.is_running:
            self._do_maintenance()
            # 挂起 60 秒，通过细粒度分片循环实现快速退出响应
            for _ in range(60):
                if not self.is_running:
                    break
                time.sleep(1)

    def _do_maintenance(self):
        tasks = Storage.load_tasks()
        templates = Storage.load_periodic_templates()
        today = datetime.date.today()
        today_str = today.strftime("%Y-%m-%d")
        
        changed = False
        
        # ==========================================
        # 1. 扫描逾期惩罚
        # ==========================================
        for task in tasks:
            if task.deadline:
                try:
                    deadline_date = datetime.datetime.strptime(task.deadline, "%Y-%m-%d").date()
                    # 触发条件：真实日期晚于截止日期，并且今天还没有执行过惩罚操作
                    if today > deadline_date and task.overdue_penalty_date != today_str:
                        # 执行提权与顺延
                        pri = task.priority
                        task.priority = "medium" if pri == "low" else "high"
                        task.deadline = (deadline_date + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                        task.overdue_penalty_date = today_str
                        changed = True
                        
                        # 向主 UI 线程抛送拦截信号，让主线程调用系统弹窗和 WxPusher 报警
                        self.task_overdue.emit(task)
                except ValueError:
                    pass

        # ==========================================
        # 2. 扫描周期任务自动化派发
        # ==========================================
        tmpl_changed = False
        for tmpl in templates:
            periodicity = tmpl.periodicity
            if periodicity == "daily":
                prefix = today.strftime("%y%m%d")
            elif periodicity == "weekly":
                iso_year, iso_week, _ = today.isocalendar()
                prefix = f"{str(iso_year)[2:]}第{iso_week}周"
            elif periodicity == "monthly":
                prefix = today.strftime("%y%m")
            else:
                prefix = today.strftime("%y%m%d")
                
            if tmpl.last_generated_period != prefix:
                new_title = f"【{prefix}】{tmpl.base_title}"
                new_task = Task(
                    id=str(uuid.uuid4()),
                    title=new_title,
                    category=tmpl.category,
                    details=tmpl.details,
                    priority=tmpl.priority,
                    deadline="",
                    task_type="periodic_instance",
                    template_id=tmpl.template_id
                )
                tasks.append(new_task)
                tmpl.last_generated_period = prefix
                changed = True
                tmpl_changed = True

        # 持久化落盘并通知 UI 刷新
        if changed:
            Storage.save_tasks(tasks)
            self.tasks_updated.emit()
            
        if tmpl_changed:
            Storage.save_periodic_templates(templates)

    def stop(self):
        self.is_running = False
        self.wait()
