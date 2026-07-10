"""Stateful gesture recognition service for FastAPI routes."""
from __future__ import annotations

import json
from pathlib import Path
from threading import RLock
from typing import Any

import config

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

BUILT_IN_GESTURES = []


class GestureRecognitionService:
    def __init__(self, config_path: Path, prototype_path: Path) -> None:
        self.config_path = config_path
        self.prototype_path = prototype_path
        self._lock = RLock()
        self.engine = create_recognition_engine(self._load_prototypes(), self._load_config())

    def health(self) -> dict[str, Any]:
        with self._lock:
            return {
                "ok": True,
                "service": "owner-gesture-recognition",
                "prototypes": len(self.engine["prototypes"]),
                "recording": get_recording_status(self.engine),
            }

    def state(self, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        with self._lock:
            return self._state_unlocked(extra)

    def get_config(self) -> dict[str, Any]:
        with self._lock:
            return {"config": self.engine["config"]}

    def update_config(self, payload: dict[str, Any], replace: bool = False) -> dict[str, Any]:
        with self._lock:
            next_config = payload if replace else self._deep_merge(self.engine["config"], payload)
            update_engine_config(self.engine, next_config)
            self._persist_config()
            return self._state_unlocked()

    def list_prototypes(self) -> dict[str, Any]:
        with self._lock:
            return {"prototypes": summarize_prototypes(self.engine["prototypes"])}

    def clear_prototypes(self) -> dict[str, Any]:
        with self._lock:
            clear_prototypes(self.engine)
            self._persist_prototypes()
            return self._state_unlocked()

    def delete_prototype(self, prototype_id: str) -> dict[str, Any]:
        with self._lock:
            delete_prototype(self.engine, prototype_id)
            self._persist_prototypes()
            return self._state_unlocked()

    def start_recording(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            start_recording(self.engine, payload)
            return self._state_unlocked()

    def cancel_recording(self) -> dict[str, Any]:
        with self._lock:
            cancel_recording(self.engine)
            return self._state_unlocked()

    def process_frame(self, vector: list[float]) -> dict[str, Any]:
        with self._lock:
            result = process_frame(self.engine, vector)
            if result.get("recordingComplete"):
                self._persist_prototypes()
            return result

    def recognize(self, payload: dict[str, Any]) -> dict[str, Any]:
        vector = self._vector_from_payload(payload)
        sequence = payload.get("sequence") or []
        with self._lock:
            recognition = recognize_once(
                self.engine["prototypes"],
                vector,
                sequence,
                self.engine["config"],
            )
            return {"recognition": recognition}

    def enroll(self, payload: dict[str, Any]) -> dict[str, Any]:
        vectors = self._vectors_from_payload(payload)
        with self._lock:
            gesture = enroll_vectors(self.engine, payload, vectors)
            self._persist_prototypes()
            return self._legacy_payload({"gesture": self._legacy_gesture_for_summary(gesture)})

    def update(self, prototype_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            gesture = update_prototype(self.engine, prototype_id, payload)
            self._persist_prototypes()
            return self._legacy_payload({"gesture": self._legacy_gesture_for_summary(gesture)})

    def delete(self, prototype_id: str) -> dict[str, Any]:
        with self._lock:
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
            "prototypes": summarize_prototypes(self.engine["prototypes"]),
            "recording": get_recording_status(self.engine),
            "vehicle": get_vehicle_state(self.engine),
            "config": self.engine["config"],
            **(extra or {}),
        }

    def _legacy_payload(self, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "gestures": [
                *self._built_in_legacy_gestures(),
                *[self._legacy_gesture(prototype) for prototype in self.engine["prototypes"]],
            ],
            "prototypes": summarize_prototypes(self.engine["prototypes"]),
            "recording": get_recording_status(self.engine),
            "vehicle": get_vehicle_state(self.engine),
            "config": self.engine["config"],
            **(extra or {}),
        }

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
        gestures = []
        for item in BUILT_IN_GESTURES:
            setting = settings.get(item["gestureCode"], {})
            action_type = setting.get("actionType") or item["actionType"]
            gestures.append({
                "gestureCode": item["gestureCode"],
                "gestureName": setting.get("gestureName") or item["gestureName"],
                "action": action_label(action_type),
                "actionType": action_type,
                "kind": "built_in",
                "source": "built_in",
                "sampleCount": 0,
                "motion": 0,
                "holdMs": None,
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
        return {
            "gestureCode": str(item.get("gestureCode")),
            "gestureName": item.get("gestureName"),
            "actionType": action_type,
            "actionLabel": action_label(action_type),
            "enabled": action_type != "NONE",
        }

    def _prototype_control_setting(self, prototype: dict[str, Any]) -> dict[str, Any]:
        action_type = prototype.get("action") or "NONE"
        return {
            "gestureCode": str(prototype.get("id")),
            "gestureName": prototype.get("name"),
            "actionType": action_type,
            "actionLabel": action_label(action_type),
            "enabled": action_type != "NONE",
        }

    def _normalize_control_setting(self, item: dict[str, Any]) -> dict[str, Any]:
        action_type = item.get("actionType") or "NONE"
        enabled = item.get("enabled", action_type != "NONE")
        return {
            "gestureCode": str(item.get("gestureCode")),
            "gestureName": str(item.get("gestureName") or item.get("gestureCode") or "").strip(),
            "actionType": action_type,
            "actionLabel": item.get("actionLabel") or action_label(action_type),
            "enabled": bool(enabled) and action_type != "NONE",
        }

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


gesture_service = GestureRecognitionService(
    config.GESTURE_CONFIG_PATH,
    config.GESTURE_PROTOTYPE_STORE,
)
