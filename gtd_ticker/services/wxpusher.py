import requests
from typing import Dict, Any
from gtd_ticker.config import WXPUSHER_APP_TOKEN, WXPUSHER_UID

class WxPusherService:
    """微信 WxPusher 推送服务接口封装"""
    API_URL = "https://wxpusher.zjiecode.com/api/send/message"

    @classmethod
    def send_message(cls, content: str, summary: str = "GTDTicker 通知") -> Dict[str, Any]:
        if not WXPUSHER_APP_TOKEN or not WXPUSHER_UID:
            return {"code": -1, "msg": "WXPUSHER token or UID is missing."}
            
        payload = {
            "appToken": WXPUSHER_APP_TOKEN,
            "content": content,
            "summary": summary,
            "contentType": 3,  # 3 代表 Markdown 格式
            "uids": [WXPUSHER_UID]
        }
        try:
            resp = requests.post(cls.API_URL, json=payload, timeout=10)
            return resp.json()
        except Exception as e:
            return {"code": -1, "msg": str(e)}
