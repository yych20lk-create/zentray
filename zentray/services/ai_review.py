import requests
from typing import Optional
from zentray.config import AI_API_BASE_URL, AI_API_KEY, AI_MODEL_NAME

class AIReviewService:
    """调用大模型 API 生成每日毒舌锐评总结"""
    
    @classmethod
    def generate_summary(cls, prompt: str) -> Optional[str]:
        if not AI_API_KEY:
            return None
            
        headers = {
            "Authorization": f"Bearer {AI_API_KEY}",
            "Content-Type": "application/json"
        }
        
        system_prompt = (
            "你是一个尖酸刻薄但内心温暖的高级效率教练。你会根据用户的待办完成情况和明日计划进行总结，"
            "毫不留情地指出用户的摸鱼行为，但结尾必须给予极其提振士气的鼓励。输出标准 Markdown 格式。"
        )
        
        payload = {
            "model": AI_MODEL_NAME,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7
        }
        
        try:
            resp = requests.post(f"{AI_API_BASE_URL}/chat/completions", json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"AI Review API Error: {e}")
            return None
