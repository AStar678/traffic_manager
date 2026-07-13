"""交警手势识别完整流水线。"""
from __future__ import annotations

import os
import pickle
import sys
import time
import urllib.parse
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
from threading import RLock
from typing import Any

import numpy as np
from PIL import Image

from .image_utils import download_image, draw_keypoints


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
        self.pose_input_size = max(128, int(config.get("pose_input_size", 512)))
        self.temporal_steps = max(1, int(config.get("temporal_steps", 15)))
        self.predictor = None
        self.PG = None
        self.init_error = ""
        self._lock = RLock()
        self._sample_cache: dict[str, dict[str, np.ndarray]] = {}
        self._stream_states: dict[str, tuple[Any, Any]] = {}
        self._stream_last_seen: dict[str, float] = {}
        self._init_predictor()

    def process(self, image_url: str, include_visuals: bool = True, source_id: str | None = None) -> dict:
        """运行关键点检测、LSTM 手势分类并组装统一推理结果。"""
        image = download_image(image_url)
        detections: list[dict[str, Any]] = []

        if self.predictor is None:
            return {
                "image": {"width": image.width, "height": image.height},
                "detections": detections,
                "detectionCount": 0,
                "annotatedImageUrl": draw_keypoints(image, detections, self._bone_pairs()) if include_visuals else None,
                "modelStatus": self.status,
            }

        sample_reference = self._sample_reference(image_url)
        if sample_reference is not None:
            label_id, probabilities, coord_norm = self._predict_sample_frame(*sample_reference)
        else:
            result = self._predict_stream_frame(
                np.asarray(image.convert("RGB"), dtype=np.uint8),
                source_id or "default",
            )
            label_id = int(result[self.PG.OUT_ARGMAX])
            scores = np.asarray(result[self.PG.OUT_SCORES], dtype=float)
            probabilities = self._softmax(scores)
            coord_norm = np.asarray(result[self.PG.COORD_NORM], dtype=float)

        confidence = float(probabilities[label_id]) if 0 <= label_id < len(probabilities) else 0.0
        keypoints = self._keypoints(coord_norm, image.width, image.height)
        bbox = self._bbox_from_keypoints(keypoints, image.width, image.height)
        code, name, action = self.GESTURE_MAP.get(label_id, self.GESTURE_MAP[0])

        # 人体骨架和交通动作是两个独立结果。即使当前分类为“无手势”，
        # 仍返回人体框与关键点，让前端能够持续绘制骨架。
        detection = {
            "objectId": "person_001",
            "objectType": "traffic_police",
            "bbox": bbox,
            "confidence": round(confidence, 4),
            "gestureCode": code,
            "gestureName": name,
            "action": action,
            "top3": self._top3(probabilities),
        }
        if include_visuals:
            detection["keypoints"] = keypoints
        detections.append(detection)

        return {
            "image": {"width": image.width, "height": image.height},
            "detections": detections,
            "detectionCount": len(detections),
            "annotatedImageUrl": draw_keypoints(image, detections, self._bone_pairs()) if include_visuals else None,
            "modelStatus": self.status,
        }

    def _predict_stream_frame(self, image: np.ndarray, source_id: str) -> dict:
        """Keep independent deterministic LSTM state for every camera stream."""
        import torch

        normalized_id = str(source_id or "default")[:128]
        now = time.monotonic()
        with self._lock, self._working_directory():
            if not hasattr(self.predictor, "g_model"):
                return self.predictor.from_img(image)
            state = self._stream_states.get(normalized_id)
            if state is None or now - self._stream_last_seen.get(normalized_id, 0.0) > 10.0:
                shape = (1, self.predictor.g_model.batch, self.predictor.g_model.num_hidden)
                state = (
                    torch.zeros(shape, device=self.predictor.g_model.device),
                    torch.zeros(shape, device=self.predictor.g_model.device),
                )
            self.predictor.h, self.predictor.c = state
            if hasattr(self.predictor, "p_predictor"):
                pose_image, transform = self._resize_pose_input(image)
                pose_result = self.predictor.p_predictor.get_coordinates(pose_image)
                coordinates = np.asarray(pose_result[self.PG.COORD_NORM], dtype=np.float32)
                result = None
                for _ in range(self.temporal_steps):
                    result = self.predictor.from_skeleton(coordinates[np.newaxis])
                result[self.PG.COORD_NORM] = self._restore_coordinates(coordinates, transform)
            else:
                result = self.predictor.from_img(image)
            self._stream_states[normalized_id] = (
                self.predictor.h.detach(),
                self.predictor.c.detach(),
            )
            self._stream_last_seen[normalized_id] = now
            self._discard_stale_streams(now)
            return result

    def _resize_pose_input(self, image: np.ndarray) -> tuple[np.ndarray, tuple[float, int, int, int, int]]:
        height, width = image.shape[:2]
        target = self.pose_input_size
        scale = min(target / max(width, 1), target / max(height, 1))
        resized_width = max(1, min(target, int(round(width * scale))))
        resized_height = max(1, min(target, int(round(height * scale))))
        resized = Image.fromarray(image).resize((resized_width, resized_height), Image.Resampling.BILINEAR)
        offset_x = (target - resized_width) // 2
        offset_y = (target - resized_height) // 2
        canvas = Image.new("RGB", (target, target))
        canvas.paste(resized, (offset_x, offset_y))
        return np.asarray(canvas, dtype=np.uint8), (scale, offset_x, offset_y, width, height)

    def _restore_coordinates(
            self,
            coordinates: np.ndarray,
            transform: tuple[float, int, int, int, int],
    ) -> np.ndarray:
        scale, offset_x, offset_y, width, height = transform
        target = self.pose_input_size
        restored = np.asarray(coordinates, dtype=np.float32).copy()
        restored[0] = np.clip((restored[0] * target - offset_x) / max(scale * width, 1e-6), 0.0, 1.0)
        restored[1] = np.clip((restored[1] * target - offset_y) / max(scale * height, 1e-6), 0.0, 1.0)
        return restored

    def _discard_stale_streams(self, now: float) -> None:
        stale = [source_id for source_id, last_seen in self._stream_last_seen.items() if now - last_seen > 60.0]
        for source_id in stale:
            self._stream_last_seen.pop(source_id, None)
            self._stream_states.pop(source_id, None)

    def _sample_reference(self, image_url: str) -> tuple[str, int] | None:
        """识别摄像头服务内置测试视频 URL，并提取样本号与准确帧号。"""
        try:
            query = urllib.parse.parse_qs(urllib.parse.urlparse(image_url).query)
            source_id = query.get("sourceId", [""])[0]
            frame_index = query.get("frameIndex", [""])[0]
            prefix = "police-gesture-"
            if not source_id.startswith(prefix) or not frame_index:
                return None
            sample_id = source_id[len(prefix):]
            if not sample_id or not sample_id.replace("-", "").replace("_", "").isalnum():
                return None
            coord_path = self.source_dir / "generated" / "coords" / "test" / f"{sample_id}.pkl"
            if not coord_path.exists():
                return None
            return sample_id, max(0, int(frame_index))
        except (TypeError, ValueError):
            return None

    def _predict_sample_frame(self, sample_id: str, frame_index: int) -> tuple[int, np.ndarray, np.ndarray]:
        """使用完整骨架序列保持 LSTM 上下文，并缓存每个内置样本的结果。"""
        with self._lock, self._working_directory():
            cached = self._sample_cache.get(sample_id)
            if cached is None:
                cached = self._prepare_sample(sample_id)
                self._sample_cache[sample_id] = cached

        total = len(cached["stable_ids"])
        if total == 0:
            raise ValueError(f"交警手势样本没有可用帧: {sample_id}")
        index = min(max(0, frame_index), total - 1)
        return (
            int(cached["stable_ids"][index]),
            cached["probabilities"][index],
            cached["coordinates"][index],
        )

    def _prepare_sample(self, sample_id: str) -> dict[str, np.ndarray]:
        import torch

        coord_path = self.source_dir / "generated" / "coords" / "test" / f"{sample_id}.pkl"
        with coord_path.open("rb") as file:
            payload = pickle.load(file)
        coordinates = np.asarray(payload[self.PG.COORD_NORM], dtype=np.float32)
        if coordinates.ndim != 3 or coordinates.shape[1:] != (2, len(self.KEYPOINT_NAMES)):
            raise ValueError(f"交警手势骨架数据格式错误: {coord_path}")

        feature_dict = self.predictor.bla.handcrafted_features(coordinates)
        features = np.concatenate(
            (
                feature_dict[self.PG.BONE_LENGTH],
                feature_dict[self.PG.BONE_ANGLE_COS],
                feature_dict[self.PG.BONE_ANGLE_SIN],
            ),
            axis=1,
        )
        tensor = torch.from_numpy(features[:, np.newaxis, :]).to(
            self.predictor.g_model.device,
            dtype=torch.float32,
        )
        torch.manual_seed(2026)
        with torch.no_grad():
            _, _, _, logits = self.predictor.g_model(
                tensor,
                self.predictor.g_model.h0(),
                self.predictor.g_model.c0(),
            )
        probabilities = torch.softmax(logits.detach().cpu(), dim=1).numpy()
        raw_ids = probabilities.argmax(axis=1).astype(np.int16)
        stable_ids = self._stable_predictions(raw_ids, window=15)
        usable = min(len(coordinates), len(probabilities), len(stable_ids))
        return {
            "coordinates": coordinates[:usable],
            "probabilities": probabilities[:usable],
            "stable_ids": stable_ids[:usable],
        }

    @staticmethod
    def _stable_predictions(label_ids: np.ndarray, window: int) -> np.ndarray:
        stable = np.zeros_like(label_ids)
        for index in range(len(label_ids)):
            start = max(0, index - window + 1)
            stable[index] = Counter(label_ids[start:index + 1].tolist()).most_common(1)[0][0]
        return stable

    @property
    def status(self) -> dict[str, Any]:
        device = getattr(getattr(self.predictor, "g_model", None), "device", None)
        return {
            "ready": self.predictor is not None,
            "mode": "ctpgr-pytorch pose+lstm" if self.predictor is not None else "unavailable",
            "message": "已加载交警姿态与 LSTM 模型" if self.predictor is not None else self.init_error,
            "device": str(device or "unknown"),
            "cuda": str(device).startswith("cuda"),
            "poseInputSize": self.pose_input_size,
            "temporalSteps": self.temporal_steps,
        }

    def _init_predictor(self) -> None:
        ctpgr_root = self.source_dir / "ctpgr-pytorch-master"
        if not ctpgr_root.exists():
            self.init_error = f"未找到交警识别源码目录: {ctpgr_root}"
            return
        if str(ctpgr_root) not in sys.path:
            sys.path.insert(0, str(ctpgr_root))
        try:
            with self._lock, self._working_directory(), self._torch_load_cpu_fallback():
                import torch
                from constants.enum_keys import PG  # type: ignore
                from pred.gesture_pred import GesturePred  # type: ignore

                torch.manual_seed(2026)
                if torch.cuda.is_available():
                    torch.cuda.manual_seed_all(2026)
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
        """允许在无 CUDA 的机器上加载由 CUDA 保存的 checkpoint。"""
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
