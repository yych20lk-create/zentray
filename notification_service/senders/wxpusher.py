import requests
from .base import BaseSender

class WxPusherSender(BaseSender):
    """WxPusher 推送通道"""
    API_URL = "https://wxpusher.zjiecode.com/api/send/message"

    def send(self, title: str, content: str) -> bool:
        app_token = self.config.get("WXPUSHER_APP_TOKEN")
        uid = self.config.get("WXPUSHER_UID")
        if not app_token or not uid:
            print("WxPusher Error: WXPUSHER_APP_TOKEN or WXPUSHER_UID is missing.")
            return False

        payload = {
            "appToken": app_token,
            "content": content,
            "summary": title,
            "contentType": 3,  # Markdown 格式
            "uids": [uid]
        }
        try:
            resp = requests.post(self.API_URL, json=payload, timeout=10)
            resp_json = resp.json()
            if resp_json.get("code") == 1000:
                return True
            else:
                print(f"WxPusher Error: {resp_json}")
                return False
        except Exception as e:
            print(f"WxPusher Connection Error: {e}")
            return False
