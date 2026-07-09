"""交警手势识别完整流水线"""
from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import numpy as np

from utils.image_utils import download_image, draw_keypoints

class PoliceGesturePipeline:
    GESTURE_MAP = {
        0: (None, "无手势", "保持当前驾驶策略"),
        1: ("STOP", "停止信号", "停车等待"),
        2: ("GO_STRAIGHT", "直行信号", "允许通行"),
        3: ("LEFT_TURN", "左转弯信号", "左转通行"),
        4: ("LEFT_WAIT", "左转弯待转信号", "进入待转区"),
        5: ("RIGHT_TURN", "右转弯信号", "右转通行"),
        6: ("LANE_CHANGE", "变道信号", "变更车道"),
        7: ("SLOW_DOWN", "减速慢行信号", "减速慢行"),
        8: ("PULL_OVER", "靠边停车信号", "靠边停车"),
    }

    KEYPOINT_NAMES = [
        "right_shoulder", "right_elbow", "right_wrist",
        "left_shoulder", "left_elbow", "left_wrist",
        "right_hip", "right_knee", "right_ankle",
        "left_hip", "left_knee", "left_ankle",
        "nose", "neck",
    ]

    def __init__(self, config: dict):
        self.source_dir = Path(config["source_dir"])
        self.predictor = None
        self.PG = None
        self.init_error = ""
        self._init_predictor()

    def process(self, image_url: str) -> dict:
        """完整流水线：关键点检测→手势分类→结果组装"""
        image = download_image(image_url)
        detections: list[dict[str, Any]] = []

        if self.predictor is None:
            return {
                "image": {"width": image.width, "height": image.height},
                "detections": detections,
                "detectionCount": 0,
                "annotatedImageUrl": draw_keypoints(image, detections, self._bone_pairs()),
                "modelStatus": self.status,
            }

        with self._working_directory():
            result = self.predictor.from_img(np.asarray(image.convert("RGB"), dtype=np.uint8))

        label_id = int(result[self.PG.OUT_ARGMAX])
        scores = np.asarray(result[self.PG.OUT_SCORES], dtype=float)
        probabilities = self._softmax(scores)
        confidence = float(probabilities[label_id]) if 0 <= label_id < len(probabilities) else 0.0
        coord_norm = np.asarray(result[self.PG.COORD_NORM], dtype=float)
        keypoints = self._keypoints(coord_norm, image.width, image.height)
        bbox = self._bbox_from_keypoints(keypoints, image.width, image.height)
        code, name, action = self.GESTURE_MAP.get(label_id, self.GESTURE_MAP[0])

        if code:
            detections.append({
                "objectId": "person_001",
                "objectType": "traffic_police",
                "bbox": bbox,
                "confidence": round(confidence, 4),
                "gestureCode": code,
                "gestureName": name,
                "action": action,
                "keypoints": keypoints,
                "top3": self._top3(probabilities),
            })

        return {
            "image": {"width": image.width, "height": image.height},
            "detections": detections,
            "detectionCount": len(detections),
            "annotatedImageUrl": draw_keypoints(image, detections, self._bone_pairs()),
            "modelStatus": self.status,
        }

    @property
    def status(self) -> dict[str, Any]:
        return {
            "ready": self.predictor is not None,
            "mode": "ctpgr-pytorch pose+lstm" if self.predictor is not None else "unavailable",
            "message": "已加载交警姿态与 LSTM 模型" if self.predictor is not None else self.init_error,
        }

    def _init_predictor(self) -> None:
        ctpgr_root = self.source_dir / "ctpgr-pytorch-master"
        if not ctpgr_root.exists():
            self.init_error = f"未找到交警识别源码目录: {ctpgr_root}"
            return
        if str(ctpgr_root) not in sys.path:
            sys.path.insert(0, str(ctpgr_root))
        try:
            with self._working_directory(), self._torch_load_cpu_fallback():
                from constants.enum_keys import PG  # type: ignore
                from pred.gesture_pred import GesturePred  # type: ignore

                self.PG = PG
                self.predictor = GesturePred()
        except Exception as exc:  # noqa: BLE001
            self.predictor = None
            self.init_error = f"加载交警手势模型失败: {exc}"

    @contextmanager
    def _working_directory(self):
        previous = Path.cwd()
        os.chdir(self.source_dir)
        try:
            yield
        finally:
            os.chdir(previous)

    @contextmanager
    def _torch_load_cpu_fallback(self):
        """Load CUDA-saved checkpoints on CPU-only machines."""
        try:
            import torch
        except Exception:  # noqa: BLE001
            yield
            return

        if torch.cuda.is_available():
            yield
            return

        original_load = torch.load

        def load_with_cpu(*args, **kwargs):
            kwargs.setdefault("map_location", torch.device("cpu"))
            return original_load(*args, **kwargs)

        torch.load = load_with_cpu
        try:
            yield
        finally:
            torch.load = original_load

    def _keypoints(self, coord_norm: np.ndarray, width: int, height: int) -> list[dict[str, Any]]:
        if coord_norm.shape == (2, len(self.KEYPOINT_NAMES)):
            coords = coord_norm.T
        elif coord_norm.shape == (len(self.KEYPOINT_NAMES), 2):
            coords = coord_norm
        else:
            coords = coord_norm.reshape(2, -1).T[: len(self.KEYPOINT_NAMES)]
        return [
            {
                "name": name,
                "x": int(round(float(x) * width)),
                "y": int(round(float(y) * height)),
                "score": 1.0,
            }
            for name, (x, y) in zip(self.KEYPOINT_NAMES, coords)
        ]

    @staticmethod
    def _bbox_from_keypoints(keypoints: list[dict], width: int, height: int) -> dict:
        xs = [point["x"] for point in keypoints]
        ys = [point["y"] for point in keypoints]
        padding = 24
        return {
            "x1": max(0, min(xs) - padding),
            "y1": max(0, min(ys) - padding),
            "x2": min(width, max(xs) + padding),
            "y2": min(height, max(ys) + padding),
        }

    def _top3(self, probabilities: np.ndarray) -> list[dict[str, Any]]:
        order = np.argsort(probabilities)[-3:][::-1]
        result = []
        for label_id in order:
            code, name, _ = self.GESTURE_MAP.get(int(label_id), self.GESTURE_MAP[0])
            result.append({
                "gestureCode": code,
                "gestureName": name,
                "confidence": round(float(probabilities[label_id]), 4),
            })
        return result

    @staticmethod
    def _softmax(scores: np.ndarray) -> np.ndarray:
        scores = scores - np.max(scores)
        exp = np.exp(scores)
        return exp / max(float(exp.sum()), 1e-8)

    @staticmethod
    def _bone_pairs() -> list[tuple[str, str]]:
        return [
            ("nose", "neck"), ("neck", "left_shoulder"), ("neck", "right_shoulder"),
            ("left_shoulder", "left_elbow"), ("left_elbow", "left_wrist"),
            ("right_shoulder", "right_elbow"), ("right_elbow", "right_wrist"),
            ("left_shoulder", "left_hip"), ("right_shoulder", "right_hip"),
            ("left_hip", "left_knee"), ("left_knee", "left_ankle"),
            ("right_hip", "right_knee"), ("right_knee", "right_ankle"),
        ]
