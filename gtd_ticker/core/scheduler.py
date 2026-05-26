import random
from typing import List, Optional
from gtd_ticker.core.models import Task

class Scheduler:
    """
    核心加权滚动算法引擎。
    负责根据优先级生成轮播队列，并控制暂停/恢复（用于专注模式）。
    """
    def __init__(self):
        self.queue: List[Task] = []
        self.cursor: int = 0
        self.is_paused: bool = False

    def build_queue(self, tasks: List[Task]):
        self.queue = []
        self.cursor = 0
        if not tasks:
            return
            
        temp_list = []
        for task in tasks:
            # 权重配置：高优 2x，中低 1x
            weight = 2 if task.priority == "high" else 1
            for _ in range(weight):
                temp_list.append(task)
                
        # 穿插打乱算法：将高优任务与中低优任务隔开，防止同类连续霸屏
        high_tasks = [t for t in temp_list if t.priority == "high"]
        other_tasks = [t for t in temp_list if t.priority != "high"]
        
        random.shuffle(high_tasks)
        random.shuffle(other_tasks)
        
        while high_tasks or other_tasks:
            if high_tasks:
                self.queue.append(high_tasks.pop(0))
            if other_tasks:
                self.queue.append(other_tasks.pop(0))

    def get_next(self) -> Optional[Task]:
        """获取下一个任务，若队列为空或被暂停（如番茄钟状态），则返回 None"""
        if self.is_paused or not self.queue:
            return None
        task = self.queue[self.cursor % len(self.queue)]
        self.cursor += 1
        return task
        
    def get_current(self) -> Optional[Task]:
        """获取当前正在展示的任务"""
        if self.is_paused or not self.queue:
            return None
        # 因为 get_next 已经让 cursor 步进了，所以当前显示的实际上是 cursor - 1
        return self.queue[(self.cursor - 1) % len(self.queue)]
        
    def pause(self):
        """挂起轮播，进入专注模式"""
        self.is_paused = True
        
    def resume(self):
        """恢复轮播"""
        self.is_paused = False
