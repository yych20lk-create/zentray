from dataclasses import dataclass, field, asdict
from typing import List, Optional
import datetime
import uuid

@dataclass
class Task:
    title: str
    category: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    details: str = ""
    priority: str = "medium"  # high, medium, low
    deadline: Optional[str] = None # YYYY-MM-DD
    attachments: List[str] = field(default_factory=list)
    task_type: str = "one-time" # one-time, periodic_instance
    template_id: Optional[str] = None
    overdue_penalty_date: Optional[str] = None
    progress: int = 0  # 0 to 100
    progress_logs: List[dict] = field(default_factory=list)  # list of {"time": str, "percent": int, "note": str}
    created_at: str = field(default_factory=lambda: datetime.datetime.now().isoformat())

    def __post_init__(self):
        if self.attachments is None:
            self.attachments = []
        if self.details is None:
            self.details = ""
        if self.priority is None:
            self.priority = "medium"
        if not self.title:
            self.title = "Untitled"
        if not self.category:
            self.category = "工作"
        if getattr(self, 'progress', None) is None:
            self.progress = 0
        if getattr(self, 'progress_logs', None) is None:
            self.progress_logs = []

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        # 兼容性处理：仅提取属于该数据类的字段
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})

@dataclass
class PeriodicTemplate:
    base_title: str
    category: str
    periodicity: str # daily, weekly, monthly
    template_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    details: str = ""
    priority: str = "medium"
    last_generated_period: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.datetime.now().isoformat())

    def __post_init__(self):
        if self.details is None:
            self.details = ""
        if self.priority is None:
            self.priority = "medium"
        if not self.base_title:
            self.base_title = "Untitled"
        if not self.category:
            self.category = "工作"

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})
