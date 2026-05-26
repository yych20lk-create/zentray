# GTD 极客看板 (GTD Ticker v3.5)

> 本项目已全面升维至 **跨平台架构 (Windows/macOS/Linux)**，脱胎换骨为一款现代化的极致效率工具。针对 Linux 桌面环境进行了独创的顶栏原生文字级融合。

## ✨ v3.5 全新特性

- **顶栏状态栏融合模式 (GNOME Natively)**：Linux 下引入 **`双进程原生桥接 (Native GTK Bridge)`**，直接绕过 Qt 托盘 1:1 比例限制，在系统状态栏以文字形式直接呈现当前待办，并根据任务标题长度自适应文本框宽度。
- **跨平台智能降级**：在 Windows / macOS 系统或不兼容 AppIndicator 的 Linux 桌面下，智能回退为原生 `QSystemTrayIcon`，不阻塞系统事件循环。
- **极客下拉菜单交互**：
  - **🔄 状态更新**：子菜单支持「✅ 完成」或「❌ 废弃」当前任务。
  - **📝 编辑查看**：点击后直接呼出模态框，支持对当前任务的标题、分类、优先级、死线、详情、附件进行查看与二次编辑。
  - **📋 任务列表**：子菜单展示当前所有未完成的任务，带当前指示符，支持点击一键切换至该任务。
  - **常规选项**：包含「➕ 新建任务」、「🍅 专注 25 分钟」（自动显示倒计时）及「❌ 退出程序」。
- **一键式部署与运行**：
  - **Linux / macOS**: 提供 `run.sh` 脚本，自动初始化 venv 虚拟环境、自动检测并补齐 Python 依赖，一键快捷无感启动。
  - **Windows**: 提供 `run.bat` 批处理文件，双击即用。
- **现代化架构**：全面使用 `PySide6` 重构，支持暗黑模式 QSS 注入、无边框渲染、圆角阴影 UI。
- **多线程防崩溃护城河**：采用 Qt 原生的 `QThread` 配合 `Signal/Slot` 机制处理一切后台任务（包含大模型请求、死线扫描等），UI 线程极致流畅，0 卡顿。
- **AI 毒舌复盘**：集成每日 23:30 自动异步执行 of AI 复盘服务，利用带有“毒舌+鼓励”性格的系统 Prompt，生成总结后调用 WxPusher 报警推送至你的手机。

## 🛠️ 环境要求与安装

### 🚀 快速启动（推荐）

直接运行包装脚本，会自动安装 Python 依赖（从 `requirements.txt` 读取）并启动程序：

```bash
# Linux / macOS
chmod +x run.sh
./run.sh

# Windows
双击运行 run.bat
```

### 📦 手动安装模式

```bash
# 1. 确保 Python 3.10+
python3 --version

# 2. 安装所有重构后的底层依赖
pip install -r requirements.txt

# 3. 运行主程序
python gtd_ticker/main.py
```

## ⚙️ 核心环境变量

打开 `gtd_ticker/config.py`，你可以在此调整你的极客参数：
- `AI_API_BASE_URL` / `AI_API_KEY`：配置你的大模型地址以激活“毒舌教练”。
- `WXPUSHER_APP_TOKEN` / `WXPUSHER_UID`：配置手机端强提醒推送令牌。
- `POMODORO_MINUTES`：全局沉浸状态倒计时长度（默认 25 分钟）。

## 📁 架构说明
本仓库严格遵循 Clean Architecture 原则。业务逻辑、底层持久化与视图渲染完全解耦。
- `gtd_ticker/core/`: 调度器 (`scheduler.py`)、数据层映射 (`storage.py`) 及任务模型。
- `gtd_ticker/ui/`: 原生跨平台托盘菜单实现 (`tray.py` / `linux_tray_bridge.py`) 及编辑器/覆盖层弹框。
- `gtd_ticker/workers/`: 超时监控与 AI 异步服务。
