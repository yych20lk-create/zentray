# ZenTray 个人禅定看板 (v3.6)

> 本项目已全面升维至 **跨平台架构 (Windows/macOS/Linux)**，是一款现代化的极致个人效率与专注工具。
> - 在 **Linux (GNOME)** 环境下：采用独创的 **双进程原生桥接 (Native GTK Bridge)**，实现系统顶栏文字级原生无缝融合、状态栏自适应与完美的彩色进度圆饼图标渲染。
> - 在 **Windows / macOS / 其他 Linux** 环境下：自动无缝回退到标准 **Qt 系统托盘模式 (Qt Standard Tray)**，提供统一且美观的系统级交互面板。

---

## 🛠️ 环境要求与安装

### 🚀 快速启动（推荐）

直接运行包装脚本，会自动安装 Python 依赖（从 `requirements.txt` 读取）并启动程序（包括本地通知服务）：

#### Linux / macOS 部署：
```bash
chmod +x run.sh
./run.sh
```
*提示：脚本已配置 `nohup` 运行，进程启动后您可以直接安全地关闭终端，应用仍会在后台持续静默运行。*

#### Windows 部署：
双击运行项目根目录下的 **`run.bat`**。
*提示：批处理脚本会在后台通过 `pythonw.exe` 独立拉起服务和主程序，无任何烦人的 Cmd 命令行黑窗口残留。*

---

## ⚠️ 跨平台注意事项与常见问题 (FAQ)

### 1. macOS 系统下「快捷键无法唤出」
* **原因**：看板的快捷键机制基于 `pynput` 的全局监听，在 macOS 系统中，任何监听全局键鼠的程序都需要系统**辅助功能 (Accessibility) 权限**。
* **解决办法**：
  1. 打开 macOS 的 **系统设置** -> **隐私与安全性** -> **辅助功能**。
  2. 在列表中添加并勾选您运行此脚本的终端软件（如 `Terminal`、`iTerm2` 或 `Visual Studio Code`）。
  3. 重新运行 `./run.sh` 即可。

### 2. Linux 平台下「无法切换中文输入法 (Fcitx5)」
* **原因**：部分 Linux 发行版下的 PySide6 (Qt) 库会与系统的 Fcitx 发生输入法 ABI 冲突。
* **解决办法**：本项目已在 `zentray/main.py` 的入口中自动注入了环境变量：
  ```python
  os.environ["QT_IM_MODULE"] = "ibus"
  ```
  该行已完美解决 Fcitx 唤出与打字问题，无需用户手动配置。

### 3. Windows 下「如何彻底关闭后台程序」
* **原因**：Windows 下使用了 `pythonw` 独立运行于后台。
* **解决办法**：
  * 在托盘图标上右键，选择 **`❌ 退出程序`** 可安全关闭主看板（退出时会自动触发本地通知服务的关闭）。
  * 若要手动清理，亦可直接在 cmd 中运行以下命令杀死残余进程：
    ```cmd
    taskkill /f /im python.exe
    taskkill /f /im pythonw.exe
    ```

---

## ⚙️ 核心配置文件与参数

### 1. 通讯通道配置：`../notification_service/config.json`
在这里配置接收端凭证和激活的推送通道：
- `PORT`: 本地服务监听端口（默认 `18330`）。
- `ACTIVE_SENDERS`: 激活的通道列表（例如 `["wxpusher"]` 或 `["wxpusher", "dingtalk"]`）。
- `WXPUSHER`: 包含 `WXPUSHER_APP_TOKEN` 和 `WXPUSHER_UID`。
- `DINGTALK`: 包含 `DINGTALK_WEBHOOK_URL`。

### 2. ZenTray 配置：`zentray/config.py`
调整番茄钟时间或大模型锐评教练参数：
- `AI_API_BASE_URL` / `AI_API_KEY`：配置大模型地址以激活“毒舌教练”。
- `POMODORO_MINUTES`：番茄钟时长（默认 25 分钟）。
- `HOTKEY_QUICK_ADD`：闪电添加任务的全局快捷键，macOS 默认为 `cmd+alt+t`，Windows/Linux 默认为 `ctrl+alt+t`。

---

## 📡 本地通知 API 接口

任何第三方应用或脚本都可以直接向本地服务投递消息：
* **请求方法**: `POST`
* **请求地址**: `http://127.0.0.1:18330/send`
* **请求体 (JSON)**:
  ```json
  {
    "title": "消息标题",
    "content": "这里是支持 **Markdown** 的正文内容"
  }
  ```

---

## 📁 架构说明
- `zentray/`: 看板核心逻辑与 PySide6 GUI 视图。
- `../notification_service/`: 独立通道通知模块，位于与本项目平级的本地目录。
  - `senders/`: 通道发送器（WxPusher, DingTalk 等，均继承自 `BaseSender`）。
  - `main.py`: 本地 API 服务主入口。
  - `client.py`: 通用推送服务的轻量 Python 客户端类 `NotificationClient`。
- `send_daily_summary.py`: 根目录下的一键手动发送日报脚本。可在终端中通过 `python send_daily_summary.py` 直接调用发送。
