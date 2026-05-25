#!/usr/bin/env python3
import os
import json
import uuid
import datetime
import random
import shutil
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('AyatanaAppIndicator3', '0.1')
from gi.repository import Gtk, GLib, AyatanaAppIndicator3 as AppIndicator3

APP_DIR = os.path.expanduser('~/.local/share/my_todo_ticker')
ARCHIVE_DIR = os.path.join(APP_DIR, 'archive')
ACTIVE_TASKS_FILE = os.path.join(APP_DIR, 'active_tasks.json')
PERIODIC_TEMPLATES_FILE = os.path.join(APP_DIR, 'periodic_templates.json')

EMOJIS = {
    "high": "🔴",
    "medium": "🟡",
    "low": "🟢"
}

class WeightedTaskScheduler:
    def __init__(self, tasks):
        self.tasks = tasks
        self.queue = []
        self.cursor = 0
        self._build_queue()

    def update_tasks(self, tasks):
        self.tasks = tasks
        self._build_queue()

    def _build_queue(self):
        self.queue = []
        self.cursor = 0
        if not self.tasks:
            return
            
        temp_list = []
        for task in self.tasks:
            weight = 2 if task.get("priority") == "high" else 1
            for _ in range(weight):
                temp_list.append(task)
                
        # Interleave logic to avoid same high priority tasks continuously
        high_tasks = [t for t in temp_list if t.get("priority") == "high"]
        other_tasks = [t for t in temp_list if t.get("priority") != "high"]
        
        random.shuffle(high_tasks)
        random.shuffle(other_tasks)
        
        while high_tasks or other_tasks:
            if high_tasks:
                self.queue.append(high_tasks.pop(0))
            if other_tasks:
                self.queue.append(other_tasks.pop(0))

    def get_next_task(self):
        if not self.queue:
            return None
        task = self.queue[self.cursor % len(self.queue)]
        self.cursor += 1
        return task

class TodoTickerApp:
    def __init__(self):
        self._ensure_directories()
        self.tasks = self._load_json(ACTIVE_TASKS_FILE)
        self.periodic_templates = self._load_json(PERIODIC_TEMPLATES_FILE)
        
        self.scheduler = WeightedTaskScheduler(self.tasks)
        self.current_task = None

        self.indicator = AppIndicator3.Indicator.new(
            "my-todo-ticker",
            "emblem-documents-symbolic",
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        
        self.menu = Gtk.Menu()
        
        # Run daily maintenance (overdue check + periodic dispatch) before building menu
        self._daily_maintenance()
        
        self._build_menu()
        self.indicator.set_menu(self.menu)

        self._update_display()

        # Update display every 30 seconds
        GLib.timeout_add_seconds(30, self._update_display_timer)
        # Check for file changes every 5 seconds
        GLib.timeout_add_seconds(5, self._periodic_reload)
        # Daily maintenance check every 1 hour to handle day-crossing
        GLib.timeout_add_seconds(3600, self._daily_maintenance_timer)

    def _ensure_directories(self):
        os.makedirs(ARCHIVE_DIR, exist_ok=True)

    def _load_json(self, filepath):
        if not os.path.exists(filepath):
            return []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            backup_file = filepath + '.bak'
            shutil.copy(filepath, backup_file)
            return []
        except FileNotFoundError:
            return []

    def _save_json(self, data, filepath):
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _save_tasks(self):
        self._save_json(self.tasks, ACTIVE_TASKS_FILE)

    def _save_periodic_templates(self):
        self._save_json(self.periodic_templates, PERIODIC_TEMPLATES_FILE)

    def _daily_maintenance_timer(self):
        self._daily_maintenance()
        return True

    def _daily_maintenance(self):
        today = datetime.date.today()
        today_str = today.strftime("%Y-%m-%d")
        
        changed_tasks = False
        changed_templates = False
        
        # 1. Overdue penalty check
        for task in self.tasks:
            deadline_str = task.get("deadline")
            if deadline_str:
                try:
                    deadline_date = datetime.datetime.strptime(deadline_str, "%Y-%m-%d").date()
                    if today > deadline_date:
                        pri = task.get("priority", "low")
                        if pri == "low": new_pri = "medium"
                        elif pri == "medium": new_pri = "high"
                        else: new_pri = "high"
                        
                        task["priority"] = new_pri
                        task["deadline"] = (deadline_date + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                        task["overdue_penalty_date"] = today_str
                        changed_tasks = True
                except ValueError:
                    pass

        # 2. Periodic dispatch
        for tmpl in self.periodic_templates:
            periodicity = tmpl.get("periodicity", "daily")
            
            if periodicity == "daily":
                prefix = today.strftime("%y%m%d")
            elif periodicity == "weekly":
                iso_year, iso_week, _ = today.isocalendar()
                prefix = f"{str(iso_year)[2:]}第{iso_week}周"
            elif periodicity == "monthly":
                prefix = today.strftime("%y%m")
            else:
                prefix = today.strftime("%y%m%d")
                
            if tmpl.get("last_generated_period") != prefix:
                new_title = f"【{prefix}】{tmpl.get('base_title', '')}"
                new_task = {
                    "id": str(uuid.uuid4()),
                    "title": new_title,
                    "category": tmpl.get("category", "工作"),
                    "details": tmpl.get("details", ""),
                    "priority": tmpl.get("priority", "medium"),
                    "deadline": "",
                    "attachments": [],
                    "task_type": "periodic_instance",
                    "template_id": tmpl.get("template_id"),
                    "created_at": datetime.datetime.now().isoformat()
                }
                self.tasks.append(new_task)
                tmpl["last_generated_period"] = prefix
                changed_tasks = True
                changed_templates = True
                
        if changed_tasks:
            self._save_tasks()
            self.scheduler.update_tasks(self.tasks)
            self._build_menu()
            self._update_display()
        if changed_templates:
            self._save_periodic_templates()

    def _archive_task(self, task, status):
        date_str = datetime.datetime.now().strftime('%Y-%m-%d')
        archive_file = os.path.join(ARCHIVE_DIR, f"{date_str}.log")
        
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        priority = task.get("priority", "low").upper()
        title = task.get("title", "")
        category = task.get("category", "工作")
        attachments = task.get("attachments", [])
        att_count = len(attachments)
        details = task.get("details", "").replace("\n", " ").replace("\r", " ")
        
        log_line = f"[{timestamp}] [状态: {status}] [分类: {category}] [{priority}] {title} - {details} (附件数: {att_count})\n"
        
        with open(archive_file, 'a', encoding='utf-8') as f:
            f.write(log_line)

    def _build_menu(self):
        for item in self.menu.get_children():
            self.menu.remove(item)

        self.item_new = Gtk.MenuItem(label="➕ 新建任务")
        self.item_new.connect('activate', self.on_new_task)
        self.menu.append(self.item_new)

        self.item_done = Gtk.MenuItem(label="✅ 完成并归档 (当前展示任务)")
        self.item_done.connect('activate', self.on_mark_done)
        self.menu.append(self.item_done)

        self.item_edit = Gtk.MenuItem(label="📝 修改详情 (当前展示任务)")
        self.item_edit.connect('activate', self.on_edit_task)
        self.menu.append(self.item_edit)

        self.item_discard = Gtk.MenuItem(label="🗑️ 直接废弃 (当前展示任务)")
        self.item_discard.connect('activate', self.on_discard)
        self.menu.append(self.item_discard)

        self.menu.append(Gtk.SeparatorMenuItem())
        
        self.all_tasks_item = Gtk.MenuItem(label="📋 所有待办任务")
        self.all_tasks_submenu = Gtk.Menu()
        self.all_tasks_item.set_submenu(self.all_tasks_submenu)
        self.menu.append(self.all_tasks_item)

        if not self.tasks:
            empty_item = Gtk.MenuItem(label="🎉 暂无待办事项")
            empty_item.set_sensitive(False)
            self.all_tasks_submenu.append(empty_item)
        else:
            priority_order = {"high": 0, "medium": 1, "low": 2}
            sorted_tasks = sorted(self.tasks, key=lambda t: priority_order.get(t.get("priority", "low"), 2))
            for task in sorted_tasks:
                emoji = EMOJIS.get(task.get("priority", "low"), "🟢")
                title = task.get("title", "")
                if len(title) > 20:
                    title = title[:20] + "..."
                task_item = Gtk.MenuItem(label=f"{emoji} {title}")
                task_item.connect('activate', lambda widget, t=task: self.on_edit_specific_task(widget, t))
                self.all_tasks_submenu.append(task_item)

        self.menu.append(Gtk.SeparatorMenuItem())

        self.item_quit = Gtk.MenuItem(label="❌ 退出程序")
        self.item_quit.connect('activate', self.on_quit)
        self.menu.append(self.item_quit)

        self.menu.show_all()
        self._update_menu_sensitive_state()

    def _update_menu_sensitive_state(self):
        has_task = self.current_task is not None
        if hasattr(self, 'item_done'):
            self.item_done.set_sensitive(has_task)
            self.item_edit.set_sensitive(has_task)
            self.item_discard.set_sensitive(has_task)

    def _update_display_timer(self):
        self._update_display()
        return True

    def _update_display(self):
        self.current_task = self.scheduler.get_next_task()
        if not self.current_task:
            self.indicator.set_label("🎉 暂无待办事项。", "")
        else:
            title = self.current_task.get("title", "")
            if len(title) > 15:
                title = title[:15] + "..."
            emoji = EMOJIS.get(self.current_task.get("priority", "low"), "🟢")
            self.indicator.set_label(f" {emoji} {title}", "")
        
        self._update_menu_sensitive_state()

    def _periodic_reload(self):
        try:
            if os.path.exists(ACTIVE_TASKS_FILE):
                with open(ACTIVE_TASKS_FILE, 'r', encoding='utf-8') as f:
                    new_tasks = json.load(f)
                if json.dumps(new_tasks, sort_keys=True) != json.dumps(self.tasks, sort_keys=True):
                    self.tasks = new_tasks
                    self.scheduler.update_tasks(self.tasks)
                    self._build_menu()
                    self._update_display()
        except Exception:
            pass
        return True

    def on_new_task(self, widget):
        dialog = TaskDialog()
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            data = dialog.get_data()
            if data['title']:
                if data['task_type'] == 'periodic':
                    new_tmpl = {
                        "template_id": str(uuid.uuid4()),
                        "base_title": data['title'],
                        "category": data['category'],
                        "details": data['details'],
                        "priority": data['priority'],
                        "periodicity": data['periodicity'],
                        "created_at": datetime.datetime.now().isoformat()
                    }
                    self.periodic_templates.append(new_tmpl)
                    self._save_periodic_templates()
                    self._daily_maintenance() # trigger immediate generation
                else:
                    new_task = {
                        "id": str(uuid.uuid4()),
                        "title": data['title'],
                        "category": data['category'],
                        "details": data['details'],
                        "priority": data['priority'],
                        "deadline": data['deadline'],
                        "attachments": data['attachments'],
                        "task_type": "one-time",
                        "created_at": datetime.datetime.now().isoformat()
                    }
                    self.tasks.append(new_task)
                    self._save_tasks()
                    self.scheduler.update_tasks(self.tasks)
                    self._build_menu()
                    self._update_display()
        dialog.destroy()

    def on_edit_task(self, widget):
        if not self.current_task: return
        self.on_edit_specific_task(widget, self.current_task)

    def on_edit_specific_task(self, widget, task):
        dialog = TaskDialog(task)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            data = dialog.get_data()
            if data['title']:
                for t in self.tasks:
                    if t['id'] == task['id']:
                        t['title'] = data['title']
                        t['category'] = data['category']
                        t['details'] = data['details']
                        t['priority'] = data['priority']
                        t['deadline'] = data['deadline']
                        t['attachments'] = data['attachments']
                        break
                self._save_tasks()
                self.scheduler.update_tasks(self.tasks)
                self._build_menu()
                self._update_display()
        dialog.destroy()

    def on_mark_done(self, widget):
        if not self.current_task: return
        self._archive_task(self.current_task, "DONE")
        self.tasks = [t for t in self.tasks if t['id'] != self.current_task['id']]
        self._save_tasks()
        self.scheduler.update_tasks(self.tasks)
        self._build_menu()
        self._update_display()

    def on_discard(self, widget):
        if not self.current_task: return
        self._archive_task(self.current_task, "DISCARD")
        self.tasks = [t for t in self.tasks if t['id'] != self.current_task['id']]
        self._save_tasks()
        self.scheduler.update_tasks(self.tasks)
        self._build_menu()
        self._update_display()

    def on_quit(self, widget):
        Gtk.main_quit()

class TaskDialog(Gtk.Dialog):
    def __init__(self, task=None):
        title_str = "修改任务" if task else "新建任务"
        super().__init__(title=title_str, flags=Gtk.DialogFlags.MODAL)
        self.set_default_size(500, 450)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_border_width(10)
        
        self.add_buttons(
            "取消", Gtk.ResponseType.CANCEL,
            "保存", Gtk.ResponseType.OK
        )
        
        self.is_editing = task is not None
        self.attachments = list(task.get("attachments", [])) if task else []
        
        box = self.get_content_area()
        box.set_orientation(Gtk.Orientation.VERTICAL)
        box.set_spacing(10)

        # 1. Task Type (Only show if new)
        if not self.is_editing:
            type_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            self.rb_one_time = Gtk.RadioButton.new_with_label_from_widget(None, "一次性任务")
            self.rb_periodic = Gtk.RadioButton.new_with_label_from_widget(self.rb_one_time, "周期任务")
            self.rb_periodic.connect("toggled", self.on_type_toggled)
            type_box.pack_start(Gtk.Label(label="任务类型:"), False, False, 0)
            type_box.pack_start(self.rb_one_time, False, False, 0)
            type_box.pack_start(self.rb_periodic, False, False, 0)
            box.pack_start(type_box, False, False, 0)
            
            self.period_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            self.period_combo = Gtk.ComboBoxText()
            self.period_combo.append("daily", "每日任务")
            self.period_combo.append("weekly", "每周任务")
            self.period_combo.append("monthly", "每月任务")
            self.period_combo.set_active_id("daily")
            self.period_box.pack_start(Gtk.Label(label="周期频率:"), False, False, 0)
            self.period_box.pack_start(self.period_combo, True, True, 0)
            box.pack_start(self.period_box, False, False, 0)
            # hide initially
            self.period_box.set_no_show_all(True)
            self.period_box.hide()

        # 2. Title
        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        title_label = Gtk.Label(label="标题:")
        self.title_entry = Gtk.Entry()
        self.title_entry.set_max_length(50)
        title_box.pack_start(title_label, False, False, 0)
        title_box.pack_start(self.title_entry, True, True, 0)
        box.pack_start(title_box, False, False, 0)
        
        # 3. Category & Priority
        cp_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        cp_box.pack_start(Gtk.Label(label="分类:"), False, False, 0)
        self.category_combo = Gtk.ComboBoxText()
        self.category_combo.append("工作", "工作")
        self.category_combo.append("生活", "生活")
        self.category_combo.append("学习", "学习")
        self.category_combo.set_active_id("工作")
        cp_box.pack_start(self.category_combo, True, True, 0)
        
        cp_box.pack_start(Gtk.Label(label="优先级:"), False, False, 0)
        self.priority_combo = Gtk.ComboBoxText()
        self.priority_combo.append("high", "🔴 高优先级")
        self.priority_combo.append("medium", "🟡 中优先级")
        self.priority_combo.append("low", "🟢 低优先级")
        cp_box.pack_start(self.priority_combo, True, True, 0)
        box.pack_start(cp_box, False, False, 0)

        # 4. Deadline
        deadline_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        deadline_box.pack_start(Gtk.Label(label="截止日期:"), False, False, 0)
        self.deadline_entry = Gtk.Entry()
        self.deadline_entry.set_placeholder_text("YYYY-MM-DD (选填)")
        deadline_box.pack_start(self.deadline_entry, True, True, 0)
        box.pack_start(deadline_box, False, False, 0)

        # 5. Details
        details_label = Gtk.Label(label="详情:")
        details_label.set_valign(Gtk.Align.START)
        details_label.set_halign(Gtk.Align.START)
        box.pack_start(details_label, False, False, 0)
        
        self.details_textview = Gtk.TextView()
        self.details_textview.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.add(self.details_textview)
        box.pack_start(scrolled_window, True, True, 0)
        
        # 6. Attachments
        attach_label_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        attach_label_box.pack_start(Gtk.Label(label="附件管理:"), False, False, 0)
        add_attach_btn = Gtk.Button(label="➕ 添加附件")
        add_attach_btn.connect("clicked", self.on_add_attachment)
        attach_label_box.pack_start(add_attach_btn, False, False, 0)
        box.pack_start(attach_label_box, False, False, 0)
        
        self.attach_list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box.pack_start(self.attach_list_box, False, False, 0)

        # Populate if editing
        if task:
            self.title_entry.set_text(task.get("title", ""))
            self.category_combo.set_active_id(task.get("category", "工作"))
            self.priority_combo.set_active_id(task.get("priority", "medium"))
            self.deadline_entry.set_text(task.get("deadline", ""))
            self.details_textview.get_buffer().set_text(task.get("details", ""))
        else:
            self.priority_combo.set_active_id("medium")

        self.refresh_attachments_ui()
        self.show_all()
        if not self.is_editing:
            self.period_box.hide()

    def on_type_toggled(self, widget):
        if self.rb_periodic.get_active():
            self.period_box.show()
            self.deadline_entry.set_sensitive(False)
            self.deadline_entry.set_text("")
        else:
            self.period_box.hide()
            self.deadline_entry.set_sensitive(True)

    def on_add_attachment(self, widget):
        dialog = Gtk.FileChooserDialog(
            title="选择附件",
            parent=self,
            action=Gtk.FileChooserAction.OPEN,
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK
        )
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filepath = dialog.get_filename()
            if filepath not in self.attachments:
                self.attachments.append(filepath)
                self.refresh_attachments_ui()
        dialog.destroy()
        
    def on_remove_attachment(self, widget, filepath):
        if filepath in self.attachments:
            self.attachments.remove(filepath)
            self.refresh_attachments_ui()

    def refresh_attachments_ui(self):
        for child in self.attach_list_box.get_children():
            self.attach_list_box.remove(child)
            
        for path in self.attachments:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
            lbl = Gtk.Label(label=os.path.basename(path))
            lbl.set_halign(Gtk.Align.START)
            btn = Gtk.Button(label="❌")
            btn.set_relief(Gtk.ReliefStyle.NONE)
            btn.connect("clicked", self.on_remove_attachment, path)
            row.pack_start(lbl, True, True, 0)
            row.pack_start(btn, False, False, 0)
            self.attach_list_box.pack_start(row, False, False, 0)
            
        self.attach_list_box.show_all()

    def get_data(self):
        title = self.title_entry.get_text().strip()
        
        buffer = self.details_textview.get_buffer()
        start, end = buffer.get_bounds()
        details = buffer.get_text(start, end, True).strip()
        
        priority = self.priority_combo.get_active_id() or "medium"
        category = self.category_combo.get_active_id() or "工作"
        deadline = self.deadline_entry.get_text().strip()
        
        task_type = "one-time"
        periodicity = "daily"
        if not self.is_editing and self.rb_periodic.get_active():
            task_type = "periodic"
            periodicity = self.period_combo.get_active_id()
            
        return {
            "title": title,
            "details": details,
            "priority": priority,
            "category": category,
            "deadline": deadline,
            "attachments": self.attachments,
            "task_type": task_type,
            "periodicity": periodicity
        }

if __name__ == "__main__":
    app = TodoTickerApp()
    Gtk.main()
