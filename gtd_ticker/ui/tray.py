import os
import sys
import uuid
import json
import subprocess
import threading
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QMessageBox, QApplication
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import QTimer, Qt, Signal, QObject

from gtd_ticker.core.models import Task
from gtd_ticker.core.storage import Storage
from gtd_ticker.core.scheduler import Scheduler
from gtd_ticker.config import POLLING_INTERVAL_MS, POMODORO_MINUTES

# ==========================================
# 1. 底层跨平台托盘接口抽象
# ==========================================
class TrayImplementation(QObject):
    """跨平台状态栏底层接口定义。"""
    action_received = Signal(str)

    def set_label(self, text: str):
        pass

    def update_menu(self, items: list):
        pass

    def show_notification(self, title: str, msg: str):
        pass

    def shutdown(self):
        pass

# ==========================================
# 2. Linux 原生 GNOME 桥接实现
# ==========================================
class LinuxBridgeTray(TrayImplementation):
    """通过系统 Python 和 AyatanaAppIndicator 实现的 Linux 顶栏文本滚动模块。"""
    def __init__(self):
        super().__init__()
        self.bridge_process = None
        self._start_bridge()

    def _start_bridge(self):
        bridge_script = os.path.join(os.path.dirname(__file__), "linux_tray_bridge.py")
        self.bridge_process = subprocess.Popen(
            ["/usr/bin/python3", bridge_script],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, bufsize=1
        )
        
        def read_bridge():
            for line in self.bridge_process.stdout:
                try:
                    data = json.loads(line)
                    if "action" in data:
                        self.action_received.emit(data["action"])
                except Exception:
                    pass
        threading.Thread(target=read_bridge, daemon=True).start()

    def _send(self, data):
        if self.bridge_process and self.bridge_process.poll() is None:
            try:
                self.bridge_process.stdin.write(json.dumps(data) + "\n")
                self.bridge_process.stdin.flush()
            except Exception:
                pass

    def set_label(self, text: str):
        self._send({"type": "label", "text": text})

    def update_menu(self, items: list):
        self._send({"type": "menu", "items": items})

    def show_notification(self, title: str, msg: str):
        tray = QSystemTrayIcon(QIcon.fromTheme("emblem-default"))
        tray.show()
        tray.showMessage(title, msg, QSystemTrayIcon.Information, 5000)
        QTimer.singleShot(6000, tray.hide)

    def shutdown(self):
        self._send({"type": "quit"})

# ==========================================
# 3. Windows/macOS 标准 Qt 实现
# ==========================================
class QtStandardTray(TrayImplementation):
    """标准的跨平台托盘，适用于 Windows / macOS 或不支持 AppIndicator 的桌面。"""
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.tray = QSystemTrayIcon()
        
        # Windows / Mac 下尝试使用默认图标或 fallback 图标
        fallback_icon = QIcon.fromTheme("emblem-default")
        if fallback_icon.isNull():
            # 这里如果有项目自带的 ico 可以换掉
            pass 
            
        self.tray.setIcon(fallback_icon)
        self.menu = QMenu()
        self.tray.setContextMenu(self.menu)
class QtStandardTray(TrayImplementation):
    """标准的跨平台托盘，适用于 Windows / macOS 或不支持 AppIndicator 的桌面。"""
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.tray = QSystemTrayIcon()
        
        fallback_icon = QIcon.fromTheme("emblem-default")
        self.tray.setIcon(fallback_icon)
        self.menu = QMenu()
        self.tray.setContextMenu(self.menu)
        self.tray.show()
        self.actions = []
        
    def set_label(self, text: str):
        self.tray.setToolTip(text)

    def update_menu(self, items: list):
        self.menu.clear()
        self.actions.clear()
        self._build_qt_menu(self.menu, items)

    def _build_qt_menu(self, qt_menu, items):
        for item in items:
            if item == "separator":
                qt_menu.addSeparator()
            elif "submenu" in item:
                submenu = QMenu(item["label"], qt_menu)
                self._build_qt_menu(submenu, item["submenu"])
                qt_menu.addMenu(submenu)
            else:
                action = QAction(item["label"], qt_menu)
                action.setEnabled(item.get("enabled", True))
                # 捕获闭包中的变量
                action.triggered.connect(lambda checked=False, aid=item["id"]: self.action_received.emit(aid))
                qt_menu.addAction(action)
                self.actions.append(action)

    def show_notification(self, title: str, msg: str):
        self.tray.showMessage(title, msg, QSystemTrayIcon.Information, 5000)

    def shutdown(self):
        self.tray.hide()

# 托盘后端工厂方法
def create_tray_backend(app) -> TrayImplementation:
    if sys.platform.startswith('linux'):
        try:
            # 探测 Linux 系统是否真正支持 GI 和 AppIndicator
            res = subprocess.run(["/usr/bin/python3", "-c", "import gi; gi.require_version('AppIndicator3', '0.1')"], capture_output=True, timeout=1)
            if res.returncode == 0:
                return LinuxBridgeTray()
        except Exception:
            pass
    # 其他情况 (Windows, macOS，或不兼容的 Linux) 退回到默认实现
    return QtStandardTray(app)

# ==========================================
# 4. 业务逻辑与状态管理器 (TrayManager)
# ==========================================
class TrayManager(QObject):
    """
    负责调度 GTD 任务与界面的交互。完全解耦了系统底层托盘实现，
    使核心代码极具可移植性和整洁性。
    """
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.scheduler = Scheduler()
        
        # 初始化跨平台托盘底层
        self.backend = create_tray_backend(app)
        self.backend.action_received.connect(self.handle_action)
        self.app.aboutToQuit.connect(self.backend.shutdown)

        # 状态参数
        self.pomodoro_remaining = 0
        self.is_pomodoro = False
        self.current_text = ""
        
        # 数据加载
        self.reload_data()
        
        # 后台轮训引擎 (常规任务检测)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_ticker)
        self.timer.start(POLLING_INTERVAL_MS)
        
        # 番茄钟心跳引擎
        self.pomodoro_timer = QTimer()
        self.pomodoro_timer.timeout.connect(self.tick_pomodoro)

    def handle_action(self, action_id):
        """中央事件路由"""
        if action_id == "new":
            self.open_new_task_dialog()
        elif action_id == "done":
            self.mark_current_task_done()
        elif action_id == "abandon":
            self.abandon_current_task()
        elif action_id == "edit":
            self.edit_current_task()
        elif action_id.startswith("select_task_"):
            task_id = action_id[len("select_task_"):]
            self.select_task(task_id)
        elif action_id == "pomodoro":
            self.start_pomodoro()
        elif action_id == "quit":
            self.app.quit()

    def update_menu_state(self):
        """动态刷新右键菜单状态"""
        task = self.scheduler.get_current()
        active_tasks = Storage.load_tasks()

        # Build 状态更新 submenu
        status_submenu = [
            {"id": "done", "label": "✅ 完成", "enabled": task is not None and not self.is_pomodoro},
            {"id": "abandon", "label": "❌ 废弃", "enabled": task is not None and not self.is_pomodoro}
        ]

        # Build 任务列表 submenu
        task_list_submenu = []
        if active_tasks:
            for t in active_tasks:
                emoji = "🔴" if t.priority == "high" else "🟡" if t.priority == "medium" else "🟢"
                prefix = "★ " if task and t.id == task.id else ""
                task_list_submenu.append({
                    "id": f"select_task_{t.id}",
                    "label": f"{prefix}{emoji} {t.title}",
                    "enabled": not self.is_pomodoro
                })
        else:
            task_list_submenu.append({
                "id": "no_tasks",
                "label": "暂无待办任务",
                "enabled": False
            })

        # Main items
        items = [
            {
                "id": "status_update",
                "label": "🔄 状态更新",
                "submenu": status_submenu,
                "enabled": task is not None and not self.is_pomodoro
            },
            {
                "id": "edit",
                "label": "📝 编辑查看",
                "enabled": task is not None and not self.is_pomodoro
            },
            {
                "id": "task_list",
                "label": "📋 任务列表",
                "submenu": task_list_submenu,
                "enabled": not self.is_pomodoro
            },
            "separator",
            {"id": "new", "label": "➕ 新建任务", "enabled": not self.is_pomodoro},
            {
                "id": "pomodoro",
                "label": f"🍅 专注 {POMODORO_MINUTES} 分钟" if not self.is_pomodoro else f"🍅 专注中 {self.pomodoro_remaining // 60:02d}:{self.pomodoro_remaining % 60:02d}",
                "enabled": not self.is_pomodoro
            },
            "separator",
            {"id": "quit", "label": "❌ 退出程序"}
        ]
        self.backend.update_menu(items)

    def set_display_text(self, text: str):
        """渲染状态栏文本 (自适应宽度，不滚动)"""
        if text != self.current_text:
            self.current_text = text
            self.backend.set_label(text)

    def reload_data(self):
        """重新载入磁盘任务并渲染"""
        tasks = Storage.load_tasks()
        self.scheduler.build_queue(tasks)
        self.update_ticker()

    def update_ticker(self):
        """标准循环帧：展示待办事项"""
        if self.scheduler.is_paused or self.is_pomodoro:
            return
            
        task = self.scheduler.get_next()
        if not task:
            text = "🎉 暂无待办事项"
            self.set_display_text(text)
        else:
            emoji = "🔴" if task.priority == "high" else "🟡" if task.priority == "medium" else "🟢"
            text = f"{emoji} {task.title}"
            self.set_display_text(text)
        
        self.update_menu_state()

    def select_task(self, task_id):
        """手动选择并切换至指定任务"""
        target_idx = -1
        for idx, t in enumerate(self.scheduler.queue):
            if t.id == task_id:
                target_idx = idx
                break
        if target_idx != -1:
            self.scheduler.cursor = target_idx
            task = self.scheduler.get_next()
            if task:
                emoji = "🔴" if task.priority == "high" else "🟡" if task.priority == "medium" else "🟢"
                text = f"{emoji} {task.title}"
                self.set_display_text(text)
                self.update_menu_state()

    def start_pomodoro(self):
        """启用番茄钟模式"""
        self.scheduler.pause()
        self.timer.stop()
        self.is_pomodoro = True
        self.pomodoro_remaining = POMODORO_MINUTES * 60
        self.pomodoro_timer.start(1000)
        self.tick_pomodoro()

    def tick_pomodoro(self):
        """番茄钟心跳刷新"""
        self.pomodoro_remaining -= 1
        mins = self.pomodoro_remaining // 60
        secs = self.pomodoro_remaining % 60
        text = f"🍅 专注中 {mins:02d}:{secs:02d}"
        
        self.set_display_text(text)
        self.update_menu_state()
        
        if self.pomodoro_remaining <= 0:
            self.pomodoro_timer.stop()
            self.scheduler.resume()
            self.is_pomodoro = False
            self.timer.start(POLLING_INTERVAL_MS)
            self.backend.show_notification("番茄钟完成", "辛苦了！请稍微休息一下。")
            self.update_ticker()

    def open_new_task_dialog(self):
        """启动创建任务模态框"""
        from gtd_ticker.ui.dialogs import TaskDialog
        dialog = TaskDialog()
        dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowStaysOnTopHint)
        
        if dialog.exec():
            data = dialog.get_data()
            task = Task(
                id=str(uuid.uuid4()),
                title=data["title"],
                category=data["category"],
                priority=data["priority"],
                deadline=data["deadline"] if data["deadline"] else None,
                details=data["details"],
                attachments=data["attachments"],
                task_type=data["task_type"]
            )
            
            if data["task_type"] == "periodic":
                from gtd_ticker.core.models import PeriodicTemplate
                tmpl = PeriodicTemplate(
                    base_title=data["title"],
                    category=data["category"],
                    periodicity=data["periodicity"],
                    details=data["details"],
                    priority=data["priority"]
                )
                templates = Storage.load_periodic_templates()
                templates.append(tmpl)
                Storage.save_periodic_templates(templates)
            else:
                tasks = Storage.load_tasks()
                tasks.append(task)
                Storage.save_tasks(tasks)
                
            self.reload_data()

    def mark_current_task_done(self):
        """完成当前任务的原子操作"""
        task = self.scheduler.get_current()
        if not task:
            return
            
        Storage.archive_task(task, "DONE")
        
        tasks = Storage.load_tasks()
        tasks = [t for t in tasks if t.id != task.id]
        Storage.save_tasks(tasks)
        
        self.reload_data()
        self.backend.show_notification("任务完成", f"已斩杀: {task.title}")

    def abandon_current_task(self):
        """废弃当前任务的原子操作"""
        task = self.scheduler.get_current()
        if not task:
            return
            
        Storage.archive_task(task, "ABANDONED")
        
        tasks = Storage.load_tasks()
        tasks = [t for t in tasks if t.id != task.id]
        Storage.save_tasks(tasks)
        
        self.reload_data()
        self.backend.show_notification("任务废弃", f"已废弃: {task.title}")

    def edit_current_task(self):
        """编辑当前任务"""
        task = self.scheduler.get_current()
        if not task:
            return
        from gtd_ticker.ui.dialogs import TaskDialog
        dialog = TaskDialog(task=task)
        dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowStaysOnTopHint)
        
        if dialog.exec():
            data = dialog.get_data()
            task.title = data["title"]
            task.category = data["category"]
            task.priority = data["priority"]
            task.deadline = data["deadline"] if data["deadline"] else None
            task.details = data["details"]
            task.attachments = data["attachments"]
            
            tasks = Storage.load_tasks()
            for i, t in enumerate(tasks):
                if t.id == task.id:
                    tasks[i] = task
                    break
            Storage.save_tasks(tasks)
            self.reload_data()

    def show_overdue_warning(self, task):
        """强制逾期警告"""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("🚨 任务逾期警告")
        msg.setText(f"你的任务【{task.title}】已逾期！")
        msg.setInformativeText("系统已将其自动延期1天，并强制提升优先级！马上处理！")
        msg.setWindowFlags(msg.windowFlags() | Qt.WindowStaysOnTopHint)
        msg.exec()

    def show_notification(self, text):
        """暴露给外部 workers 的通知接口"""
        self.backend.show_notification("GTD Ticker", text)
