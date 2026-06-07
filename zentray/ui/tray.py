import os
import sys
import uuid
import json
import subprocess
import threading
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QMessageBox, QApplication
from PySide6.QtGui import QIcon, QAction, QImage, QPainter, QColor, QPen
from PySide6.QtCore import QTimer, Qt, Signal, QObject
import random

from zentray.core.models import Task
from zentray.core.storage import Storage
from zentray.core.scheduler import Scheduler
from zentray.config import POLLING_INTERVAL_MS, POMODORO_MINUTES, DATA_DIR

# ==========================================
# 1. 底层跨平台托盘接口抽象
# ==========================================
class TrayImplementation(QObject):
    """跨平台状态栏底层接口定义。"""
    action_received = Signal(str)

    def set_label(self, text: str):
        pass

    def set_icon(self, name: str):
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
        icon_dir = os.path.join(DATA_DIR, "icons")
        self.bridge_process = subprocess.Popen(
            ["/usr/bin/python3", bridge_script, icon_dir],
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

    def set_icon(self, name: str):
        self._send({"type": "icon", "icon": name})

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
        
        fallback_icon = QIcon.fromTheme("emblem-default")
        self.tray.setIcon(fallback_icon)
        self.menu = QMenu()
        self.tray.setContextMenu(self.menu)
        self.tray.show()
        self.actions = []
        
    def set_label(self, text: str):
        self.tray.setToolTip(text)

    def set_icon(self, name: str):
        icon_path = os.path.join(DATA_DIR, "icons", f"{name}.png")
        if os.path.exists(icon_path):
            self.tray.setIcon(QIcon(icon_path))

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
                if "icon" in item:
                    icon_path = os.path.join(DATA_DIR, "icons", f"{item['icon']}.png")
                    if os.path.exists(icon_path):
                        submenu.setIcon(QIcon(icon_path))
                self._build_qt_menu(submenu, item["submenu"])
                qt_menu.addMenu(submenu)
            else:
                action = QAction(item["label"], qt_menu)
                action.setEnabled(item.get("enabled", True))
                if "icon" in item:
                    icon_path = os.path.join(DATA_DIR, "icons", f"{item['icon']}.png")
                    if os.path.exists(icon_path):
                        action.setIcon(QIcon(icon_path))
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
        
        # 状态参数
        self.pomodoro_remaining = 0
        self.is_pomodoro = False
        self.current_text = ""
        self.is_loading = True
        self.last_menu_items = None
        
        # 先生成饼图图标，使底层的桥接进程能正常加载
        self.generate_pie_icons()
        
        # 初始化跨平台托盘底层
        self.backend = create_tray_backend(app)
        self.backend.action_received.connect(self.handle_action)
        self.app.aboutToQuit.connect(self.backend.shutdown)

        # 启动随机加载提示
        welcome_msgs = [
            "🚀 正在同步星际轨道数据...请稍候!",
            "👾 正在捕捉摸鱼的灵感...",
            "🔮 正在连接高效超能力水晶球...",
            "☕ 正在为您注入虚拟咖啡因...",
            "🔋 动力电池已加载 99.9%...冲冲冲!"
        ]
        self.set_display_text(random.choice(welcome_msgs))
        self.set_icon("pie_none_0")
        
        # 2.5秒后加载真实数据
        QTimer.singleShot(2500, self.finish_loading)
        
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
        elif action_id == "progress":
            self.update_current_task_progress()
        elif action_id == "edit":
            self.edit_current_task()
        elif action_id.startswith("task_action_"):
            task_id = action_id[len("task_action_"):]
            self.show_task_action_dialog(task_id)
        elif action_id.startswith("select_task_"):
            task_id = action_id[len("select_task_"):]
            self.select_task(task_id)
        elif action_id.startswith("edit_task_list_"):
            task_id = action_id[len("edit_task_list_"):]
            self.edit_specific_task(task_id)
        elif action_id.startswith("done_task_list_"):
            task_id = action_id[len("done_task_list_"):]
            self.mark_specific_task_done(task_id)
        elif action_id.startswith("abandon_task_list_"):
            task_id = action_id[len("abandon_task_list_"):]
            self.abandon_specific_task(task_id)
        elif action_id.startswith("edit_periodic_"):
            template_id = action_id[len("edit_periodic_"):]
            self.edit_periodic_template(template_id)
        elif action_id.startswith("terminate_periodic_"):
            template_id = action_id[len("terminate_periodic_"):]
            self.terminate_periodic_template(template_id)
        elif action_id == "pomodoro":
            self.start_pomodoro()
        elif action_id == "stop_pomodoro":
            self.stop_pomodoro()
        elif action_id == "extend_pomodoro":
            self.extend_pomodoro()
        elif action_id == "quit":
            self.app.quit()

    def update_menu_state(self):
        """动态刷新右键菜单状态"""
        if self.is_pomodoro:
            items = [
                {"id": "stop_pomodoro", "label": "⏹ 中止当前专注"},
                {"id": "extend_pomodoro", "label": "➕ 延长当前专注 (+10分钟)"}
            ]
            if self.last_menu_items != items:
                self.last_menu_items = items
                self.backend.update_menu(items)
            return

        task = self.scheduler.get_current()
        active_tasks = Storage.load_tasks()
        periodic_templates = Storage.load_periodic_templates()

        # Build 状态更新 submenu
        status_submenu = [
            {"id": "done", "label": "✅ 完成", "enabled": task is not None and not self.is_pomodoro},
            {"id": "abandon", "label": "❌ 废弃", "enabled": task is not None and not self.is_pomodoro}
        ]

        # Build 任务列表 submenu
        task_list_submenu = []
        if active_tasks:
            task_list_submenu.append({"id": "label_active", "label": "【当前活跃任务】", "enabled": False})
            for t in active_tasks:
                prefix = "★ " if task and t.id == task.id else ""
                
                # 计算与顶栏完全一致的饼图图标文件名
                prio = t.priority if t.priority in ["high", "medium", "low"] else "medium"
                progress_val = getattr(t, "progress", 0)
                pct = max(0, min(100, (progress_val // 10) * 10))
                icon_name = f"pie_{prio}_{pct}"
                
                task_list_submenu.append({
                    "id": f"task_action_{t.id}",
                    "label": f"{prefix}{t.title}",
                    "icon": icon_name,
                    "enabled": not self.is_pomodoro
                })
        else:
            task_list_submenu.append({
                "id": "no_tasks",
                "label": "暂无待办任务",
                "enabled": False
            })

        task_list_submenu.append("separator")

        if periodic_templates:
            task_list_submenu.append({"id": "label_periodic", "label": "【周期任务模板】", "enabled": False})
            for pt in periodic_templates:
                emoji = "🔁"
                pt_submenu = [
                    {"id": f"edit_periodic_{pt.template_id}", "label": "📝 编辑模板"},
                    {"id": f"terminate_periodic_{pt.template_id}", "label": "🛑 终止周期任务"}
                ]
                task_list_submenu.append({
                    "id": f"periodic_{pt.template_id}",
                    "label": f"{emoji} {pt.base_title}",
                    "submenu": pt_submenu,
                    "enabled": not self.is_pomodoro
                })
        else:
            task_list_submenu.append({
                "id": "no_periodic",
                "label": "暂无周期任务",
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
                "id": "progress",
                "label": "📊 更新进度",
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
                "label": f"🍅 专注 {POMODORO_MINUTES} 分钟" if not self.is_pomodoro else "🍅 专注中...",
                "enabled": not self.is_pomodoro
            },
            "separator",
            {"id": "quit", "label": "❌ 退出程序"}
        ]
        if self.last_menu_items != items:
            self.last_menu_items = items
            self.backend.update_menu(items)

    def set_display_text(self, text: str):
        """渲染状态栏文本 (自适应宽度，不滚动)"""
        if text != self.current_text:
            self.current_text = text
            self.backend.set_label(text)

    def reload_data(self):
        """重新载入磁盘任务并渲染"""
        if self.is_loading:
            return
        tasks = Storage.load_tasks()
        self.scheduler.build_queue(tasks)
        self.update_ticker()

    def update_ticker(self):
        """标准循环帧：展示待办事项"""
        if self.is_loading:
            return
        if self.scheduler.is_paused or self.is_pomodoro:
            return
            
        task = self.scheduler.get_next()
        if not task:
            text = "🎉 暂无待办事项"
            self.set_display_text(text)
            self.set_icon("pie_none_0")
        else:
            text = task.title
            self.set_display_text(text)
            # 动态更新饼图图标
            prio = task.priority if task.priority in ["high", "medium", "low"] else "medium"
            progress_val = getattr(task, "progress", 0)
            pct = max(0, min(100, (progress_val // 10) * 10))
            self.set_icon(f"pie_{prio}_{pct}")
        
        self.update_menu_state()

    def set_icon(self, name: str):
        """更新托盘图标"""
        self.backend.set_icon(name)

    def finish_loading(self):
        """结束程序加载状态，载入真实任务"""
        self.is_loading = False
        self.reload_data()

    def generate_pie_icons(self):
        """在本地生成一套 0%-100% 进度的圆饼图图标"""
        import os
        from PySide6.QtGui import QImage, QPainter, QColor, QPen
        from PySide6.QtCore import Qt
        
        icon_dir = os.path.join(DATA_DIR, "icons")
        os.makedirs(icon_dir, exist_ok=True)
        
        colors = {
            "high": QColor(235, 87, 87),    # 扁平化红色
            "medium": QColor(242, 201, 76), # 扁平化黄色
            "low": QColor(39, 174, 96),     # 扁平化绿色
        }
        
        for key, color in colors.items():
            for pct in range(0, 110, 10):
                img_path = os.path.join(icon_dir, f"pie_{key}_{pct}.png")
                image = QImage(22, 22, QImage.Format_ARGB32)
                image.fill(QColor(0, 0, 0, 0))
                
                painter = QPainter(image)
                painter.setRenderHint(QPainter.Antialiasing)
                
                # 背景轨道 (Desaturated/Lighter)
                bg_color = QColor(color)
                bg_color.setAlpha(60)
                painter.setBrush(bg_color)
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(2, 2, 18, 18)
                
                # 顺时针进度填充 (0-100%)
                if pct > 0:
                    painter.setBrush(color)
                    start_angle = 90 * 16
                    span_angle = -int(360 * (pct / 100.0) * 16)
                    painter.drawPie(2, 2, 18, 18, start_angle, span_angle)
                
                # 边缘圆环
                painter.setBrush(Qt.NoBrush)
                painter.setPen(QPen(color, 1))
                painter.drawEllipse(2, 2, 18, 18)
                
                painter.end()
                image.save(img_path)
                
        # 灰色无状态图标 (pie_none_0)
        img_path = os.path.join(icon_dir, "pie_none_0.png")
        image = QImage(22, 22, QImage.Format_ARGB32)
        image.fill(QColor(0, 0, 0, 0))
        
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        
        none_color = QColor(142, 142, 147)
        bg_color = QColor(none_color)
        bg_color.setAlpha(60)
        painter.setBrush(bg_color)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(2, 2, 18, 18)
        
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(none_color, 1))
        painter.drawEllipse(2, 2, 18, 18)
        
        painter.end()
        image.save(img_path)

        # 番茄钟专用图标 (pomodoro)
        img_path = os.path.join(icon_dir, "pomodoro.png")
        image = QImage(22, 22, QImage.Format_ARGB32)
        image.fill(QColor(0, 0, 0, 0))
        
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 红色番茄主体
        painter.setBrush(QColor(235, 87, 87)) # 番茄红
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(3, 5, 16, 14) # 稍微扁平的椭圆
        
        # 绿色番茄蒂/叶
        painter.setBrush(QColor(39, 174, 96)) # 叶片绿
        from PySide6.QtGui import QPolygon
        from PySide6.QtCore import QPoint
        poly = QPolygon([
            QPoint(11, 2),
            QPoint(8, 6),
            QPoint(14, 6)
        ])
        painter.drawPolygon(poly)
        
        painter.end()
        image.save(img_path)

    def update_current_task_progress(self):
        """打开当前任务的进度记录弹窗"""
        task = self.scheduler.get_current()
        if not task:
            return
        from zentray.ui.dialogs import ProgressDialog
        dialog = ProgressDialog(task=task)
        dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowStaysOnTopHint)
        
        if dialog.exec():
            percent, note = dialog.get_data()
            task.progress = percent
            
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_desc = note if note else f"进度更新为 {percent}%"
            task.progress_logs.append({
                "time": timestamp,
                "percent": percent,
                "note": log_desc
            })
            
            # 保存数据并刷新
            tasks = Storage.load_tasks()
            for i, t in enumerate(tasks):
                if t.id == task.id:
                    tasks[i] = task
                    break
            Storage.save_tasks(tasks)
            self.reload_data()

    def select_task(self, task_id):
        """手动选择并切换至指定任务"""
        target_idx = -1
        for idx, t in enumerate(self.scheduler.queue):
            if t.id == task_id:
                target_idx = idx
                break
        if target_idx != -1:
            self.scheduler.cursor = target_idx
            self.update_ticker()

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
        text = f"专注中 {mins:02d}:{secs:02d}"
        
        self.set_display_text(text)
        self.set_icon("pomodoro")
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
        from zentray.ui.dialogs import TaskDialog
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
                from zentray.core.models import PeriodicTemplate
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
        from zentray.ui.dialogs import TaskDialog
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

    def edit_specific_task(self, task_id):
        tasks = Storage.load_tasks()
        target_task = None
        for t in tasks:
            if t.id == task_id:
                target_task = t
                break
        if not target_task:
            return

        from zentray.ui.dialogs import TaskDialog
        dialog = TaskDialog(task=target_task)
        dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowStaysOnTopHint)
        
        if dialog.exec():
            data = dialog.get_data()
            target_task.title = data["title"]
            target_task.category = data["category"]
            target_task.priority = data["priority"]
            target_task.deadline = data["deadline"] if data["deadline"] else None
            target_task.details = data["details"]
            target_task.attachments = data["attachments"]
            
            Storage.save_tasks(tasks)
            self.reload_data()

    def mark_specific_task_done(self, task_id):
        tasks = Storage.load_tasks()
        target_task = None
        for t in tasks:
            if t.id == task_id:
                target_task = t
                break
        if not target_task:
            return
            
        Storage.archive_task(target_task, "DONE")
        tasks = [t for t in tasks if t.id != task_id]
        Storage.save_tasks(tasks)
        self.reload_data()
        self.backend.show_notification("任务完成", f"已斩杀: {target_task.title}")

    def abandon_specific_task(self, task_id):
        tasks = Storage.load_tasks()
        target_task = None
        for t in tasks:
            if t.id == task_id:
                target_task = t
                break
        if not target_task:
            return
            
        Storage.archive_task(target_task, "ABANDONED")
        tasks = [t for t in tasks if t.id != task_id]
        Storage.save_tasks(tasks)
        self.reload_data()
        self.backend.show_notification("任务废弃", f"已废弃: {target_task.title}")

    def edit_periodic_template(self, template_id):
        templates = Storage.load_periodic_templates()
        target_template = None
        for pt in templates:
            if pt.template_id == template_id:
                target_template = pt
                break
        if not target_template:
            return
            
        from zentray.ui.dialogs import TaskDialog
        dialog = TaskDialog(task=target_template)
        dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowStaysOnTopHint)
        
        if dialog.exec():
            data = dialog.get_data()
            target_template.base_title = data["title"]
            target_template.category = data["category"]
            target_template.priority = data["priority"]
            target_template.details = data["details"]
            
            Storage.save_periodic_templates(templates)
            self.reload_data()
            self.backend.show_notification("周期任务", "周期任务模板已更新。")

    def terminate_periodic_template(self, template_id):
        templates = Storage.load_periodic_templates()
        templates = [pt for pt in templates if pt.template_id != template_id]
        Storage.save_periodic_templates(templates)
        self.reload_data()
        self.backend.show_notification("周期任务", "该周期任务已终止。")

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
        self.backend.show_notification("ZenTray", text)

    def show_task_action_dialog(self, task_id):
        # 查找任务
        tasks = Storage.load_tasks()
        task = next((t for t in tasks if t.id == task_id), None)
        if not task:
            return
            
        from zentray.ui.dialogs import TaskActionDialog
        dialog = TaskActionDialog(task=task)
        dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowStaysOnTopHint)
        if dialog.exec():
            action = dialog.get_selected_action()
            if action == "select":
                self.select_task(task_id)
            elif action == "edit":
                self.edit_specific_task(task_id)
            elif action == "done":
                self.mark_specific_task_done(task_id)
            elif action == "abandon":
                self.abandon_specific_task(task_id)
            elif action == "progress":
                from zentray.ui.dialogs import ProgressDialog
                pd = ProgressDialog(task=task)
                pd.setWindowFlags(pd.windowFlags() | Qt.WindowStaysOnTopHint)
                if pd.exec():
                    percent, note = pd.get_data()
                    task.progress = percent
                    import datetime
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    log_desc = note if note else f"进度更新为 {percent}%"
                    task.progress_logs.append({
                        "time": timestamp,
                        "percent": percent,
                        "note": log_desc
                    })
                    # 保存任务
                    for i, t in enumerate(tasks):
                        if t.id == task.id:
                            tasks[i] = task
                            break
                    Storage.save_tasks(tasks)
                    self.reload_data()

    def stop_pomodoro(self):
        """中止当前专注"""
        self.pomodoro_timer.stop()
        self.scheduler.resume()
        self.is_pomodoro = False
        self.timer.start(POLLING_INTERVAL_MS)
        self.update_ticker()
        self.backend.show_notification("番茄钟已中止", "当前专注会话已手动中止。")

    def extend_pomodoro(self):
        """延长当前专注 10 分钟"""
        self.pomodoro_remaining += 10 * 60
        self.tick_pomodoro()
        self.backend.show_notification("番茄钟延时", "已成功为您延长 10 分钟专注时间！")
