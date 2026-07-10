"""Prototype gesture engine ported from gesture_recognition_app/src/gesture-engine.js."""
from __future__ import annotations

import copy
import math
import time
import uuid
from datetime import datetime, timezone
from typing import Any


DEFAULT_CONFIG: dict[str, Any] = {
    "sampleTarget": 45,
    "recordingWarmupFrames": 60,
    "staticMatchThreshold": 0.84,
    "dynamicMatchThreshold": 0.78,
    "palmDirectionThreshold": 0.28,
    "palmWorldDirectionThreshold": 0.62,
    "palmWorldMismatchPenalty": 0.45,
    "minDynamicMotion": 0.28,
    "staticStillMotionLimit": 0.55,
    "staticMotionHardLimit": 0.9,
    "staticMotionPenaltyMax": 0.12,
    "dynamicMotionRatio": 0.45,
    "staticRecognitionHoldMs": 300,
    "triggerCooldownMs": 1500,
    "defaultHoldMs": 1200,
    "sequencePoseWeight": 0.45,
    "sequencePathWeight": 0.55,
    "vehicleVolumeStep": 8,
    "vehicleVolumeMin": 0,
    "vehicleVolumeMax": 100,
    "motionTrackedIndexes": [[66, 67], [24, 25], [12, 13], [36, 37]],
    "vehicleFeatureNames": ["主页", "音乐", "空调", "电话", "导航"],
    "defaultVehicleState": {
        "power": "待唤醒",
        "volume": 35,
        "temperature": 24,
        "phone": "空闲",
        "featureIndex": 0,
    },
}

ACTION_LABELS = {
    "NONE": "不触发控制",
    "wake": "启动 / 唤醒",
    "confirm": "确认 / 执行",
    "volume_up": "音量增加",
    "volume_down": "音量降低",
    "next_feature": "切换功能",
    "answer_call": "接听电话",
    "hangup_call": "挂断电话",
    "home": "返回主页",
}

ACTION_ALIASES = {
    "WAKE_SYSTEM": "wake",
    "CONFIRM": "confirm",
    "VOLUME_UP": "volume_up",
    "VOLUME_DOWN": "volume_down",
    "NEXT_MEDIA": "next_feature",
    "NEXT_FEATURE": "next_feature",
    "ANSWER_CALL": "answer_call",
    "HANG_UP": "hangup_call",
    "HANGUP_CALL": "hangup_call",
    "RETURN_HOME": "home",
    "HOME": "home",
    "启动/唤醒系统": "wake",
    "启动 / 唤醒": "wake",
    "确认当前操作": "confirm",
    "确认 / 执行": "confirm",
    "音量增加": "volume_up",
    "音量降低": "volume_down",
    "切换下一首": "next_feature",
    "切换功能": "next_feature",
    "接听电话": "answer_call",
    "挂断电话": "hangup_call",
    "返回驾驶主页": "home",
    "返回主页": "home",
}


def create_recognition_engine(initial_prototypes: list[dict[str, Any]] | None, config: dict[str, Any] | None) -> dict[str, Any]:
    normalized_config = normalize_config(config)
    feature_names = normalized_config["vehicleFeatureNames"]
    default_vehicle = normalized_config["defaultVehicleState"]
    feature_index = int(default_vehicle.get("featureIndex", 0))

    return {
        "config": normalized_config,
        "prototypes": copy.deepcopy(initial_prototypes or []),
        "liveVectors": [],
        "recording": None,
        "lastStableName": "",
        "stableSince": 0.0,
        "staticStillSince": 0.0,
        "lastTriggerAt": 0.0,
        "vehicle": {
            "power": default_vehicle.get("power", "待唤醒"),
            "volume": default_vehicle.get("volume", 35),
            "temperature": default_vehicle.get("temperature", 24),
            "phone": default_vehicle.get("phone", "空闲"),
            "featureIndex": feature_index,
            "feature": feature_names[feature_index] if 0 <= feature_index < len(feature_names) else feature_names[0],
        },
    }


def update_engine_config(engine: dict[str, Any], next_config: dict[str, Any]) -> dict[str, Any]:
    engine["config"] = normalize_config(next_config)
    sample_target = engine["config"]["sampleTarget"]
    warmup_target = engine["config"]["recordingWarmupFrames"]
    engine["liveVectors"] = engine["liveVectors"][-sample_target:]
    engine["staticStillSince"] = 0.0
    engine["lastStableName"] = ""
    engine["stableSince"] = 0.0
    if engine.get("recording"):
        recording = engine["recording"]
        recording.setdefault("analysisVectors", [])
        recording.setdefault("vectors", [])
        if len(recording["analysisVectors"]) > warmup_target:
            recording["analysisVectors"] = recording["analysisVectors"][-warmup_target:]
        if len(recording["vectors"]) > sample_target:
            recording["vectors"] = recording["vectors"][-sample_target:]
    return engine["config"]


def start_recording(engine: dict[str, Any], options: dict[str, Any]) -> dict[str, Any]:
    name = str(options.get("name") or options.get("gestureName") or "").strip()
    action = normalize_action(options.get("action") or options.get("actionType") or "NONE")
    if not name:
        raise ValueError("动作名称不能为空")

    engine["recording"] = {
        "id": random_id(),
        "name": name,
        "action": action,
        "kind": "pending",
        "phase": "detecting",
        "motion": 0.0,
        "holdMs": int(options.get("holdMs") or engine["config"]["defaultHoldMs"]),
        "analysisVectors": [],
        "vectors": [],
    }
    return get_recording_status(engine)


def cancel_recording(engine: dict[str, Any]) -> dict[str, Any]:
    engine["recording"] = None
    return get_recording_status(engine)


def process_frame(engine: dict[str, Any], vector: list[float], now: float | None = None) -> dict[str, Any]:
    now = performance_now() if now is None else now
    vector = normalize_vector(vector)
    config = engine["config"]
    engine["liveVectors"].append(vector)
    if len(engine["liveVectors"]) > config["sampleTarget"]:
        engine["liveVectors"].pop(0)

    was_recording = bool(engine.get("recording"))
    recording_complete = None
    if engine.get("recording"):
        recording_complete = process_recording_frame(engine, vector)

    live_motion = sequence_motion(engine["liveVectors"][-config["sampleTarget"] :], config)
    static_ready = update_static_readiness(engine, live_motion, now)
    if was_recording:
        recognition = create_recording_recognition(engine, recording_complete, live_motion)
    else:
        match = match_prototype(engine["prototypes"], vector, engine["liveVectors"], static_ready, config)
        recognition = (
            handle_stable_trigger(engine, match, now)
            if match
            else create_rejected_recognition(engine, live_motion, static_ready, now)
        )

    return {
        "recognition": recognition,
        "recording": get_recording_status(engine),
        "recordingComplete": recording_complete,
        "prototypes": summarize_prototypes(engine["prototypes"]),
        "vehicle": get_vehicle_state(engine),
        "config": config,
    }


def recognize_once(
    prototypes: list[dict[str, Any]],
    vector: list[float],
    sequence: list[list[float]] | None,
    config: dict[str, Any],
    now: float | None = None,
) -> dict[str, Any]:
    now = performance_now() if now is None else now
    temp_engine = create_recognition_engine(prototypes, config)
    temp_engine["liveVectors"] = (sequence or [vector])[-temp_engine["config"]["sampleTarget"] :]
    temp_engine["staticStillSince"] = now - temp_engine["config"]["staticRecognitionHoldMs"]
    live_motion = sequence_motion(temp_engine["liveVectors"], temp_engine["config"])
    match = match_prototype(prototypes, normalize_vector(vector), temp_engine["liveVectors"], True, temp_engine["config"])
    if match:
        return {
            "accepted": True,
            "id": match.get("id"),
            "gestureCode": match.get("id"),
            "name": match["name"],
            "action": match.get("action"),
            "kind": normalize_prototype_kind(match),
            "score": match["score"],
            "motion": live_motion,
            "motionLabel": motion_label(live_motion, temp_engine["config"]),
        }
    return {
        "accepted": False,
        "name": "unknown",
        "score": 0,
        "motion": live_motion,
        "motionLabel": motion_label(live_motion, temp_engine["config"]),
    }


def enroll_vectors(engine: dict[str, Any], options: dict[str, Any], vectors: list[list[float]]) -> dict[str, Any]:
    name = str(options.get("name") or options.get("gestureName") or "").strip()
    if not name:
        raise ValueError("动作名称不能为空")
    if not vectors:
        raise ValueError("至少需要 1 帧手部关键点向量")

    normalized_vectors = [normalize_vector(vector) for vector in vectors]
    motion = sequence_motion(normalized_vectors, engine["config"])
    kind = options.get("kind") or infer_kind_from_motion(motion, engine["config"])
    prototype = {
        "id": str(options.get("id") or random_id()),
        "name": name,
        "action": normalize_action(options.get("action") or options.get("actionType") or "NONE"),
        "kind": "dynamic" if kind == "dynamic" else "static",
        "holdMs": int(options.get("holdMs") or engine["config"]["defaultHoldMs"]),
        "motion": motion,
        "vector": mean_vector(normalized_vectors),
        "sequence": normalized_vectors,
        "createdAt": iso_now(),
    }

    engine["prototypes"] = [
        prototype,
        *[
            item
            for item in engine["prototypes"]
            if item.get("id") != prototype["id"] and item.get("name") != prototype["name"]
        ],
    ]
    return summarize_prototypes([prototype])[0]


def update_prototype(engine: dict[str, Any], prototype_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    prototype = find_prototype(engine["prototypes"], prototype_id)
    if not prototype:
        raise ValueError("只能编辑已录入的自定义手势")
    if patch.get("name") or patch.get("gestureName"):
        prototype["name"] = str(patch.get("name") or patch.get("gestureName")).strip()
    if patch.get("action") or patch.get("actionType"):
        prototype["action"] = normalize_action(patch.get("action") or patch.get("actionType"))
    if patch.get("kind"):
        prototype["kind"] = "dynamic" if patch.get("kind") == "dynamic" else "static"
    if patch.get("holdMs"):
        prototype["holdMs"] = int(patch["holdMs"])
    prototype["updatedAt"] = iso_now()
    return summarize_prototypes([prototype])[0]


def delete_prototype(engine: dict[str, Any], prototype_id: str) -> list[dict[str, Any]]:
    prototype = find_prototype(engine["prototypes"], prototype_id)
    if not prototype:
        raise ValueError("手势不存在")
    engine["prototypes"] = [item for item in engine["prototypes"] if item is not prototype]
    return engine["prototypes"]


def clear_prototypes(engine: dict[str, Any]) -> list[dict[str, Any]]:
    engine["prototypes"] = []
    engine["lastStableName"] = ""
    engine["stableSince"] = 0.0
    return engine["prototypes"]


def get_recording_status(engine: dict[str, Any]) -> dict[str, Any]:
    if not engine.get("recording"):
        config = engine["config"]
        total_target = config["recordingWarmupFrames"] + config["sampleTarget"]
        return {
            "active": False,
            "kind": "pending",
            "phase": "idle",
            "count": 0,
            "target": total_target,
            "detectCount": 0,
            "detectTarget": config["recordingWarmupFrames"],
            "sampleCount": 0,
            "sampleTarget": config["sampleTarget"],
            "totalCount": 0,
            "totalTarget": total_target,
            "motion": 0,
            "motionLabel": motion_label(0, config),
        }
    recording = engine["recording"]
    config = engine["config"]
    recording.setdefault("analysisVectors", [])
    recording.setdefault("vectors", [])
    detect_count = len(recording["analysisVectors"])
    sample_count = len(recording["vectors"])
    total_target = config["recordingWarmupFrames"] + config["sampleTarget"]
    phase = recording.get("phase") or "detecting"
    count = detect_count if phase == "detecting" else sample_count
    target = config["recordingWarmupFrames"] if phase == "detecting" else config["sampleTarget"]
    return {
        "active": True,
        "id": recording["id"],
        "name": recording["name"],
        "kind": recording["kind"],
        "phase": phase,
        "count": count,
        "target": target,
        "detectCount": detect_count,
        "detectTarget": config["recordingWarmupFrames"],
        "sampleCount": sample_count,
        "sampleTarget": config["sampleTarget"],
        "totalCount": detect_count + sample_count,
        "totalTarget": total_target,
        "motion": recording.get("motion", 0),
        "motionLabel": motion_label(float(recording.get("motion") or 0), config),
    }


def get_vehicle_state(engine: dict[str, Any]) -> dict[str, Any]:
    return dict(engine["vehicle"])


def summarize_prototypes(prototypes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": prototype.get("id"),
            "name": prototype.get("name"),
            "action": prototype.get("action"),
            "kind": normalize_prototype_kind(prototype),
            "holdMs": prototype.get("holdMs"),
            "motion": prototype.get("motion", 0),
            "createdAt": prototype.get("createdAt"),
        }
        for prototype in prototypes
    ]


def find_prototype(prototypes: list[dict[str, Any]], prototype_id: str) -> dict[str, Any] | None:
    target = str(prototype_id or "")
    for prototype in prototypes:
        if target in {str(prototype.get("id")), str(prototype.get("name")), str(prototype.get("gestureCode"))}:
            return prototype
    return None


def finish_recording(engine: dict[str, Any]) -> dict[str, Any]:
    recording = engine["recording"]
    if recording.get("kind") not in {"dynamic", "static"}:
        motion = sequence_motion(recording["analysisVectors"] or recording["vectors"], engine["config"])
        recording["kind"] = infer_kind_from_motion(motion, engine["config"])
        recording["motion"] = motion
    prototype = {
        "id": random_id(),
        "name": recording["name"],
        "action": recording["action"],
        "kind": recording["kind"],
        "holdMs": recording["holdMs"],
        "motion": sequence_motion(recording["vectors"], engine["config"]),
        "vector": mean_vector(recording["vectors"]),
        "sequence": recording["vectors"],
        "createdAt": iso_now(),
    }
    engine["prototypes"] = [
        prototype,
        *[item for item in engine["prototypes"] if item.get("name") != prototype["name"]],
    ]
    engine["recording"] = None
    return summarize_prototypes([prototype])[0]


def process_recording_frame(engine: dict[str, Any], vector: list[float]) -> dict[str, Any] | None:
    recording = engine["recording"]
    config = engine["config"]
    warmup_target = config["recordingWarmupFrames"]
    recording.setdefault("analysisVectors", [])
    recording.setdefault("vectors", [])

    if len(recording["analysisVectors"]) < warmup_target:
        recording["phase"] = "detecting"
        recording["analysisVectors"].append(vector)
        if len(recording["analysisVectors"]) >= warmup_target:
            motion = sequence_motion(recording["analysisVectors"], config)
            recording["motion"] = motion
            recording["kind"] = infer_kind_from_motion(motion, config)
            recording["phase"] = "sampling"
        return None

    if recording.get("kind") not in {"dynamic", "static"}:
        motion = sequence_motion(recording["analysisVectors"], config)
        recording["motion"] = motion
        recording["kind"] = infer_kind_from_motion(motion, config)
    recording["phase"] = "sampling"
    recording["vectors"].append(vector)
    if len(recording["vectors"]) >= config["sampleTarget"]:
        return finish_recording(engine)
    return None


def create_recording_recognition(
    engine: dict[str, Any],
    recording_complete: dict[str, Any] | None,
    live_motion: float,
) -> dict[str, Any]:
    if recording_complete:
        return {
            "accepted": False,
            "name": recording_complete["name"],
            "kind": recording_complete["kind"],
            "score": None,
            "motion": live_motion,
            "motionLabel": motion_label(live_motion, engine["config"]),
            "triggerState": f"录入完成：{kind_label(recording_complete['kind'])}",
        }

    recording = engine.get("recording") or {}
    phase = recording.get("phase")
    if phase == "detecting":
        trigger_state = "动态判定中"
    elif phase == "sampling":
        trigger_state = f"{kind_label(recording.get('kind'))}采样中"
    else:
        trigger_state = "录入中"
    return {
        "accepted": False,
        "name": recording.get("name") or "录入中",
        "kind": recording.get("kind") or "pending",
        "score": None,
        "motion": live_motion,
        "motionLabel": motion_label(live_motion, engine["config"]),
        "triggerState": trigger_state,
    }


def match_prototype(
    prototypes: list[dict[str, Any]],
    vector: list[float],
    sequence: list[list[float]],
    static_ready: bool,
    config: dict[str, Any],
) -> dict[str, Any] | None:
    best = None
    for prototype in prototypes:
        result = score_prototype(prototype, vector, sequence, static_ready, config)
        if not result["accepted"]:
            continue
        if not best or result["score"] > best["score"]:
            best = {**prototype, **result}
    return best


def score_prototype(
    prototype: dict[str, Any],
    vector: list[float],
    sequence: list[list[float]],
    static_ready: bool,
    config: dict[str, Any],
) -> dict[str, Any]:
    kind = normalize_prototype_kind(prototype)
    live_motion = sequence_motion(sequence[-config["sampleTarget"] :], config)

    if kind == "dynamic":
        required_motion = max(config["minDynamicMotion"], float(prototype.get("motion") or 0) * config["dynamicMotionRatio"])
        if live_motion < required_motion:
            return {"accepted": False, "score": live_motion / required_motion if required_motion else 0, "reason": "motion"}
        score = compare_sequence(sequence, prototype.get("sequence") or [], config)
        return {"accepted": score >= config["dynamicMatchThreshold"], "score": score, "reason": "dynamic"}

    if not static_ready:
        return {"accepted": False, "score": 0, "reason": "static-hold"}

    palm_consistency = palm_direction_consistency(vector, prototype.get("vector") or [], config)
    if palm_consistency < config["palmDirectionThreshold"]:
        return {"accepted": False, "score": palm_consistency, "reason": "palm"}

    score = cosine_similarity(vector, prototype.get("vector") or [])
    if live_motion > config["staticStillMotionLimit"]:
        penalty = min(
            (live_motion - config["staticStillMotionLimit"]) / config["staticMotionHardLimit"],
            config["staticMotionPenaltyMax"],
        )
        score -= penalty

    return {"accepted": score >= config["staticMatchThreshold"], "score": score, "reason": "static"}


def update_static_readiness(engine: dict[str, Any], motion: float, now: float) -> bool:
    config = engine["config"]
    if motion <= config["staticStillMotionLimit"]:
        engine["staticStillSince"] = engine["staticStillSince"] or now
    else:
        engine["staticStillSince"] = 0.0
    return bool(engine["staticStillSince"] and now - engine["staticStillSince"] >= config["staticRecognitionHoldMs"])


def create_rejected_recognition(engine: dict[str, Any], live_motion: float, static_ready: bool, now: float) -> dict[str, Any]:
    engine["lastStableName"] = ""
    engine["stableSince"] = 0.0
    return {
        "accepted": False,
        "name": "unknown" if engine["prototypes"] else "未录入",
        "score": None,
        "motion": live_motion,
        "motionLabel": motion_label(live_motion, engine["config"]),
        "triggerState": static_hold_message(engine, live_motion, static_ready, now)
        or ("拒识" if engine["prototypes"] else "等待录入"),
    }


def handle_stable_trigger(engine: dict[str, Any], match: dict[str, Any], now: float) -> dict[str, Any]:
    config = engine["config"]
    if match["name"] == engine["lastStableName"]:
        engine["stableSince"] = engine["stableSince"] or now
    else:
        engine["lastStableName"] = match["name"]
        engine["stableSince"] = now

    hold_ms = match.get("holdMs") or config["defaultHoldMs"]
    elapsed = now - engine["stableSince"]
    remaining = max(hold_ms - elapsed, 0)
    triggered = False

    if elapsed >= hold_ms and now - engine["lastTriggerAt"] > config["triggerCooldownMs"]:
        engine["lastTriggerAt"] = now
        triggered = True
        apply_vehicle_action(engine, match.get("action"))

    live_motion = sequence_motion(engine["liveVectors"][-config["sampleTarget"] :], config)
    return {
        "accepted": True,
        "id": match.get("id"),
        "gestureCode": match.get("id"),
        "name": match["name"],
        "action": match.get("action"),
        "kind": normalize_prototype_kind(match),
        "score": match["score"],
        "motion": live_motion,
        "motionLabel": motion_label(live_motion, config),
        "triggerState": "已触发" if triggered else (f"稳定中 {math.ceil(remaining / 100) / 10:g}s" if remaining else "可触发"),
        "triggered": triggered,
    }


def apply_vehicle_action(engine: dict[str, Any], action: str | None) -> None:
    action = normalize_action(action)
    config = engine["config"]
    feature_names = config["vehicleFeatureNames"]
    vehicle = engine["vehicle"]
    if action == "wake":
        vehicle["power"] = "已唤醒"
    elif action == "confirm":
        vehicle["power"] = "已执行"
    elif action == "volume_up":
        vehicle["volume"] = min(vehicle["volume"] + config["vehicleVolumeStep"], config["vehicleVolumeMax"])
    elif action == "volume_down":
        vehicle["volume"] = max(vehicle["volume"] - config["vehicleVolumeStep"], config["vehicleVolumeMin"])
    elif action == "next_feature":
        vehicle["featureIndex"] = (vehicle["featureIndex"] + 1) % len(feature_names)
        vehicle["feature"] = feature_names[vehicle["featureIndex"]]
    elif action == "answer_call":
        vehicle["phone"] = "通话中"
    elif action == "hangup_call":
        vehicle["phone"] = "已挂断"
    elif action == "home":
        vehicle["featureIndex"] = 0
        vehicle["feature"] = feature_names[0]


def static_hold_message(engine: dict[str, Any], motion: float, static_ready: bool, now: float) -> str:
    config = engine["config"]
    if static_ready or motion > config["staticStillMotionLimit"] or not has_static_prototype(engine):
        return ""
    elapsed = now - engine["staticStillSince"]
    remaining = max(config["staticRecognitionHoldMs"] - elapsed, 0)
    return f"静态稳定中 {math.ceil(remaining / 100) / 10:g}s"


def has_static_prototype(engine: dict[str, Any]) -> bool:
    return any(normalize_prototype_kind(prototype) == "static" for prototype in engine["prototypes"])


def extract_feature_vector(landmarks: list[dict[str, float]], world_landmarks: list[dict[str, float]] | None = None) -> list[float]:
    if len(landmarks) < 21:
        raise ValueError("手势识别需要 21 个手部关键点")
    wrist = landmarks[0]
    middle_base = landmarks[9]
    center = {
        "x": sum(point.get("x", 0) for point in landmarks) / len(landmarks),
        "y": sum(point.get("y", 0) for point in landmarks) / len(landmarks),
        "z": sum(point.get("z", 0) for point in landmarks) / len(landmarks),
    }
    scale = distance(wrist, middle_base) or 1
    normalized = [
        value
        for point in landmarks
        for value in (
            (point.get("x", 0) - wrist.get("x", 0)) / scale,
            (point.get("y", 0) - wrist.get("y", 0)) / scale,
            (point.get("z", 0) - wrist.get("z", 0)) / scale,
        )
    ]
    finger_tips = [landmarks[index] for index in [4, 8, 12, 16, 20]]
    palm_spread = [
        distance(finger_tips[0], finger_tips[4]) / scale,
        distance(finger_tips[1], finger_tips[3]) / scale,
        distance(finger_tips[2], wrist) / scale,
    ]
    palm_direction = palm_direction_score(landmarks)
    finger_curl = [
        distance(landmarks[tip_index], wrist) / (distance(landmarks[tip_index - 2], wrist) or 1)
        for tip_index in [8, 12, 16, 20]
    ]
    world_palm_direction = palm_direction_score(world_landmarks) if world_landmarks else palm_direction
    return [
        *normalized,
        *palm_spread,
        center["x"],
        center["y"],
        center["z"],
        palm_direction,
        *finger_curl,
        world_palm_direction,
    ]


def mean_vector(vectors: list[list[float]]) -> list[float]:
    if not vectors:
        return []
    length = len(vectors[0])
    return [sum(vector[index] if index < len(vector) else 0 for vector in vectors) / len(vectors) for index in range(length)]


def compare_sequence(live_sequence: list[list[float]], prototype_sequence: list[list[float]], config: dict[str, Any]) -> float:
    if not prototype_sequence or len(live_sequence) < len(prototype_sequence):
        return 0
    window = live_sequence[-len(prototype_sequence) :]
    sequence_total = sum(cosine_similarity(window[index], prototype_vector) for index, prototype_vector in enumerate(prototype_sequence))
    sequence_score = sequence_total / len(prototype_sequence)
    path_score = compare_path(window, prototype_sequence, config)
    return sequence_score * config["sequencePoseWeight"] + path_score * config["sequencePathWeight"]


def compare_path(live_sequence: list[list[float]], prototype_sequence: list[list[float]], config: dict[str, Any]) -> float:
    live_path = center_deltas(live_sequence, config)
    prototype_path = center_deltas(prototype_sequence, config)
    if not live_path or len(live_path) != len(prototype_path):
        return 0
    return cosine_similarity(live_path, prototype_path)


def center_deltas(sequence: list[list[float]], config: dict[str, Any]) -> list[float]:
    values = []
    for index in range(1, len(sequence)):
        for x_index, y_index in config["motionTrackedIndexes"]:
            if x_index >= len(sequence[index]) or y_index >= len(sequence[index]) or x_index >= len(sequence[index - 1]) or y_index >= len(sequence[index - 1]):
                continue
            values.append(sequence[index][x_index] - sequence[index - 1][x_index])
            values.append(sequence[index][y_index] - sequence[index - 1][y_index])
    return values


def sequence_motion(sequence: list[list[float]] | None, config: dict[str, Any] | None = None) -> float:
    config = normalize_config(config)
    if not sequence or len(sequence) < 2:
        return 0
    total = 0.0
    for index in range(1, len(sequence)):
        frame_motion = 0.0
        tracked = 0
        for x_index, y_index in config["motionTrackedIndexes"]:
            if x_index >= len(sequence[index]) or y_index >= len(sequence[index]) or x_index >= len(sequence[index - 1]) or y_index >= len(sequence[index - 1]):
                continue
            frame_motion += math.hypot(sequence[index][x_index] - sequence[index - 1][x_index], sequence[index][y_index] - sequence[index - 1][y_index])
            tracked += 1
        total += frame_motion / tracked if tracked else 0
    return total


def normalize_prototype_kind(prototype: dict[str, Any]) -> str:
    return "dynamic" if prototype.get("kind") == "dynamic" else "static"


def palm_direction_consistency(current_vector: list[float], prototype_vector: list[float], config: dict[str, Any]) -> float:
    current_world_direction = palm_world_direction_from_vector(current_vector)
    prototype_world_direction = palm_world_direction_from_vector(prototype_vector)
    if math.isfinite(current_world_direction) and math.isfinite(prototype_world_direction):
        world_consistency = direction_consistency(current_world_direction, prototype_world_direction)
        return world_consistency if world_consistency >= config["palmWorldDirectionThreshold"] else world_consistency * config["palmWorldMismatchPenalty"]

    current_direction = palm_direction_from_vector(current_vector)
    prototype_direction = palm_direction_from_vector(prototype_vector)
    if not math.isfinite(current_direction) or not math.isfinite(prototype_direction):
        return 1
    return direction_consistency(current_direction, prototype_direction)


def palm_direction_from_vector(vector: list[float]) -> float:
    if len(vector) > 69:
        return vector[69]
    wrist = vector_point(vector, 0)
    index_base = vector_point(vector, 5)
    pinky_base = vector_point(vector, 17)
    if not wrist or not index_base or not pinky_base:
        return math.nan
    index_vector = subtract_point(index_base, wrist)
    pinky_vector = subtract_point(pinky_base, wrist)
    normal = cross_product(index_vector, pinky_vector)
    length = math.sqrt(normal["x"] ** 2 + normal["y"] ** 2 + normal["z"] ** 2) or 1
    return normal["z"] / length


def palm_world_direction_from_vector(vector: list[float]) -> float:
    return vector[74] if len(vector) > 74 else math.nan


def direction_consistency(current_direction: float, prototype_direction: float) -> float:
    return 1 - min(abs(current_direction - prototype_direction), 2) / 2


def palm_direction_score(landmarks: list[dict[str, float]]) -> float:
    wrist = landmarks[0]
    index_base = landmarks[5]
    pinky_base = landmarks[17]
    index_vector = subtract_point(index_base, wrist)
    pinky_vector = subtract_point(pinky_base, wrist)
    normal = cross_product(index_vector, pinky_vector)
    length = math.sqrt(normal["x"] ** 2 + normal["y"] ** 2 + normal["z"] ** 2) or 1
    return normal["z"] / length


def vector_point(vector: list[float], landmark_index: int) -> dict[str, float] | None:
    start = landmark_index * 3
    if len(vector) <= start + 2:
        return None
    return {"x": vector[start], "y": vector[start + 1], "z": vector[start + 2]}


def subtract_point(a: dict[str, float], b: dict[str, float]) -> dict[str, float]:
    return {
        "x": a.get("x", 0) - b.get("x", 0),
        "y": a.get("y", 0) - b.get("y", 0),
        "z": a.get("z", 0) - b.get("z", 0),
    }


def cross_product(a: dict[str, float], b: dict[str, float]) -> dict[str, float]:
    return {
        "x": a["y"] * b["z"] - a["z"] * b["y"],
        "y": a["z"] * b["x"] - a["x"] * b["z"],
        "z": a["x"] * b["y"] - a["y"] * b["x"],
    }


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0
    length = min(len(a), len(b))
    dot = sum(a[index] * b[index] for index in range(length))
    norm_a = sum(a[index] * a[index] for index in range(length))
    norm_b = sum(b[index] * b[index] for index in range(length))
    return dot / (math.sqrt(norm_a) * math.sqrt(norm_b) or 1)


def distance(a: dict[str, float], b: dict[str, float]) -> float:
    return math.sqrt(
        (a.get("x", 0) - b.get("x", 0)) ** 2
        + (a.get("y", 0) - b.get("y", 0)) ** 2
        + (a.get("z", 0) - b.get("z", 0)) ** 2
    )


def motion_label(motion: float, config: dict[str, Any]) -> str:
    value = f"{motion:.2f}"
    if motion <= config["minDynamicMotion"]:
        return f"画面静态 {value}"
    if motion <= config["staticStillMotionLimit"]:
        return f"画面小幅变化 {value}"
    return f"画面动态 {value}"


def infer_kind_from_motion(motion: float, config: dict[str, Any]) -> str:
    return "dynamic" if motion >= config["minDynamicMotion"] else "static"


def kind_label(kind: Any) -> str:
    return "动态轨迹" if kind == "dynamic" else "静态姿态"


def normalize_config(config: dict[str, Any] | None) -> dict[str, Any]:
    merged = copy.deepcopy(DEFAULT_CONFIG)
    if config:
        merged = deep_merge(merged, config)
    return merged


def deep_merge(target: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    output = copy.deepcopy(target)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(output.get(key), dict):
            output[key] = deep_merge(output[key], value)
        else:
            output[key] = copy.deepcopy(value)
    return output


def normalize_vector(vector: list[Any]) -> list[float]:
    if not isinstance(vector, list):
        raise ValueError("手势识别输入必须是关键点特征向量")
    return [float(value) for value in vector]


def normalize_action(action: Any) -> str:
    value = str(action or "").strip()
    return ACTION_ALIASES.get(value, value)


def action_label(action: Any) -> str:
    normalized = normalize_action(action)
    return ACTION_LABELS.get(normalized, str(action or normalized))


def random_id() -> str:
    return str(uuid.uuid4())


def performance_now() -> float:
    return time.perf_counter() * 1000


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
