import requests
from .base import BaseSender

class DingTalkSender(BaseSender):
    """钉钉机器人 webhook 推送通道"""
    def send(self, title: str, content: str) -> bool:
        webhook_url = self.config.get("DINGTALK_WEBHOOK_URL")
        if not webhook_url:
            print("DingTalk Error: DINGTALK_WEBHOOK_URL is missing.")
            return False

        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": f"### {title}\n\n{content}"
            }
        }
        try:
            resp = requests.post(webhook_url, json=payload, timeout=10)
            if resp.status_code == 200:
                return True
            else:
                print(f"DingTalk Error Status: {resp.status_code}, Body: {resp.text}")
                return False
        except Exception as e:
            print(f"DingTalk Connection Error: {e}")
            return False
