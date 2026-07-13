"""Stateful gesture recognition service for FastAPI routes."""
from __future__ import annotations

import json
import copy
from pathlib import Path
from threading import RLock
from typing import Any

from gesture_dinov2_tcn import DINO_ALGORITHM_ID, Dinov2TcnPrototypeRuntime
from gesture_dinov2_tcn.runtime import LEGACY_ALGORITHM_ID

from . import config

from .engine import (
    ACTION_LABELS,
    action_label,
    cancel_recording,
    clear_prototypes,
    create_recognition_engine,
    delete_prototype,
    enroll_vectors,
    extract_feature_vector,
    get_recording_status,
    get_vehicle_state,
    process_frame,
    recognize_once,
    start_recording,
    summarize_prototypes,
    normalize_action,
    update_engine_config,
    update_prototype,
)

BUILT_IN_GESTURES = [
    {
        "gestureCode": "Closed_Fist",
        "gestureName": "握拳",
        "gestureKind": "static",
        "gestureSource": "built_in",
        "actionType": "NONE",
    },
    {
        "gestureCode": "Open_Palm",
        "gestureName": "手掌张开",
        "gestureKind": "static",
        "gestureSource": "built_in",
        "actionType": "NONE",
    },
    {
        "gestureCode": "Pointing_Up",
        "gestureName": "单指向上",
        "gestureKind": "static",
        "gestureSource": "built_in",
        "actionType": "NONE",
    },
    {
        "gestureCode": "Thumb_Down",
        "gestureName": "拇指向下",
        "gestureKind": "static",
        "gestureSource": "built_in",
        "actionType": "NONE",
    },
    {
        "gestureCode": "Thumb_Up",
        "gestureName": "拇指向上",
        "gestureKind": "static",
        "gestureSource": "built_in",
        "actionType": "NONE",
    },
    {
        "gestureCode": "Victory",
        "gestureName": "胜利手势",
        "gestureKind": "static",
        "gestureSource": "built_in",
        "actionType": "NONE",
    },
    {
        "gestureCode": "ILoveYou",
        "gestureName": "I Love You",
        "gestureKind": "static",
        "gestureSource": "built_in",
        "actionType": "NONE",
    },
]


class GestureRecognitionService:
    def __init__(
        self,
        config_path: Path,
        prototype_path: Path,
        deep_checkpoint_path: Path | None = None,
        deep_prototype_path: Path | None = None,
    ) -> None:
        self.config_path = config_path
        self.prototype_path = prototype_path
        self._lock = RLock()
        self.engine = create_recognition_engine(self._load_prototypes(), self._load_config())
        active = str(self.engine["config"].get("activeAlgorithm") or LEGACY_ALGORITHM_ID)
        self.active_algorithm = active if active in {LEGACY_ALGORITHM_ID, DINO_ALGORITHM_ID} else LEGACY_ALGORITHM_ID
        self.engine["config"]["activeAlgorithm"] = self.active_algorithm
        deep_store = deep_prototype_path or prototype_path.with_name("dinov2_tcn_gesture_prototypes.json")
        self.deep_runtime = Dinov2TcnPrototypeRuntime(
            deep_checkpoint_path or Path("gesture_dinov2_tcn/checkpoints/best_model.pt"),
            deep_store,
        )

    def health(self) -> dict[str, Any]:
        with self._lock:
            return {
                "ok": True,
                "service": "owner-gesture-recognition",
                "activeAlgorithm": self.active_algorithm,
                "prototypes": len(self._active_prototypes()),
                "recording": self._active_recording_status(),
                "algorithms": self.algorithm_state()["options"],
            }

    def algorithm_state(self) -> dict[str, Any]:
        return {
            "active": self.active_algorithm,
            "options": [
                {
                    "id": LEGACY_ALGORITHM_ID,
                    "name": "MediaPipe 关键点原型",
                    "description": "原有关键点余弦/轨迹匹配算法",
                    "ready": True,
                },
                {
                    "id": DINO_ALGORITHM_ID,
                    "name": "DINOv2 + TCN 视频原型",
                    "description": "RGB 视频与 175 维手部几何特征融合",
                    **self.deep_runtime.status(),
                },
            ],
        }

    def select_algorithm(self, algorithm_id: str) -> dict[str, Any]:
        target = str(algorithm_id or "").strip()
        if target not in {LEGACY_ALGORITHM_ID, DINO_ALGORITHM_ID}:
            raise ValueError("不支持的手势识别算法")
        with self._lock:
            if target == DINO_ALGORITHM_ID:
                self.deep_runtime.ensure_ready()
            cancel_recording(self.engine)
            self.deep_runtime.cancel_recording()
            self.deep_runtime.reset_live()
            self.active_algorithm = target
            self.engine["config"]["activeAlgorithm"] = target
            self._persist_config()
            return self._state_unlocked()

    def state(self, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        with self._lock:
            return self._state_unlocked(extra)

    def get_config(self) -> dict[str, Any]:
        with self._lock:
            return {"config": self._effective_config()}

    def update_config(self, payload: dict[str, Any], replace: bool = False) -> dict[str, Any]:
        with self._lock:
            next_config = payload if replace else self._deep_merge(self.engine["config"], payload)
            update_engine_config(self.engine, next_config)
            self._persist_config()
            return self._state_unlocked()

    def list_prototypes(self) -> dict[str, Any]:
        with self._lock:
            return {"prototypes": self._active_prototypes(), "algorithm": self.algorithm_state()}

    def clear_prototypes(self) -> dict[str, Any]:
        with self._lock:
            if self._using_deep_algorithm():
                self.deep_runtime.clear_prototypes()
            else:
                clear_prototypes(self.engine)
                self._persist_prototypes()
            return self._state_unlocked()

    def delete_prototype(self, prototype_id: str) -> dict[str, Any]:
        with self._lock:
            if self._using_deep_algorithm():
                self.deep_runtime.delete_prototype(prototype_id)
            else:
                delete_prototype(self.engine, prototype_id)
                self._persist_prototypes()
            return self._state_unlocked()

    def start_recording(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            if self._using_deep_algorithm():
                self.deep_runtime.start_recording(payload)
            else:
                start_recording(self.engine, payload)
            return self._state_unlocked()

    def cancel_recording(self) -> dict[str, Any]:
        with self._lock:
            if self._using_deep_algorithm():
                self.deep_runtime.cancel_recording()
            else:
                cancel_recording(self.engine)
            return self._state_unlocked()

    def process_frame(self, vector: list[float]) -> dict[str, Any]:
        """Backward-compatible entry point used by the original tests/API."""
        with self._lock:
            result = process_frame(self.engine, vector)
            if result.get("recordingComplete"):
                self._persist_prototypes()
            return result

    def process_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            if self._using_deep_algorithm():
                result = self.deep_runtime.process(payload, self.engine["config"])
                result["vehicle"] = get_vehicle_state(self.engine)
                return result
            vector = self._vector_from_payload(payload)
            result = process_frame(self.engine, vector)
            if result.get("recordingComplete"):
                self._persist_prototypes()
            result["algorithm"] = self.algorithm_state()
            return result

    def recognize(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self._using_deep_algorithm():
            with self._lock:
                result = self.deep_runtime.process(payload, self.engine["config"])
                return {"recognition": result["recognition"], "algorithm": result["algorithm"]}
        vector = self._vector_from_payload(payload)
        sequence = payload.get("sequence") or []
        # 只在复制共享配置/原型时持锁；实际匹配使用请求私有快照，多个
        # recognize 请求可在线程池中真正并行，同时不会观察到半次更新。
        with self._lock:
            prototypes = copy.deepcopy(self.engine["prototypes"])
            engine_config = copy.deepcopy(self.engine["config"])
        recognition = recognize_once(prototypes, vector, sequence, engine_config)
        return {"recognition": recognition}

    def enroll(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self._using_deep_algorithm():
            raise ValueError("DINOv2-TCN 手势请通过视频录入流程建立原型")
        vectors = self._vectors_from_payload(payload)
        with self._lock:
            gesture = enroll_vectors(self.engine, payload, vectors)
            self._persist_prototypes()
            return self._legacy_payload({"gesture": self._legacy_gesture_for_summary(gesture)})

    def update(self, prototype_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        if self._using_deep_algorithm():
            raise ValueError("DINOv2-TCN 原型请重新录入以更新")
        with self._lock:
            gesture = update_prototype(self.engine, prototype_id, payload)
            self._persist_prototypes()
            return self._legacy_payload({"gesture": self._legacy_gesture_for_summary(gesture)})

    def delete(self, prototype_id: str) -> dict[str, Any]:
        with self._lock:
            if self._using_deep_algorithm():
                self.deep_runtime.delete_prototype(prototype_id)
            else:
                delete_prototype(self.engine, prototype_id)
                self._persist_prototypes()
            return self._legacy_payload()

    def legacy_library(self) -> dict[str, Any]:
        with self._lock:
            return self._legacy_payload()

    def control_settings(self) -> dict[str, Any]:
        with self._lock:
            settings = self._merged_control_settings()
            return {
                "settings": settings,
                "actions": self._action_options(),
                "vehicle": get_vehicle_state(self.engine),
                "config": self.engine["config"],
            }

    def save_control_settings(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            settings = payload.get("settings") if isinstance(payload, dict) else None
            if isinstance(settings, list):
                by_id = {
                    str(item.get("gestureCode")): item
                    for item in settings
                    if isinstance(item, dict) and item.get("gestureCode")
                }
                for prototype in self.engine["prototypes"]:
                    setting = by_id.get(str(prototype.get("id")))
                    if not setting:
                        continue
                    if setting.get("gestureName"):
                        prototype["name"] = str(setting["gestureName"]).strip()
                    if setting.get("actionType"):
                        prototype["action"] = normalize_action(setting["actionType"])
                self.engine["config"]["controlSettings"] = [
                    self._normalize_control_setting(item)
                    for item in settings
                    if isinstance(item, dict) and item.get("gestureCode")
                ]
                self._persist_prototypes()
                self._persist_config()
            return self.control_settings()

    def _state_unlocked(self, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "algorithm": self.algorithm_state(),
            "prototypes": self._active_prototypes(),
            "recording": self._active_recording_status(),
            "vehicle": get_vehicle_state(self.engine),
            "config": self._effective_config(),
            **(extra or {}),
        }

    def _legacy_payload(self, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        raw_prototypes = self.deep_runtime.raw_prototypes() if self._using_deep_algorithm() else self.engine["prototypes"]
        return {
            "gestures": [
                *self._built_in_legacy_gestures(),
                *[self._legacy_gesture(prototype) for prototype in raw_prototypes],
            ],
            "algorithm": self.algorithm_state(),
            "prototypes": self._active_prototypes(),
            "recording": self._active_recording_status(),
            "vehicle": get_vehicle_state(self.engine),
            "config": self._effective_config(),
            **(extra or {}),
        }

    def _using_deep_algorithm(self) -> bool:
        return self.active_algorithm == DINO_ALGORITHM_ID

    def _active_prototypes(self) -> list[dict[str, Any]]:
        if self._using_deep_algorithm():
            return self.deep_runtime.list_prototypes()
        return summarize_prototypes(self.engine["prototypes"])

    def _active_recording_status(self) -> dict[str, Any]:
        if self._using_deep_algorithm():
            return self.deep_runtime.recording_status()
        return get_recording_status(self.engine)

    def _effective_config(self) -> dict[str, Any]:
        effective = copy.deepcopy(self.engine["config"])
        effective["activeAlgorithm"] = self.active_algorithm
        if self._using_deep_algorithm():
            effective["sampleTarget"] = self.deep_runtime.sequence_length
        return effective

    def _legacy_gesture(self, prototype: dict[str, Any]) -> dict[str, Any]:
        return {
            "gestureCode": str(prototype.get("id")),
            "gestureName": prototype.get("name"),
            "action": action_label(prototype.get("action")),
            "actionType": prototype.get("action"),
            "kind": prototype.get("kind", "static"),
            "source": "custom",
            "sampleCount": len(prototype.get("sequence") or []),
            "motion": prototype.get("motion", 0),
            "holdMs": prototype.get("holdMs"),
            "createdAt": prototype.get("createdAt"),
            "vector": prototype.get("vector") or [],
            "sequence": prototype.get("sequence") or [],
        }

    def _legacy_gesture_for_summary(self, summary: dict[str, Any]) -> dict[str, Any]:
        prototype_id = str(summary.get("id"))
        prototype = next((item for item in self.engine["prototypes"] if str(item.get("id")) == prototype_id), None)
        return self._legacy_gesture(prototype or summary)

    def _built_in_legacy_gestures(self) -> list[dict[str, Any]]:
        settings = {item["gestureCode"]: item for item in self._merged_control_settings(include_prototypes=False)}
        default_hold_ms = int(self.engine["config"].get("defaultHoldMs") or 1200)
        gestures = []
        for item in BUILT_IN_GESTURES:
            setting = settings.get(item["gestureCode"], {})
            action_type = setting.get("actionType") or item["actionType"]
            hold_ms = normalize_positive_int(setting.get("holdMs"), default_hold_ms)
            gestures.append({
                "gestureCode": item["gestureCode"],
                "gestureName": setting.get("gestureName") or item["gestureName"],
                "action": action_label(action_type),
                "actionType": action_type,
                "kind": item.get("gestureKind") or "static",
                "source": item.get("gestureSource") or "built_in",
                "sampleCount": 0,
                "motion": 0,
                "holdMs": hold_ms,
                "createdAt": None,
                "enabled": setting.get("enabled", True),
                "vector": [],
                "sequence": [],
            })
        return gestures

    def _merged_control_settings(self, *, include_prototypes: bool = True) -> list[dict[str, Any]]:
        ordered: list[dict[str, Any]] = [
            self._default_control_setting(item)
            for item in BUILT_IN_GESTURES
        ]
        if include_prototypes:
            ordered.extend(self._prototype_control_setting(prototype) for prototype in self.engine["prototypes"])

        merged = {item["gestureCode"]: item for item in ordered}
        for item in self.engine["config"].get("controlSettings") or []:
            if not isinstance(item, dict) or not item.get("gestureCode"):
                continue
            normalized = self._normalize_control_setting(item)
            existing = merged.get(normalized["gestureCode"], {})
            merged[normalized["gestureCode"]] = {**existing, **normalized}

        return [
            self._normalize_control_setting(merged[item["gestureCode"]])
            for item in ordered
            if item["gestureCode"] in merged
        ]

    def _default_control_setting(self, item: dict[str, Any]) -> dict[str, Any]:
        action_type = item.get("actionType") or "NONE"
        hold_ms = normalize_positive_int(item.get("holdMs"), self.engine["config"].get("defaultHoldMs"))
        return {
            "gestureCode": str(item.get("gestureCode")),
            "gestureName": item.get("gestureName"),
            "gestureKind": item.get("gestureKind") or item.get("kind") or "static",
            "gestureSource": item.get("gestureSource") or item.get("source") or "built_in",
            "actionType": action_type,
            "actionLabel": action_label(action_type),
            "enabled": action_type != "NONE",
            "holdMs": hold_ms,
        }

    def _prototype_control_setting(self, prototype: dict[str, Any]) -> dict[str, Any]:
        action_type = prototype.get("action") or "NONE"
        hold_ms = normalize_positive_int(prototype.get("holdMs"), self.engine["config"].get("defaultHoldMs"))
        return {
            "gestureCode": str(prototype.get("id")),
            "gestureName": prototype.get("name"),
            "gestureKind": prototype.get("kind", "static"),
            "gestureSource": prototype.get("source", "custom"),
            "actionType": action_type,
            "actionLabel": action_label(action_type),
            "enabled": action_type != "NONE",
            "holdMs": hold_ms,
        }

    def _normalize_control_setting(self, item: dict[str, Any]) -> dict[str, Any]:
        action_type = item.get("actionType") or "NONE"
        enabled = item.get("enabled", action_type != "NONE")
        setting = {
            "gestureCode": str(item.get("gestureCode")),
            "gestureName": str(item.get("gestureName") or item.get("gestureCode") or "").strip(),
            "gestureKind": str(item.get("gestureKind") or item.get("kind") or "static").strip(),
            "gestureSource": str(item.get("gestureSource") or item.get("source") or "").strip(),
            "actionType": action_type,
            "actionLabel": item.get("actionLabel") or action_label(action_type),
            "enabled": bool(enabled) and action_type != "NONE",
        }
        hold_ms = normalize_positive_int(item.get("holdMs"), None)
        if hold_ms is not None:
            setting["holdMs"] = hold_ms
        return setting

    def _vector_from_payload(self, payload: dict[str, Any]) -> list[float]:
        if isinstance(payload.get("vector"), list):
            return payload["vector"]
        if isinstance(payload.get("landmarks"), list):
            return extract_feature_vector(payload["landmarks"], payload.get("worldLandmarks"))
        raise ValueError("missing_vector")

    def _vectors_from_payload(self, payload: dict[str, Any]) -> list[list[float]]:
        for key in ("featureVectors", "vectors", "sequence"):
            value = payload.get(key)
            if isinstance(value, list) and value and all(isinstance(item, list) for item in value):
                return value
        samples = payload.get("samples") or payload.get("landmarkSamples")
        if isinstance(samples, list) and samples:
            return [extract_feature_vector(sample) for sample in samples if isinstance(sample, list)]
        vector = payload.get("vector")
        if isinstance(vector, list):
            return [vector]
        raise ValueError("至少需要 1 帧手部关键点向量")

    def _load_config(self) -> dict[str, Any]:
        if not self.config_path.exists():
            return {}
        return json.loads(self.config_path.read_text(encoding="utf-8"))

    def _persist_config(self) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps(self.engine["config"], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _load_prototypes(self) -> list[dict[str, Any]]:
        if not self.prototype_path.exists():
            return []
        try:
            parsed = json.loads(self.prototype_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        return parsed if isinstance(parsed, list) else []

    def _persist_prototypes(self) -> None:
        self.prototype_path.parent.mkdir(parents=True, exist_ok=True)
        self.prototype_path.write_text(
            json.dumps(self.engine["prototypes"], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _action_options(self) -> list[dict[str, Any]]:
        return [
            {"actionType": "NONE", "actionLabel": "不触发控制"},
            *[
                {"actionType": action_type, "actionLabel": label}
                for action_type, label in ACTION_LABELS.items()
            ],
        ]

    def _deep_merge(self, target: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
        output = dict(target)
        for key, value in (patch or {}).items():
            if isinstance(value, dict) and isinstance(output.get(key), dict):
                output[key] = self._deep_merge(output[key], value)
            else:
                output[key] = value
        return output


def normalize_positive_int(value: Any, fallback: Any = None) -> int | None:
    for candidate in (value, fallback):
        try:
            numeric = int(candidate)
        except (TypeError, ValueError):
            continue
        if numeric > 0:
            return numeric
    return None


gesture_service = GestureRecognitionService(
    config.GESTURE_CONFIG_PATH,
    config.GESTURE_PROTOTYPE_STORE,
    config.DINO_GESTURE_CHECKPOINT,
    config.DINO_GESTURE_PROTOTYPE_STORE,
)
