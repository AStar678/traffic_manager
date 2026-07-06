"""车主手势分类模块 — 几何规则 + MLP"""
class OwnerGestureClassifier:
    GESTURE_MAP = {
        1: ("001", "手掌张开", "启动/唤醒"),
        2: ("002", "握拳", "确认/执行"),
        3: ("003", "单指画圈", "调节音量"),
        4: ("004", "左右滑动", "切换功能"),
        5: ("005", "拇指向上", "接听电话"),
        6: ("006", "拇指向下", "挂断电话"),
        7: ("007", "挥手", "返回主页"),
    }

    def __init__(self):
        # TODO: 初始化分类器
        pass

    def classify(self, keypoint_sequence: list) -> dict:
        """输入关键点序列，返回 gesture_code + gesture_name + action + confidence"""
        pass
