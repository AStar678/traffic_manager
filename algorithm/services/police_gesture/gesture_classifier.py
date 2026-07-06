"""交警手势分类模块 — ST-GCN / LSTM"""
class PoliceGestureClassifier:
    GESTURE_MAP = {
        0: ("STOP", "停止信号"),
        1: ("GO_STRAIGHT", "直行信号"),
        2: ("LEFT_TURN", "左转弯信号"),
        3: ("LEFT_WAIT", "左转弯待转信号"),
        4: ("RIGHT_TURN", "右转弯信号"),
        5: ("LANE_CHANGE", "变道信号"),
        6: ("SLOW_DOWN", "减速慢行信号"),
        7: ("PULL_OVER", "靠边停车信号"),
    }

    def __init__(self, model_path: str):
        # TODO: 加载ST-GCN模型
        pass

    def classify(self, keypoint_sequence: list) -> dict:
        """输入关键点序列，返回 gesture_code + gesture_name + confidence"""
        pass
