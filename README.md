# GTD 极客看板 (GTD Ticker v3.6)

> 本项目已全面升维至 **跨平台架构 (Windows/macOS/Linux)**，脱胎换骨为一款现代化的极致效率工具。针对 Linux 桌面环境进行了独创的顶栏原生文字级融合，并集成了独立的本地公共通知发送服务。

## ✨ v3.6 全新特性

- **模块化本地通知服务 (Notification Service)**：独立拆分出通知发送模块，作为一个通用本地微服务（运行在 `http://127.0.0.1:18330`）运行。极客看板或其他本地脚本（如周报生成、报警等）均可通过调用统一的本地 API `/send` 向移动端推送消息。
- **多通道可配置发送 (Extensible Senders)**：通知服务内部实现了面向接口的通道管理，不仅支持 `WxPusher` 微信推送，还支持 `钉钉机器人 Webhook` 等多种发送通道，支持即时热插拔与多通道同步发送。
- **模版定制完全解耦**：通知服务作为“无状态通道”，本身不耦合任何日报或报警的文本格式，具体的排版与 AI 总结模版完全由调用方（如极客看板的 `NightlyJob`）自由定制。
- **顶栏状态栏融合模式 (GNOME Natively)**：Linux 下引入 **`双进程原生桥接 (Native GTK Bridge)`**，直接绕过 Qt 托盘 1:1 比例限制，在系统状态栏以文字形式直接呈现当前待办，并根据任务标题长度自适应文本框宽度。
- **极客下拉菜单交互**：
  - **🔄 状态更新**：子菜单支持「✅ 完成」或「❌ 废弃」当前任务。
  - **📝 编辑查看**：点击后直接呼出模态框，支持对当前任务进行查看与二次编辑。
  - **📋 任务列表**：子菜单展示当前所有未完成的任务，支持点击一键切换。
- **一键式部署与运行**：
  - **Linux / macOS**: 提供 `run.sh` 脚本，自动初始化 venv，一键启动本地通知服务与 GTD 看板主程序。
  - **Windows**: 提供 `run.bat` 批处理文件，双击一键拉起。

## 🛠️ 环境要求与安装

### 🚀 快速启动（推荐）

直接运行包装脚本，会自动安装 Python 依赖（从 `requirements.txt` 读取）并启动程序（包括本地通知服务）：

```bash
# Linux / macOS
chmod +x run.sh
./run.sh

# Windows
双击运行 run.bat
```

### 📦 手动安装与独立运行通知服务

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动本地通知服务
python notification_service/main.py

# 3. 启动看板主程序
python gtd_ticker/main.py
```

## ⚙️ 核心配置文件与参数

### 1. 通讯通道配置：`notification_service/config.json`
在这里配置接收端凭证和激活的推送通道：
- `PORT`: 本地服务监听端口（默认 `18330`）。
- `ACTIVE_SENDERS`: 激活的通道列表（例如 `["wxpusher"]` 或 `["wxpusher", "dingtalk"]`）。
- `WXPUSHER`: 包含 `WXPUSHER_APP_TOKEN` 和 `WXPUSHER_UID`。
- `DINGTALK`: 包含 `DINGTALK_WEBHOOK_URL`。

### 2. 极客看板配置：`gtd_ticker/config.py`
调整番茄钟时间或大模型锐评教练参数：
- `AI_API_BASE_URL` / `AI_API_KEY`：配置大模型地址以激活“毒舌教练”。
- `POMODORO_MINUTES`：番茄钟时长（默认 25 分钟）。

## 📡 本地通知 API 接口

任何第三方应用或脚本都可以直接向本地服务投递消息：
- **请求方法**: `POST`
- **请求地址**: `http://127.0.0.1:18330/send`
- **请求体 (JSON)**:
```json
{
  "title": "消息标题",
  "content": "这里是支持 **Markdown** 的正文内容"
}
```

## 📁 架构说明
- `gtd_ticker/`: 看板核心逻辑与 PySide6 GUI 视图。
- `notification_service/`: 独立通知模块。
  - `senders/`: 通道发送器（WxPusher, DingTalk 等，均继承自 `BaseSender`）。
  - `main.py`: 本地 API 服务主入口。
  - `client.py`: 供外部 Python 脚本导入调用的客户端类 `NotificationClient`。
- `send_daily_summary.py`: 根目录下的一键手动发送日报脚本。
