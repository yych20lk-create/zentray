import sys
from PySide6.QtNetwork import QLocalServer, QLocalSocket

class SingleInstanceGuard:
    """
    单例模式锁：基于 Qt 本地套接字实现跨平台防多开。
    如果检测到同名服务器正在运行，则直接退出。
    """
    def __init__(self, server_name="GTDTicker_SingleInstance"):
        self.server_name = server_name
        self.socket = QLocalSocket()
        self.socket.connectToServer(self.server_name)
        
        if self.socket.waitForConnected(500):
            print("Another instance of GTDTicker is already running. Exiting.")
            sys.exit(1)
            
        self.server = QLocalServer()
        self.server.removeServer(self.server_name)
        if not self.server.listen(self.server_name):
            print("Failed to start SingleInstanceGuard server. Exiting.")
            sys.exit(1)

# TODO: 锁屏与空闲检测的抽象接口
def is_screen_locked() -> bool:
    """检测屏幕是否处于锁屏状态 (将在后续多平台差异化实现)"""
    return False

def get_idle_time_seconds() -> int:
    """获取键鼠空闲时间 (将在后续多平台差异化实现)"""
    return 0

from pynput import keyboard
from PySide6.QtCore import QObject, Signal

class HotkeyListener(QObject):
    """
    后台全局快捷键监听器。
    使用 pynput 监听，当命中配置的快捷键时，通过 Qt Signal 唤醒主 UI 线程里的闪电添加窗口。
    """
    triggered = Signal()

    def __init__(self, hotkey_str="<ctrl>+<alt>+t"):
        super().__init__()
        self.hotkey_str = hotkey_str
        self.listener = None

    def start(self):
        self.listener = keyboard.GlobalHotKeys({
            self.hotkey_str: self.on_activate
        })
        self.listener.start()

    def on_activate(self):
        self.triggered.emit()

    def stop(self):
        if self.listener:
            self.listener.stop()
