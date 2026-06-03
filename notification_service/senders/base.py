class BaseSender:
    """所有通知通道的基类，负责接收统一的发送请求"""
    def __init__(self, config: dict):
        self.config = config

    def send(self, title: str, content: str) -> bool:
        """
        发送通知消息。
        :param title: 消息标题 / 摘要
        :param content: 消息详细内容 (通常为 Markdown 或纯文本)
        :return: 发送是否成功
        """
        raise NotImplementedError
