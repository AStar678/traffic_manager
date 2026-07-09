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
        self.available = False
        self.error = ""
        self.mp = None
        self.hands = None
        self._init_mediapipe()

    def detect(self, image: np.ndarray) -> list:
        """检测手部关键点
        Returns:
            [{name: str, x: float, y: float, score: float}, ...]  (21个关键点)
        """
        if not self.available or self.hands is None:
            return []

        if image.ndim != 3:
            raise ValueError("手势识别输入必须是 RGB 图像")

        height, width = image.shape[:2]
        result = self.hands.process(image)
        if not result.multi_hand_landmarks:
            return []

        landmarks = result.multi_hand_landmarks[0].landmark
        return [
            {
                "name": name,
                "x": int(round(point.x * width)),
                "y": int(round(point.y * height)),
                "z": float(point.z),
                "score": 1.0,
            }
            for name, point in zip(self.LANDMARK_NAMES, landmarks)
        ]

    @property
    def status(self) -> dict:
        return {
            "ready": self.available,
            "mode": "MediaPipe Hands" if self.available else "unavailable",
            "message": "已加载 MediaPipe Hands" if self.available else self.error,
        }

    def _init_mediapipe(self) -> None:
        try:
            import mediapipe as mp  # type: ignore

            self.mp = mp
            self.hands = mp.solutions.hands.Hands(
                static_image_mode=True,
                max_num_hands=1,
                min_detection_confidence=self.min_confidence,
            )
            self.available = True
        except Exception as exc:  # noqa: BLE001
            self.error = f"MediaPipe Hands 不可用: {exc}"
