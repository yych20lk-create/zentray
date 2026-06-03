import os
import sys
import json
from http.server import HTTPServer, BaseHTTPRequestHandler

# 将上级目录加入 sys.path 以支持统一模块导入
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from notification_service.senders import SENDER_MAP

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {
            "PORT": 18330,
            "ACTIVE_SENDERS": ["wxpusher"],
            "WXPUSHER": {
                "WXPUSHER_APP_TOKEN": "",
                "WXPUSHER_UID": ""
            }
        }
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading notification config: {e}")
        return {}

class NotificationRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # 禁用标准 http.server 日志输出，使终端保持清爽
        pass

    def _send_response(self, status_code, data):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def do_OPTIONS(self):
        self._send_response(200, {"status": "ok"})

    def do_POST(self):
        if self.path != "/send":
            self._send_response(404, {"error": "Not Found"})
            return

        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)

        try:
            payload = json.loads(post_data.decode("utf-8"))
        except Exception:
            self._send_response(400, {"error": "Invalid JSON payload"})
            return

        title = payload.get("title")
        content = payload.get("content")

        if not title or not content:
            self._send_response(400, {"error": "Missing 'title' or 'content' field"})
            return

        # 每次收到请求时动态读取配置文件，支持免重启即时修改配置
        config = load_config()
        active_senders = config.get("ACTIVE_SENDERS", [])
        
        results = {}
        for sender_name in active_senders:
            if sender_name in SENDER_MAP:
                # 获取该发送通道对应的配置块
                sender_cfg = config.get(sender_name.upper(), {})
                sender_cls = SENDER_MAP[sender_name]
                sender = sender_cls(sender_cfg)
                
                # 执行发送并归档结果
                success = sender.send(title, content)
                results[sender_name] = success
            else:
                results[sender_name] = False
                print(f"Warning: Unknown sender channel: '{sender_name}'")

        # 只要任意一个通道发送成功，就判定为成功
        if any(results.values()):
            self._send_response(200, {"status": "success", "results": results})
        else:
            self._send_response(500, {"status": "failed", "results": results})

def run_server():
    config = load_config()
    port = config.get("PORT", 18330)
    server_address = ("127.0.0.1", port)
    httpd = HTTPServer(server_address, NotificationRequestHandler)
    print(f"📡 Notification Local Service running on http://127.0.0.1:{port}/send")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down Notification Service...")
        httpd.server_close()

if __name__ == "__main__":
    run_server()
