import sys
import os

# 将项目根目录（gtd_ticker 的上一级目录）加入系统路径，解决绝对导包的问题
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 修复 Linux 下无法唤出 Fcitx5 输入法的底层 BUG (强制使用 ibus 桥接，解决 PySide6 Qt ABI 不兼容问题)
if sys.platform.startswith('linux'):
    os.environ["QT_IM_MODULE"] = "ibus"
    os.environ.setdefault("XMODIFIERS", "@im=fcitx")

from PySide6.QtWidgets import QApplication
from gtd_ticker.services.system_utils import SingleInstanceGuard, HotkeyListener
from gtd_ticker.ui.tray import TrayManager
from gtd_ticker.ui.overlay import QuickAddOverlay
from gtd_ticker.workers.watcher import WatcherWorker
from gtd_ticker.workers.nightly_job import NightlyJobWorker
from gtd_ticker.config import HOTKEY_QUICK_ADD

def main():
    # 1. 启动防多开锁
    guard = SingleInstanceGuard()
    
    # 2. 初始化 QApplication
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False) # 关键：防止所有窗口关闭后应用退出，因为我们是托盘应用
    
    # 3. 初始化 UI
    tray = TrayManager(app)
    
    # 3.1 初始化无边框叠加层与全局快捷键
    overlay = QuickAddOverlay()
    overlay.task_added.connect(tray.reload_data)
    
    hotkey = HotkeyListener(HOTKEY_QUICK_ADD)
    hotkey.triggered.connect(overlay.show_center)
    hotkey.start()
    
    # 4. 启动后台超时与派发巡检线程
    watcher = WatcherWorker()
    watcher.tasks_updated.connect(tray.reload_data)
    watcher.task_overdue.connect(tray.show_overdue_warning)
    watcher.start()
    
    # 5. 启动大模型夜间打更人线程
    nightly = NightlyJobWorker()
    nightly.job_completed.connect(tray.show_notification)
    nightly.start()
    
    # 6. 进入事件循环
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
