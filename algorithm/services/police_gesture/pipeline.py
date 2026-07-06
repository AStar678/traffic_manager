"""交警手势识别完整流水线"""
from .pose_detector import PoseDetector
from .gesture_classifier import PoliceGestureClassifier

class PoliceGesturePipeline:
    def __init__(self, config: dict):
        # TODO: 初始化各模块
        pass

    def process(self, image_url: str) -> dict:
        """完整流水线：关键点检测→手势分类→结果组装"""
        pass
