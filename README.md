# GTD 极客看板 (GTD Ticker)

GTD 极客看板是一个为 Linux 桌面环境（推荐 Ubuntu 24.04 GNOME Wayland）打造的轻量级、优雅且常驻顶部托盘区的 GTD (Getting Things Done) 待办事项管理工具。

## ✨ 核心特性

- **托盘常驻与智能轮播**：任务悬浮于桌面托盘区，基于加权轮播调度器自动轮播提醒，拒绝遗忘。
- **动态分类与截止日期**：支持「生活、工作、学习」分类。搭载逾期自动惩罚机制，逾期未完成任务自动提高优先级并顺延。
- **周期任务自动派发**：支持一次性任务和周期任务（每日、每周、每月），底层引擎会在后台自动派发新周期的实例任务。
- **每日精细战报推送**：集成 WxPusher，每日自动总结完成的任务、废弃的任务和明日待办清册，并精准推送到微信，带有防折叠时间戳和独立逾期警告分区。
- **读写分离与数据安全**：分离活动任务 (`active_tasks.json`) 与历史归档日志 (`archive/`)，所有操作基于原生 GTK3 弹窗，严格确保跨日或异常崩溃不丢失数据。

## 🛠️ 环境依赖

- **操作系统**: Ubuntu 24.04 (GNOME 46) 等支持 `AppIndicator3` 的 Linux 桌面系统。
- **语言与组件库**: 
  - Python 3.x
  - `python3-gi` (PyGObject)
  - `gir1.2-gtk-3.0` (GTK3)
  - `gir1.2-ayatanaappindicator3-0.1`
  - `requests` (用于微信推送)

## 🚀 快速启动

1. 赋予执行权限：
```bash
chmod +x todo_ticker.py send_daily_summary.py
```

2. 运行主程序：
```bash
./todo_ticker.py &
```
> *建议：为了极致体验，可将其配置为 Ubuntu 的“开机自启动程序”。*

3. 每日战报配置：
打开 `send_daily_summary.py`，在顶部配置区填入你在 WxPusher 后台获取的 `APP_TOKEN` 与 `MY_UID`。你可以将其加入系统 `crontab` 实现每晚自动复盘。

## 📁 存储位置
本项目严格遵循 Linux 用户规范，不会污染代码仓库。运行时所有数据均存放在以下独立目录：
* `~/.local/share/my_todo_ticker/`

## 📄 需求说明
详见仓库中的 `桌面顶部托盘应用需求文档.md`。
