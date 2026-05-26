# GTD 极客看板 (GTD Ticker v3.0)

> 本项目已全面升维至 **跨平台架构 (Windows/macOS/Linux)**，脱胎换骨为一款现代化的极致效率工具。

## ✨ v3.0 全新特性

- **Qt6 现代化架构**：全面使用 `PySide6` 重构，支持暗黑模式 QSS 注入、无边框渲染、圆角阴影 UI。彻底告别上世纪粗糙的弹窗风格。
- **多线程防崩溃护城河**：采用 Qt 原生的 `QThread` 配合 `Signal/Slot` 机制处理一切后台任务（包含大模型请求、死线扫描等），UI 线程极致流畅，0 卡顿。
- **单例进程锁**：基于 `QLocalServer` 实现跨平台级别的防多开保护机制，安全回收崩溃连接。
- **标准数据规范**：重构存储底层，使用 `platformdirs` 智能适配。你的数据将被妥善、无污染地存放在操作系统的专属用户数据目录中。
- **AI 打更人机制**：集成每日 23:30 自动异步执行的 AI 复盘服务，利用带有“毒舌+鼓励”性格的系统 Prompt，生成总结后调用 WxPusher 报警至你的手机。
- **多维度防打扰**：跨平台空闲/解锁状态监听（Beta开发中），智能合并并挂起处于锁屏状态下的强提醒弹窗。

## 🛠️ 环境要求与安装

本项目对跨平台兼容性极佳，但由于使用了最新的 Qt 渲染引擎，请确保你的环境版本足够现代。

```bash
# 1. 确保 Python 3.10+
python3 --version

# 2. 安装所有重构后的底层依赖
pip install PySide6 platformdirs requests pynput

# 3. 授予执行权限并启动主程序
chmod +x gtd_ticker/main.py
./gtd_ticker/main.py &
```

## ⚙️ 核心环境变量

打开 `gtd_ticker/config.py`，你可以在此调整你的极客参数：
- `AI_API_BASE_URL` / `AI_API_KEY`：配置你的大模型地址以激活“毒舌教练”。
- `WXPUSHER_APP_TOKEN` / `WXPUSHER_UID`：配置手机端强提醒推送令牌。
- `POMODORO_MINUTES`：全局沉浸状态倒计时长度。

## 📁 架构说明
本仓库不再使用杂乱无章的平铺脚本，而是严格遵循 Clean Architecture 原则。业务逻辑、底层持久化与视图渲染完全解耦。详情可阅读仓库底部的代码导读。
