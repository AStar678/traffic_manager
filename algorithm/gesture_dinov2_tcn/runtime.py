"""Stateful few-shot runtime for the fused video prototype network."""
from __future__ import annotations

import base64
import copy
import io
import json
import math
import time
import uuid
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np

from .geometry import GEOMETRY_FEATURE_DIM, extract_geometry_features


DINO_ALGORITHM_ID = "dinov2_tcn_prototype"
LEGACY_ALGORITHM_ID = "mediapipe_prototype"


@dataclass(frozen=True)
class VideoSample:
    frame: np.ndarray
    geometry: np.ndarray
    detected: float


class Dinov2TcnPrototypeRuntime:
    """Record and match 12-frame RGB + geometry video prototypes."""

    def __init__(
        self,
        checkpoint_path: Path,
        prototype_path: Path,
        *,
        sequence_length: int = 12,
        image_size: int = 224,
        encoder: Callable[[list[VideoSample]], np.ndarray] | None = None,
        sample_decoder: Callable[[dict[str, Any]], VideoSample] | None = None,
    ) -> None:
        self.checkpoint_path = Path(checkpoint_path)
        self.prototype_path = Path(prototype_path)
        self.sequence_length = int(sequence_length)
        self.image_size = int(image_size)
        self._encoder = encoder
        self._sample_decoder = sample_decoder or self._decode_sample
        self._model = None
        self._device = "cpu"
        self._ready = encoder is not None
        self._load_error = ""
        self.prototypes = self._load_prototypes()
        self.live_samples: deque[VideoSample] = deque(maxlen=self.sequence_length)
        self.recording: dict[str, Any] | None = None
        self.last_stable_id = ""
        self.stable_since = 0.0
        self.last_trigger_at = 0.0

    def status(self) -> dict[str, Any]:
        return {
            "ready": self._ready,
            "loadError": self._load_error or None,
            "checkpointExists": self.checkpoint_path.is_file(),
            "prototypeCount": len(self.prototypes),
            "sequenceLength": self.sequence_length,
            "device": self._device,
        }

    def ensure_ready(self) -> None:
        if self._ready:
            return
        if not self.checkpoint_path.is_file():
            self._load_error = f"DINOv2-TCN 权重不存在: {self.checkpoint_path}"
            raise RuntimeError(self._load_error)
        try:
            import torch

            from .model import GesturePrototypeNetwork

            checkpoint = torch.load(self.checkpoint_path, map_location="cpu", weights_only=False)
            model_config = checkpoint.get("config", {}).get("model", {})
            model = GesturePrototypeNetwork(
                fusion_dim=int(model_config.get("fusion_dim", 256)),
                embedding_dim=int(model_config.get("embedding_dim", 128)),
                tcn_dilations=tuple(model_config.get("tcn_dilations", [1, 2, 4, 8])),
                dropout=float(model_config.get("dropout", 0.20)),
                dino_frame_chunk=int(model_config.get("dino_frame_chunk", self.sequence_length)),
            )
            model.load_state_dict(checkpoint["model"], strict=True)
            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            model.to(self._device).eval()
            self._model = model
            self._encoder = self._encode_with_model
            self._ready = True
            self._load_error = ""
        except Exception as exc:
            self._load_error = str(exc)
            raise RuntimeError(f"DINOv2-TCN 模型加载失败: {exc}") from exc

    def reset_live(self) -> None:
        self.live_samples.clear()
        self.last_stable_id = ""
        self.stable_since = 0.0

    def start_recording(self, options: dict[str, Any]) -> dict[str, Any]:
        self.ensure_ready()
        name = str(options.get("name") or options.get("gestureName") or "").strip()
        kind = str(options.get("kind") or options.get("gestureKind") or "").strip()
        if not name:
            raise ValueError("动作名称不能为空")
        if kind not in {"static", "dynamic"}:
            raise ValueError("请选择动态或静态手势类型")
        self.recording = {
            "id": str(uuid.uuid4()),
            "name": name,
            "kind": kind,
            "action": str(options.get("action") or options.get("actionType") or "NONE"),
            "holdMs": int(options.get("holdMs") or 1200),
            "samples": [],
        }
        return self.recording_status()

    def cancel_recording(self) -> dict[str, Any]:
        self.recording = None
        return self.recording_status()

    def recording_status(self) -> dict[str, Any]:
        if not self.recording:
            return {
                "active": False, "phase": "idle", "count": 0, "target": self.sequence_length,
                "sampleCount": 0, "sampleTarget": self.sequence_length,
                "totalCount": 0, "totalTarget": self.sequence_length,
            }
        count = len(self.recording["samples"])
        return {
            "active": True,
            "id": self.recording["id"],
            "name": self.recording["name"],
            "kind": self.recording["kind"],
            "phase": "sampling",
            "count": count,
            "target": self.sequence_length,
            "sampleCount": count,
            "sampleTarget": self.sequence_length,
            "totalCount": count,
            "totalTarget": self.sequence_length,
        }

    def process(self, payload: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        self.ensure_ready()
        sample = self._sample_decoder(payload)
        self.live_samples.append(sample)
        recording_complete = None
        if self.recording:
            self.recording["samples"].append(sample)
            if len(self.recording["samples"]) >= self.sequence_length:
                recording_complete = self._finish_recording()
            return self._result(
                recognition={
                    "accepted": False,
                    "name": recording_complete["name"] if recording_complete else self.recording["name"],
                    "kind": recording_complete["kind"] if recording_complete else self.recording["kind"],
                    "score": None,
                    "triggerState": "录入完成" if recording_complete else "视频原型采样中",
                },
                recording_complete=recording_complete,
                config=config,
            )

        if len(self.live_samples) < self.sequence_length:
            return self._result(
                recognition=self._rejected(f"时序缓冲 {len(self.live_samples)} / {self.sequence_length}"),
                config=config,
            )
        if not self.prototypes:
            return self._result(recognition=self._rejected("等待录入视频原型"), config=config)

        embedding = self._encode(list(self.live_samples))
        scored = [
            (prototype, float(np.dot(embedding, np.asarray(prototype["embedding"], dtype=np.float32))))
            for prototype in self.prototypes
        ]
        prototype, cosine = max(scored, key=lambda item: item[1])
        # Normalized embedding cosine is mapped to [0, 1] for the existing UI.
        score = float(np.clip((cosine + 1.0) * 0.5, 0.0, 1.0))
        threshold = float(config.get("dinov2MatchThreshold", 0.72))
        if score < threshold:
            self.last_stable_id = ""
            self.stable_since = 0.0
            rejected = self._rejected("拒识")
            rejected["score"] = score
            return self._result(recognition=rejected, config=config)
        return self._result(recognition=self._accepted(prototype, score, config), config=config)

    def list_prototypes(self) -> list[dict[str, Any]]:
        return [self._summary(item) for item in self.prototypes]

    def clear_prototypes(self) -> None:
        self.prototypes = []
        self._persist_prototypes()
        self.reset_live()

    def delete_prototype(self, prototype_id: str) -> None:
        before = len(self.prototypes)
        self.prototypes = [item for item in self.prototypes if str(item.get("id")) != str(prototype_id)]
        if len(self.prototypes) == before:
            raise ValueError("手势不存在")
        self._persist_prototypes()

    def raw_prototypes(self) -> list[dict[str, Any]]:
        return copy.deepcopy(self.prototypes)

    def _finish_recording(self) -> dict[str, Any]:
        assert self.recording is not None
        prototype = {
            "id": self.recording["id"],
            "name": self.recording["name"],
            "kind": self.recording["kind"],
            "action": self.recording["action"],
            "holdMs": self.recording["holdMs"],
            "embedding": self._encode(self.recording["samples"]).tolist(),
            "createdAt": _iso_now(),
            "source": "custom",
            "algorithm": DINO_ALGORITHM_ID,
        }
        self.prototypes = [prototype, *[item for item in self.prototypes if item.get("name") != prototype["name"]]]
        self.recording = None
        self._persist_prototypes()
        return self._summary(prototype)

    def _accepted(self, prototype: dict[str, Any], score: float, config: dict[str, Any]) -> dict[str, Any]:
        now = time.perf_counter() * 1000
        prototype_id = str(prototype["id"])
        if prototype_id != self.last_stable_id:
            self.last_stable_id = prototype_id
            self.stable_since = now
        hold_ms = int(prototype.get("holdMs") or config.get("defaultHoldMs") or 1200)
        elapsed = now - self.stable_since
        remaining = max(hold_ms - elapsed, 0.0)
        triggered = False
        if elapsed >= hold_ms and now - self.last_trigger_at > float(config.get("triggerCooldownMs", 1500)):
            self.last_trigger_at = now
            triggered = True
        return {
            "accepted": True,
            "id": prototype_id,
            "gestureCode": prototype_id,
            "name": prototype["name"],
            "action": prototype.get("action"),
            "kind": prototype.get("kind", "dynamic"),
            "score": score,
            "triggerState": "已触发" if triggered else f"稳定中 {math.ceil(remaining / 100) / 10:g}s",
            "triggered": triggered,
        }

    def _rejected(self, state: str) -> dict[str, Any]:
        return {
            "accepted": False,
            "name": "unknown" if self.prototypes else "未录入",
            "score": None,
            "triggerState": state,
            "triggered": False,
        }

    def _result(
        self,
        *,
        recognition: dict[str, Any],
        config: dict[str, Any],
        recording_complete: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        effective_config = {**config, "sampleTarget": self.sequence_length, "activeAlgorithm": DINO_ALGORITHM_ID}
        return {
            "algorithm": self.algorithm_state(),
            "recognition": recognition,
            "recording": self.recording_status(),
            "recordingComplete": recording_complete,
            "prototypes": self.list_prototypes(),
            "config": effective_config,
        }

    def algorithm_state(self) -> dict[str, Any]:
        return {"active": DINO_ALGORITHM_ID, "runtime": self.status()}

    def _encode(self, samples: list[VideoSample]) -> np.ndarray:
        assert self._encoder is not None
        embedding = np.asarray(self._encoder(samples), dtype=np.float32).reshape(-1)
        norm = max(float(np.linalg.norm(embedding)), 1e-8)
        return embedding / norm

    def _encode_with_model(self, samples: list[VideoSample]) -> np.ndarray:
        import torch

        assert self._model is not None
        frames = torch.from_numpy(np.stack([sample.frame for sample in samples])).permute(0, 3, 1, 2).float() / 255.0
        mean = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1)
        std = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1)
        frames = ((frames - mean) / std).unsqueeze(0).to(self._device)
        geometry = torch.from_numpy(np.stack([sample.geometry for sample in samples])).unsqueeze(0).to(self._device)
        detected = torch.tensor([sample.detected for sample in samples]).unsqueeze(0).to(self._device)
        with torch.inference_mode():
            embedding = self._model(frames, geometry, detected)[0]
        return embedding.float().cpu().numpy()

    def _decode_sample(self, payload: dict[str, Any]) -> VideoSample:
        from PIL import Image

        encoded = str(payload.get("frame") or "")
        if not encoded:
            raise ValueError("DINOv2-TCN 识别需要 RGB 视频帧")
        if "," in encoded:
            encoded = encoded.split(",", 1)[1]
        try:
            image = Image.open(io.BytesIO(base64.b64decode(encoded))).convert("RGB")
        except Exception as exc:
            raise ValueError("RGB 视频帧解码失败") from exc
        image = image.resize((self.image_size, self.image_size), Image.Resampling.BILINEAR)
        frame = np.asarray(image, dtype=np.uint8)
        landmarks = _points_array(payload.get("landmarks"))
        world = _points_array(payload.get("worldLandmarks"), required=False)
        score = float(payload.get("detectionScore") or 1.0)
        handedness = _handedness_value(payload.get("handedness"))
        geometry = extract_geometry_features(
            landmarks, world, detection_score=score, handedness=handedness
        )
        return VideoSample(frame=frame, geometry=geometry, detected=1.0)

    def _load_prototypes(self) -> list[dict[str, Any]]:
        try:
            payload = json.loads(self.prototype_path.read_text(encoding="utf-8"))
            items = payload if isinstance(payload, list) else payload.get("prototypes", [])
            return [item for item in items if isinstance(item, dict) and len(item.get("embedding") or []) == 128]
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return []

    def _persist_prototypes(self) -> None:
        self.prototype_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.prototype_path.with_suffix(self.prototype_path.suffix + ".tmp")
        temporary.write_text(json.dumps(self.prototypes, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.prototype_path)

    @staticmethod
    def _summary(prototype: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": prototype.get("id"),
            "name": prototype.get("name"),
            "kind": prototype.get("kind", "dynamic"),
            "action": prototype.get("action", "NONE"),
            "holdMs": prototype.get("holdMs", 1200),
            "createdAt": prototype.get("createdAt"),
            "source": prototype.get("source", "custom"),
            "algorithm": DINO_ALGORITHM_ID,
        }


def _points_array(raw: Any, *, required: bool = True) -> np.ndarray | None:
    if raw is None and not required:
        return None
    if not isinstance(raw, list) or len(raw) != 21:
        raise ValueError("DINOv2-TCN 识别需要 21 个手部关键点")
    values = []
    for point in raw:
        if isinstance(point, dict):
            values.append([point.get("x", 0.0), point.get("y", 0.0), point.get("z", 0.0)])
        else:
            values.append(list(point)[:3])
    array = np.asarray(values, dtype=np.float32)
    if array.shape != (21, 3):
        raise ValueError("手部关键点格式错误")
    return array


def _handedness_value(value: Any) -> float:
    text = str(value or "").lower()
    if text == "right":
        return 1.0
    if text == "left":
        return -1.0
    try:
        return float(np.clip(float(value), -1.0, 1.0))
    except (TypeError, ValueError):
        return 0.0


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
