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
    created_at: str = field(default_factory=lambda: datetime.datetime.now().isoformat())

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

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})
