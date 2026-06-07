import json
import shutil
import datetime
from pathlib import Path
from typing import List

from zentray.config import ACTIVE_TASKS_FILE, PERIODIC_TEMPLATES_FILE, ARCHIVE_DIR
from zentray.core.models import Task, PeriodicTemplate

class Storage:
    """
    负责底层 JSON 数据的读写与安全备份 (分离活动数据和归档数据)。
    """
    @staticmethod
    def _load_json(filepath: Path, model_cls):
        if not filepath.exists():
            return []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data_list = json.load(f)
                return [model_cls.from_dict(d) for d in data_list]
        except json.JSONDecodeError:
            # 自动容错：若 JSON 损坏则备份，返回空列表防止应用崩溃
            backup_file = filepath.with_suffix('.json.bak')
            shutil.copy(filepath, backup_file)
            return []
        except Exception:
            return []

    @staticmethod
    def _save_json(filepath: Path, objects: List):
        data_list = [obj.to_dict() for obj in objects]
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data_list, f, indent=2, ensure_ascii=False)

    @classmethod
    def load_tasks(cls) -> List[Task]:
        return cls._load_json(ACTIVE_TASKS_FILE, Task)

    @classmethod
    def save_tasks(cls, tasks: List[Task]):
        cls._save_json(ACTIVE_TASKS_FILE, tasks)

    @classmethod
    def load_periodic_templates(cls) -> List[PeriodicTemplate]:
        return cls._load_json(PERIODIC_TEMPLATES_FILE, PeriodicTemplate)

    @classmethod
    def save_periodic_templates(cls, templates: List[PeriodicTemplate]):
        cls._save_json(PERIODIC_TEMPLATES_FILE, templates)

    @classmethod
    def archive_task(cls, task: Task, status: str):
        """将任务以纯文本单行的形式持久化到当日归档文件中"""
        date_str = datetime.datetime.now().strftime('%Y-%m-%d')
        archive_file = ARCHIVE_DIR / f"{date_str}.log"
        
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        priority = task.priority.upper()
        title = task.title
        category = task.category
        att_count = len(task.attachments)
        details = task.details.replace("\n", " ").replace("\r", " ")
        
        log_line = f"[{timestamp}] [状态: {status}] [分类: {category}] [{priority}] {title} - {details} (附件数: {att_count})\n"
        
        with open(archive_file, 'a', encoding='utf-8') as f:
            f.write(log_line)
