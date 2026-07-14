"""Hard-coded MediaPipe system gestures evaluated before user prototypes."""
from __future__ import annotations

import math
import time
from collections import deque
from dataclasses import dataclass
from typing import Any

import numpy as np


SYSTEM_GESTURE_MIN_CONFIDENCE = 0.90
SYSTEM_GESTURE_HOLD_MS = 1200
OPEN_PALM_CONFIRM_MS = 1000
DYNAMIC_GESTURE_MIN_CONFIDENCE = 0.90
MEDIAPIPE_OPEN_PALM_MIN_CONFIDENCE = 0.55
SWIPE_DURATION_MS = 300
WAVE_DURATION_MS = 600

SYSTEM_GESTURES: tuple[dict[str, Any], ...] = (
    {
        "gestureCode": "Swipe_Left",
        "gestureName": "向左滑动",
        "gestureKind": "dynamic",
        "holdMs": SWIPE_DURATION_MS,
    },
    {
        "gestureCode": "Swipe_Right",
        "gestureName": "向右滑动",
        "gestureKind": "dynamic",
        "holdMs": SWIPE_DURATION_MS,
    },
    {
        "gestureCode": "Open_Palm",
        "gestureName": "手掌张开",
        "gestureKind": "static",
        "holdMs": OPEN_PALM_CONFIRM_MS,
    },
    {"gestureCode": "Closed_Fist", "gestureName": "握拳", "gestureKind": "static"},
    {
        "gestureCode": "Waving",
        "gestureName": "挥手",
        "gestureKind": "dynamic",
        "holdMs": WAVE_DURATION_MS,
    },
)

_GESTURE_BY_CODE = {item["gestureCode"]: item for item in SYSTEM_GESTURES}


@dataclass(frozen=True)
class _TrajectoryPoint:
    timestamp_ms: float
    x: float
    y: float
    open_score: float


@dataclass(frozen=True)
class _Candidate:
    code: str
    score: float
    observed_ms: float = 0.0

    @property
    def definition(self) -> dict[str, Any]:
        return _GESTURE_BY_CODE[self.code]


class MediaPipeSystemGestureRecognizer:
    """Recognize five fixed gestures from MediaPipe category and landmark motion."""

    MOTION_WINDOW_MS = 1000.0
    # 前端每 150ms 采样一次；超过 250ms 没有有效手部帧视为张掌中断。
    FRAME_GAP_RESET_MS = 250.0
    DYNAMIC_LATCH_MS = WAVE_DURATION_MS + 450.0
    TRACK_OPEN_SCORE = MEDIAPIPE_OPEN_PALM_MIN_CONFIDENCE
    SWIPE_DISTANCE = 0.05
    SWIPE_CONSISTENCY = 0.65
    SWIPE_HORIZONTAL_DOMINANCE = 0.60
    WAVE_RANGE = 0.09
    WAVE_TRAVEL = 0.15
    DIRECTION_MIN_STEP = 0.004
    DIRECTION_MIN_RUN = 0.04

    def __init__(self) -> None:
        self.trajectory: deque[_TrajectoryPoint] = deque()
        self.last_frame_at = 0.0
        self.stable_code = ""
        self.stable_since = 0.0
        self.stable_triggered = False
        self.last_trigger_at = 0.0
        self.dynamic_latch: _Candidate | None = None
        self.dynamic_latch_until = 0.0
        self.open_palm_active = False
        self.open_palm_score = 0.0

    def reset(self) -> None:
        self.trajectory.clear()
        self.last_frame_at = 0.0
        self._reset_stability()
        self.dynamic_latch = None
        self.dynamic_latch_until = 0.0
        self._reset_open_palm_confirmation()

    def process(
        self,
        payload: dict[str, Any],
        *,
        now_ms: float | None = None,
        cooldown_ms: float = 1500.0,
    ) -> dict[str, Any]:
        now = time.perf_counter() * 1000.0 if now_ms is None else float(now_ms)
        if self.last_frame_at and now - self.last_frame_at > self.FRAME_GAP_RESET_MS:
            self.reset()
        self.last_frame_at = now

        try:
            points = _points_array(payload.get("landmarks"))
        except ValueError:
            self.reset()
            return self._rejected("系统手势关键点不足", 0.0)

        open_score, fist_score = _shape_scores(payload, points)
        mediapipe_name, mediapipe_score = _mediapipe_gesture(payload)
        mediapipe_open_score = (
            mediapipe_score if mediapipe_name in {"open_palm", "openpalm"} else 0.0
        )
        mediapipe_other_gesture = (
            mediapipe_score >= self.TRACK_OPEN_SCORE
            and mediapipe_name
            not in {"", "none", "unknown", "open_palm", "openpalm"}
        )
        if mediapipe_open_score >= self.TRACK_OPEN_SCORE:
            self.open_palm_active = True
            self.open_palm_score = max(self.open_palm_score, mediapipe_open_score)
        elif mediapipe_other_gesture:
            self._reset_open_palm_confirmation()

        center = points[[0, 5, 9, 13, 17], :2].mean(axis=0)
        if mediapipe_open_score >= self.TRACK_OPEN_SCORE:
            self.trajectory.append(
                _TrajectoryPoint(now, float(center[0]), float(center[1]), mediapipe_open_score)
            )
        elif mediapipe_other_gesture or fist_score >= SYSTEM_GESTURE_MIN_CONFIDENCE:
            # 滑动和挥手必须由 MediaPipe Open_Palm 连续驱动，不使用
            # 静态张掌的确认计时；None 帧不增加轨迹，但也不清空已有轨迹。
            self.trajectory.clear()
            self.dynamic_latch = None
            self.dynamic_latch_until = 0.0
        self._trim_trajectory(now)

        candidate = self._classify(
            now,
            open_score,
            fist_score,
            mediapipe_open_score,
            mediapipe_other_gesture,
        )
        threshold = _candidate_min_confidence(candidate)
        if candidate is None or candidate.score < threshold:
            self._reset_stability()
            score = candidate.score if candidate else max(open_score, fist_score)
            return self._rejected("系统手势未达阈值，转用户原型", score)
        return self._stable_result(candidate, now, float(cooldown_ms), threshold)

    def _classify(
        self,
        now: float,
        open_score: float,
        fist_score: float,
        mediapipe_open_score: float,
        mediapipe_other_gesture: bool,
    ) -> _Candidate | None:
        if fist_score >= SYSTEM_GESTURE_MIN_CONFIDENCE and fist_score >= open_score:
            return _Candidate("Closed_Fist", fist_score)
        points = list(self.trajectory)
        dynamic = self._dynamic_candidate(points, mediapipe_open_score)
        if (
            dynamic
            and dynamic.score >= DYNAMIC_GESTURE_MIN_CONFIDENCE
            and (
                self.dynamic_latch is None
                or now > self.dynamic_latch_until
                or (dynamic.code == "Waving" and self.dynamic_latch.code != "Waving")
            )
        ):
            self.dynamic_latch = dynamic
            self.dynamic_latch_until = now + self.DYNAMIC_LATCH_MS

        if (
            self.dynamic_latch
            and now <= self.dynamic_latch_until
            and mediapipe_open_score >= self.TRACK_OPEN_SCORE
        ):
            return _Candidate(
                self.dynamic_latch.code,
                self.dynamic_latch.score,
                self.dynamic_latch.observed_ms,
            )
        if now > self.dynamic_latch_until:
            self.dynamic_latch = None

        if mediapipe_other_gesture:
            return None
        if self.open_palm_active:
            return _Candidate("Open_Palm", max(self.open_palm_score, open_score))
        return None

    def _dynamic_candidate(
        self,
        points: list[_TrajectoryPoint],
        mediapipe_open_score: float,
    ) -> _Candidate | None:
        if len(points) < 3:
            return None
        observed_ms = points[-1].timestamp_ms - points[0].timestamp_ms
        xs = [point.x for point in points]
        ys = [point.y for point in points]
        runs = _direction_runs(xs, self.DIRECTION_MIN_STEP, self.DIRECTION_MIN_RUN)
        horizontal_range = _range(xs)
        travel = sum(abs(value) for value in runs)

        if (
            observed_ms >= WAVE_DURATION_MS
            and len(runs) >= 2
            and horizontal_range >= self.WAVE_RANGE
            and travel >= self.WAVE_TRAVEL
        ):
            motion_score = min(
                horizontal_range / self.WAVE_RANGE,
                travel / self.WAVE_TRAVEL,
                len(runs) / 2.0,
            )
            score = _clip(mediapipe_open_score * 0.60 + _clip(motion_score) * 0.40)
            return _Candidate("Waving", score, observed_ms)

        deltas = [xs[index] - xs[index - 1] for index in range(1, len(xs))]
        total_motion = sum(abs(delta) for delta in deltas)
        net = xs[-1] - xs[0]
        consistency = abs(net) / max(total_motion, 1e-6)
        vertical_range = _range(ys)
        horizontal_dominance = abs(net) / max(abs(net) + vertical_range, 1e-6)
        if (
            observed_ms >= SWIPE_DURATION_MS
            and abs(net) + 1e-6 >= self.SWIPE_DISTANCE
            and consistency >= self.SWIPE_CONSISTENCY
            and horizontal_dominance >= self.SWIPE_HORIZONTAL_DOMINANCE
        ):
            motion_score = min(
                abs(net) / self.SWIPE_DISTANCE,
                consistency / self.SWIPE_CONSISTENCY,
                horizontal_dominance / self.SWIPE_HORIZONTAL_DOMINANCE,
            )
            # 前置摄像头画面是镜像：画面 x 增大对应“向左滑动”，反之亦然。
            code = "Swipe_Left" if net > 0 else "Swipe_Right"
            score = _clip(mediapipe_open_score * 0.60 + _clip(motion_score) * 0.40)
            return _Candidate(code, score, observed_ms)
        return None

    def _stable_result(
        self,
        candidate: _Candidate,
        now: float,
        cooldown_ms: float,
        confidence_threshold: float,
    ) -> dict[str, Any]:
        if candidate.code != self.stable_code:
            self.stable_code = candidate.code
            self.stable_since = now
            self.stable_triggered = False

        hold_ms = float(candidate.definition.get("holdMs") or SYSTEM_GESTURE_HOLD_MS)
        elapsed = max(now - self.stable_since, candidate.observed_ms)
        remaining = max(hold_ms - elapsed, 0.0)
        confirmation_pending = candidate.code == "Open_Palm" and elapsed < hold_ms
        triggered = False
        if (
            elapsed >= hold_ms
            and not self.stable_triggered
            and (not self.last_trigger_at or now - self.last_trigger_at >= cooldown_ms)
        ):
            self.stable_triggered = True
            self.last_trigger_at = now
            triggered = True

        definition = candidate.definition
        if confirmation_pending:
            trigger_state = f"张掌连续确认中 {math.ceil(remaining / 100) / 10:g}s"
        elif triggered:
            trigger_state = "已触发"
        elif self.stable_triggered:
            trigger_state = "已触发，等待手势变化"
        else:
            trigger_state = f"系统手势稳定中 {math.ceil(remaining / 100) / 10:g}s"
        return {
            # 静态张掌首次由 MediaPipe 确认后，1 秒内只要没有出现
            # 其他明确手势就继续计时；None/Unknown 不会中断。
            "accepted": not confirmation_pending,
            "pending": confirmation_pending,
            "id": candidate.code,
            "gestureCode": candidate.code,
            "name": definition["gestureName"],
            "kind": definition["gestureKind"],
            "source": "built_in",
            "recognizer": "mediapipe_hardcoded",
            "score": candidate.score,
            "triggerState": trigger_state,
            "triggered": triggered,
            "stableHoldMs": int(hold_ms),
            "systemConfidenceThreshold": confidence_threshold,
        }

    def _rejected(self, state: str, score: float) -> dict[str, Any]:
        return {
            "accepted": False,
            "name": "unknown",
            "source": "built_in",
            "recognizer": "mediapipe_hardcoded",
            "score": _clip(score),
            "triggerState": state,
            "triggered": False,
            "stableHoldMs": SYSTEM_GESTURE_HOLD_MS,
            "systemConfidenceThreshold": SYSTEM_GESTURE_MIN_CONFIDENCE,
        }

    def _trim_trajectory(self, now: float) -> None:
        threshold = now - self.MOTION_WINDOW_MS
        while self.trajectory and self.trajectory[0].timestamp_ms < threshold:
            self.trajectory.popleft()

    def _reset_stability(self) -> None:
        self.stable_code = ""
        self.stable_since = 0.0
        self.stable_triggered = False

    def _reset_open_palm_confirmation(self) -> None:
        self.open_palm_active = False
        self.open_palm_score = 0.0


def system_gesture_prototypes(algorithm: str) -> list[dict[str, Any]]:
    return [
        {
            "id": item["gestureCode"],
            "gestureCode": item["gestureCode"],
            "name": item["gestureName"],
            "gestureName": item["gestureName"],
            "kind": item["gestureKind"],
            "gestureKind": item["gestureKind"],
            "source": "built_in",
            "gestureSource": "built_in",
            "algorithm": algorithm,
            "holdMs": int(item.get("holdMs") or SYSTEM_GESTURE_HOLD_MS),
            "createdAt": None,
        }
        for item in SYSTEM_GESTURES
    ]


def _shape_scores(payload: dict[str, Any], points: np.ndarray) -> tuple[float, float]:
    geometry_open = _geometric_open_score(points)
    geometry_fist = _geometric_fist_score(points, geometry_open)
    raw = payload.get("mediapipeGesture") or payload.get("mediapipe_gesture") or {}
    if not isinstance(raw, dict):
        return geometry_open, geometry_fist
    name = str(raw.get("categoryName") or raw.get("name") or raw.get("label") or "")
    normalized = name.lower().replace("-", "_").replace(" ", "_")
    score = _clip(_number(raw.get("score"), 0.0))
    if normalized in {"open_palm", "openpalm"}:
        return max(score, geometry_open), min(geometry_fist, 1.0 - score)
    if normalized in {"closed_fist", "closedfist", "fist"}:
        return min(geometry_open, 1.0 - score), max(score, geometry_fist)
    return geometry_open, geometry_fist


def _mediapipe_gesture(payload: dict[str, Any]) -> tuple[str, float]:
    raw = payload.get("mediapipeGesture") or payload.get("mediapipe_gesture") or {}
    if not isinstance(raw, dict):
        return "", 0.0
    name = str(raw.get("categoryName") or raw.get("name") or raw.get("label") or "")
    normalized = name.lower().replace("-", "_").replace(" ", "_")
    return normalized, _clip(_number(raw.get("score"), 0.0))


def _candidate_min_confidence(candidate: _Candidate | None) -> float:
    if candidate is None:
        return SYSTEM_GESTURE_MIN_CONFIDENCE
    if candidate.code in {"Swipe_Left", "Swipe_Right", "Waving"}:
        return DYNAMIC_GESTURE_MIN_CONFIDENCE
    return SYSTEM_GESTURE_MIN_CONFIDENCE


def _geometric_open_score(points: np.ndarray) -> float:
    fingers = ((5, 6, 7, 8), (9, 10, 11, 12), (13, 14, 15, 16), (17, 18, 19, 20))
    scores = [_finger_extension(points, *finger) for finger in fingers]
    return _clip(float(np.mean(scores)))


def _geometric_fist_score(points: np.ndarray, open_score: float) -> float:
    wrist = points[0]
    palm_scale = max(float(np.linalg.norm(points[9] - wrist)), 1e-6)
    tip_distance = float(np.mean([np.linalg.norm(points[index] - wrist) for index in (8, 12, 16, 20)]))
    proximity = _clip((1.45 - tip_distance / palm_scale) / 0.65)
    return _clip((1.0 - open_score) * 0.72 + proximity * 0.28)


def _finger_extension(points: np.ndarray, mcp: int, pip: int, dip: int, tip: int) -> float:
    first = points[pip] - points[mcp]
    second = points[tip] - points[dip]
    denominator = max(float(np.linalg.norm(first) * np.linalg.norm(second)), 1e-6)
    straightness = float(np.dot(first, second) / denominator)
    wrist = points[0]
    reach = float(np.linalg.norm(points[tip] - wrist)) / max(float(np.linalg.norm(points[pip] - wrist)), 1e-6)
    straight_score = _clip((straightness - 0.50) / 0.45)
    reach_score = _clip((reach - 1.02) / 0.28)
    return _clip(straight_score * 0.58 + reach_score * 0.42)


def _points_array(raw: Any) -> np.ndarray:
    if not isinstance(raw, list) or len(raw) != 21:
        raise ValueError("expected 21 landmarks")
    values = []
    for point in raw:
        if isinstance(point, dict):
            values.append([point.get("x", 0.0), point.get("y", 0.0), point.get("z", 0.0)])
        elif isinstance(point, (list, tuple)):
            values.append(list(point)[:3])
        else:
            raise ValueError("invalid landmark")
    array = np.asarray(values, dtype=np.float32)
    if array.shape != (21, 3):
        raise ValueError("invalid landmark shape")
    return array


def _direction_runs(xs: list[float], min_step: float, min_run: float) -> list[float]:
    runs: list[float] = []
    current = 0.0
    for index in range(1, len(xs)):
        delta = xs[index] - xs[index - 1]
        if abs(delta) < min_step:
            continue
        if current == 0.0 or math.copysign(1.0, current) == math.copysign(1.0, delta):
            current += delta
            continue
        if abs(current) >= min_run:
            runs.append(current)
        current = delta
    if abs(current) >= min_run:
        runs.append(current)
    return runs


def _range(values: list[float]) -> float:
    return max(values) - min(values) if len(values) >= 2 else 0.0


def _clip(value: float) -> float:
    return float(np.clip(float(value), 0.0, 1.0))


def _number(value: Any, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback
