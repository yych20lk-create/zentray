import requests

class NotificationClient:
    """提供给 ZenTray 或其他本地工具向移动端推送消息的轻量客户端"""
    def __init__(self, host: str = "127.0.0.1", port: int = 18330):
        self.url = f"http://{host}:{port}/send"

    def send(self, title: str, content: str) -> dict:
        """
        向本地公共发送服务投递一条消息。
        :param title: 消息标题 / 摘要
        :param content: 消息内容 (Markdown 或纯文本)
        :return: 接口返回的响应字典
        """
        payload = {
            "title": title,
            "content": content
        }
        try:
            resp = requests.post(self.url, json=payload, timeout=12)
            return resp.json()
        except requests.exceptions.ConnectionError:
            return {"status": "error", "message": "无法连接到本地通知服务，请确保它已启动。"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
