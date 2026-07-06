"""车牌识别完整流水线"""
from .detector import LicensePlateDetector
from .ocr import LicensePlateOCR
from .color_classifier import PlateColorClassifier

class LicensePlatePipeline:
    def __init__(self, config: dict):
        # TODO: 初始化各模块
        pass

    def process(self, image_url: str) -> dict:
        """完整流水线：检测→OCR→颜色分类→结果组装"""
        pass
