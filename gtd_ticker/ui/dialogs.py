import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QTextEdit, QComboBox, QPushButton, QRadioButton, QWidget, QFileDialog
)
from PySide6.QtCore import Qt
from gtd_ticker.core.models import Task, PeriodicTemplate

class TaskDialog(QDialog):
    def __init__(self, parent=None, task=None):
        super().__init__(parent)
        self.task = task
        self.is_editing = task is not None
        self.attachments = list(task.attachments) if isinstance(task, Task) else []
        
        # 使用 Qt.Window 配合自定义边框，或者仅用基本 Dialog，通过 QSS 实现现代化
        self.setWindowTitle("修改任务" if self.is_editing else "新建任务")
        self.resize(480, 520)
        
        self.init_ui()
        self.populate_data()
        self.load_styles()

    def load_styles(self):
        qss_path = os.path.join(os.path.dirname(__file__), 'styles', 'main.qss')
        if os.path.exists(qss_path):
            with open(qss_path, 'r', encoding='utf-8') as f:
                self.setStyleSheet(f.read())

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 1. 任务类型 (仅新建时显示)
        self.type_widget = QWidget()
        type_layout = QHBoxLayout(self.type_widget)
        type_layout.setContentsMargins(0, 0, 0, 0)
        type_layout.addWidget(QLabel("任务模式:"))
        
        self.rb_one_time = QRadioButton("一次性任务")
        self.rb_periodic = QRadioButton("周期任务")
        self.rb_one_time.setChecked(True)
        self.rb_periodic.toggled.connect(self.on_type_toggled)
        
        type_layout.addWidget(self.rb_one_time)
        type_layout.addWidget(self.rb_periodic)
        
        self.period_combo = QComboBox()
        self.period_combo.addItems(["daily", "weekly", "monthly"])
        self.period_combo.hide()
        type_layout.addWidget(self.period_combo)
        type_layout.addStretch()
        
        if not self.is_editing:
            layout.addWidget(self.type_widget)
            
        # 2. 标题
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("标题:"))
        self.title_entry = QLineEdit()
        self.title_entry.setPlaceholderText("用一句话描述待办...")
        title_layout.addWidget(self.title_entry)
        layout.addLayout(title_layout)
        
        # 3. 分类与优先级
        cp_layout = QHBoxLayout()
        cp_layout.addWidget(QLabel("分类:"))
        self.category_combo = QComboBox()
        self.category_combo.addItems(["工作", "生活", "学习"])
        cp_layout.addWidget(self.category_combo)
        
        cp_layout.addWidget(QLabel("  优先级:"))
        self.priority_combo = QComboBox()
        self.priority_combo.addItem("🔴 紧急高危", "high")
        self.priority_combo.addItem("🟡 中等优先级", "medium")
        self.priority_combo.addItem("🟢 低优先级", "low")
        cp_layout.addWidget(self.priority_combo)
        layout.addLayout(cp_layout)
        
        # 4. 截止日期
        dl_layout = QHBoxLayout()
        dl_layout.addWidget(QLabel("截止日期:"))
        self.deadline_entry = QLineEdit()
        self.deadline_entry.setPlaceholderText("例如: 2026-05-25 (选填)")
        dl_layout.addWidget(self.deadline_entry)
        layout.addLayout(dl_layout)
        
        # 5. 详情
        layout.addWidget(QLabel("任务详情 (选填):"))
        self.details_edit = QTextEdit()
        layout.addWidget(self.details_edit)
        
        # 6. 附件
        att_layout = QHBoxLayout()
        att_layout.addWidget(QLabel("附件清单:"))
        btn_add_att = QPushButton("➕ 选取文件")
        btn_add_att.clicked.connect(self.add_attachment)
        att_layout.addWidget(btn_add_att)
        att_layout.addStretch()
        layout.addLayout(att_layout)
        
        self.att_list_label = QLabel("暂未附加任何文件")
        self.att_list_label.setStyleSheet("color: #888;")
        layout.addWidget(self.att_list_label)
        
        # 7. 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_cancel = QPushButton("取消")
        btn_cancel.setObjectName("btnWarning") # 对应 QSS 里的灰边/红悬停样式
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("💾 保存任务")
        btn_save.clicked.connect(self.accept)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)

    def on_type_toggled(self):
        if self.rb_periodic.isChecked():
            self.period_combo.show()
            self.deadline_entry.setEnabled(False)
            self.deadline_entry.clear()
            self.deadline_entry.setPlaceholderText("周期任务不支持单独截期")
        else:
            self.period_combo.hide()
            self.deadline_entry.setEnabled(True)
            self.deadline_entry.setPlaceholderText("例如: 2026-05-25 (选填)")

    def add_attachment(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择你要附加的文件")
        if file_path and file_path not in self.attachments:
            self.attachments.append(file_path)
            self.update_att_label()

    def update_att_label(self):
        if not self.attachments:
            self.att_list_label.setText("暂未附加任何文件")
        else:
            names = [os.path.basename(p) for p in self.attachments]
            self.att_list_label.setText("📦 " + ", ".join(names))

    def populate_data(self):
        if not self.task:
            return
        if isinstance(self.task, Task):
            self.title_entry.setText(self.task.title)
            self.category_combo.setCurrentText(self.task.category)
            idx = self.priority_combo.findData(self.task.priority)
            if idx >= 0: self.priority_combo.setCurrentIndex(idx)
            self.deadline_entry.setText(self.task.deadline or "")
            self.details_edit.setPlainText(self.task.details)
            self.update_att_label()
        elif isinstance(self.task, PeriodicTemplate):
            self.title_entry.setText(self.task.base_title)
            self.category_combo.setCurrentText(self.task.category)
            idx = self.priority_combo.findData(self.task.priority)
            if idx >= 0: self.priority_combo.setCurrentIndex(idx)
            self.details_edit.setPlainText(self.task.details)
            self.deadline_entry.setEnabled(False)
            self.deadline_entry.setPlaceholderText("周期任务模板不支持单独截期")
            self.att_list_label.setText("周期任务模板不支持附件")

    def get_data(self) -> dict:
        is_periodic = self.rb_periodic.isChecked() if not self.is_editing else False
        return {
            "title": self.title_entry.text().strip(),
            "category": self.category_combo.currentText(),
            "priority": self.priority_combo.currentData(),
            "deadline": self.deadline_entry.text().strip(),
            "details": self.details_edit.toPlainText().strip(),
            "attachments": self.attachments,
            "task_type": "periodic" if is_periodic else "one-time",
            "periodicity": self.period_combo.currentText()
        }
