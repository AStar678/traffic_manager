"""车主手势识别完整流水线"""
from .hand_detector import HandDetector
from .gesture_classifier import OwnerGestureClassifier

class OwnerGesturePipeline:
    def __init__(self, config: dict):
        # TODO: 初始化各模块
        pass

    def process(self, image_url: str) -> dict:
        """完整流水线：手部检测→手势分类→结果组装"""
        pass
