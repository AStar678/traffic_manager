"""手部关键点检测模块 —— MediaPipe Hands
数据集: HaGRIDv2 (HAnd Gesture Recognition Image Dataset)
HaGRIDv2 包含18种手势约55万张图像，覆盖不同光照、背景和手型
"""
import numpy as np

class HandDetector:
    """MediaPipe Hands 手部21点关键点检测器"""

    LANDMARK_NAMES = [
        "wrist",
        "thumb_cmc", "thumb_mcp", "thumb_ip", "thumb_tip",
        "index_finger_mcp", "index_finger_pip", "index_finger_dip", "index_finger_tip",
        "middle_finger_mcp", "middle_finger_pip", "middle_finger_dip", "middle_finger_tip",
        "ring_finger_mcp", "ring_finger_pip", "ring_finger_dip", "ring_finger_tip",
        "pinky_mcp", "pinky_pip", "pinky_dip", "pinky_tip"
    ]

    def __init__(self, min_detection_confidence: float = 0.7):
        self.min_confidence = min_detection_confidence
        # TODO: 初始化 MediaPipe Hands
        # import mediapipe as mp
        # self.hands = mp.solutions.hands.Hands(
        #     static_image_mode=False,
        #     max_num_hands=1,
        #     min_detection_confidence=min_detection_confidence
        # )

    def detect(self, image: np.ndarray) -> list:
        """检测手部关键点
        Returns:
            [{name: str, x: float, y: float, score: float}, ...]  (21个关键点)
        """
        # TODO: MediaPipe Hands 推理
        pass
