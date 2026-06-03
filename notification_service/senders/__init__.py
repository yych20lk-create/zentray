from .wxpusher import WxPusherSender
from .dingtalk import DingTalkSender

SENDER_MAP = {
    "wxpusher": WxPusherSender,
    "dingtalk": DingTalkSender
}
