"""车主手势识别完整流水线"""
from __future__ import annotations

import numpy as np

from utils.image_utils import download_image, draw_keypoints
from .hand_detector import HandDetector
from .gesture_classifier import OwnerGestureClassifier

class OwnerGesturePipeline:
    def __init__(self, config: dict):
        self.detector = HandDetector(config.get("min_detection_confidence", 0.6))
        self.classifier = OwnerGestureClassifier(config.get("model_path"))

    def process(self, image_url: str) -> dict:
        """完整流水线：手部检测→手势分类→结果组装"""
        image = download_image(image_url)
        array = np.asarray(image.convert("RGB"))
        keypoints = self.detector.detect(array)
        gesture = self.classifier.classify(keypoints)

        detections = []
        if keypoints:
            bbox = self._bbox_from_keypoints(keypoints)
            detections.append({
                "objectId": "hand_001",
                "objectType": "hand",
                "bbox": bbox,
                "confidence": gesture["confidence"],
                "gestureCode": gesture["gesture_code"],
                "gestureName": gesture["gesture_name"],
                "action": gesture["action"],
                "keypoints": keypoints,
            })

        return {
            "image": {"width": image.width, "height": image.height},
            "detections": detections,
            "detectionCount": len(detections),
            "annotatedImageUrl": draw_keypoints(image, detections, self._hand_bones()),
            "vehicleControl": self._vehicle_control(gesture),
            "modelStatus": {
                "detector": self.detector.status,
                "classifier": {"ready": True, "mode": "geometry+prototype-lite"},
            },
        }

    @staticmethod
    def _bbox_from_keypoints(keypoints: list[dict]) -> dict:
        xs = [int(point["x"]) for point in keypoints]
        ys = [int(point["y"]) for point in keypoints]
        padding = 18
        return {
            "x1": max(0, min(xs) - padding),
            "y1": max(0, min(ys) - padding),
            "x2": max(xs) + padding,
            "y2": max(ys) + padding,
        }

    @staticmethod
    def _hand_bones() -> list[tuple[str, str]]:
        return [
            ("wrist", "thumb_cmc"), ("thumb_cmc", "thumb_mcp"), ("thumb_mcp", "thumb_ip"), ("thumb_ip", "thumb_tip"),
            ("wrist", "index_finger_mcp"), ("index_finger_mcp", "index_finger_pip"), ("index_finger_pip", "index_finger_dip"), ("index_finger_dip", "index_finger_tip"),
            ("wrist", "middle_finger_mcp"), ("middle_finger_mcp", "middle_finger_pip"), ("middle_finger_pip", "middle_finger_dip"), ("middle_finger_dip", "middle_finger_tip"),
            ("wrist", "ring_finger_mcp"), ("ring_finger_mcp", "ring_finger_pip"), ("ring_finger_pip", "ring_finger_dip"), ("ring_finger_dip", "ring_finger_tip"),
            ("wrist", "pinky_mcp"), ("pinky_mcp", "pinky_pip"), ("pinky_pip", "pinky_dip"), ("pinky_dip", "pinky_tip"),
        ]

    @staticmethod
    def _vehicle_control(gesture: dict) -> dict:
        return {
            "gestureCode": gesture.get("gesture_code"),
            "gestureName": gesture.get("gesture_name"),
            "action": gesture.get("action"),
            "triggered": bool(gesture.get("gesture_code")),
            "confidence": gesture.get("confidence", 0.0),
        }
