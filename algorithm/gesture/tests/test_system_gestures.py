from __future__ import annotations

from typing import Any

from gesture.service import GestureRecognitionService
from gesture.system_gestures import MediaPipeSystemGestureRecognizer
from gesture_dinov2_tcn.runtime import DINO_ALGORITHM_ID


def _payload(x: float, category: str, score: float = 0.99, y: float = 0.5) -> dict[str, Any]:
    return {
        "landmarks": [[x, y, 0.0] for _ in range(21)],
        "mediapipeGesture": {"categoryName": category, "score": score},
    }


def _geometry_open_payload(x: float, category: str = "None", score: float = 0.99) -> dict[str, Any]:
    points = [[x, 0.5, 0.0] for _ in range(21)]
    offsets = (-0.06, -0.02, 0.02, 0.06)
    fingers = ((5, 6, 7, 8), (9, 10, 11, 12), (13, 14, 15, 16), (17, 18, 19, 20))
    for offset, indexes in zip(offsets, fingers):
        for y, index in zip((0.4, 0.3, 0.2, 0.1), indexes):
            points[index] = [x + offset, y, 0.0]
    return {
        "landmarks": points,
        "mediapipeGesture": {"categoryName": category, "score": score},
    }


def test_screen_right_motion_is_mirrored_to_left_swipe_and_stabilizes() -> None:
    recognizer = MediaPipeSystemGestureRecognizer()
    start = 10_000.0
    recognizer.process(_payload(0.35, "Open_Palm"), now_ms=start)
    recognizer.process(_payload(0.43, "Open_Palm"), now_ms=start + 150)
    detected = recognizer.process(_payload(0.52, "Open_Palm"), now_ms=start + 300)

    assert detected["gestureCode"] == "Swipe_Left"
    assert detected["triggered"] is True
    assert detected["stableHoldMs"] == 300


def test_screen_left_motion_is_mirrored_to_right_swipe() -> None:
    recognizer = MediaPipeSystemGestureRecognizer()
    start = 20_000.0
    recognizer.process(_payload(0.65, "Open_Palm"), now_ms=start)
    recognizer.process(_payload(0.57, "Open_Palm"), now_ms=start + 150)
    detected = recognizer.process(_payload(0.47, "Open_Palm"), now_ms=start + 300)

    assert detected["gestureCode"] == "Swipe_Right"
    assert detected["triggered"] is True
    assert detected["stableHoldMs"] == 300


def test_sensitive_swipe_accepts_five_percent_motion_at_system_threshold() -> None:
    recognizer = MediaPipeSystemGestureRecognizer()
    start = 25_000.0
    recognizer.process(_payload(0.40, "Open_Palm", 0.85), now_ms=start)
    recognizer.process(_payload(0.425, "Open_Palm", 0.85), now_ms=start + 150)
    detected = recognizer.process(_payload(0.45, "Open_Palm", 0.85), now_ms=start + 300)

    assert detected["accepted"] is True
    assert detected["gestureCode"] == "Swipe_Left"
    assert detected["triggered"] is True
    assert detected["systemConfidenceThreshold"] == 0.90


def test_swipe_does_not_wait_for_static_open_palm_confirmation() -> None:
    recognizer = MediaPipeSystemGestureRecognizer()
    start = 26_000.0
    first = recognizer.process(_payload(0.40, "Open_Palm"), now_ms=start)
    middle = recognizer.process(_payload(0.43, "Open_Palm"), now_ms=start + 150)
    detected = recognizer.process(_payload(0.46, "Open_Palm"), now_ms=start + 300)

    assert first["pending"] is True
    assert middle.get("gestureCode") != "Swipe_Left"
    assert detected["gestureCode"] == "Swipe_Left"
    assert detected["triggered"] is True


def test_dynamic_gestures_require_mediapipe_open_palm_not_geometry_fallback() -> None:
    recognizer = MediaPipeSystemGestureRecognizer()
    start = 27_000.0
    recognizer.process(_geometry_open_payload(0.40), now_ms=start)
    recognizer.process(_geometry_open_payload(0.44), now_ms=start + 150)
    detected = recognizer.process(_geometry_open_payload(0.48), now_ms=start + 300)

    assert detected["accepted"] is False
    assert detected.get("gestureCode") not in {"Swipe_Left", "Swipe_Right", "Waving"}


def test_open_palm_with_direction_reversal_is_wave() -> None:
    recognizer = MediaPipeSystemGestureRecognizer()
    start = 30_000.0
    samples = ((0, 0.50), (150, 0.60), (300, 0.52), (450, 0.42), (600, 0.52))
    detected = None
    for offset, x in samples:
        detected = recognizer.process(_payload(x, "Open_Palm"), now_ms=start + offset)

    assert detected is not None
    assert detected["gestureCode"] == "Waving"
    assert detected["triggered"] is True
    assert detected["stableHoldMs"] == 600


def test_small_open_palm_reversal_is_sensitive_enough_for_wave() -> None:
    recognizer = MediaPipeSystemGestureRecognizer()
    start = 32_000.0
    samples = ((0, 0.50), (150, 0.595), (300, 0.51), (450, 0.425), (600, 0.51))
    detected = None
    for offset, x in samples:
        detected = recognizer.process(_payload(x, "Open_Palm"), now_ms=start + offset)

    assert detected is not None
    assert detected["gestureCode"] == "Waving"
    assert detected["score"] >= 0.90


def test_wave_overrides_a_swipe_candidate_when_direction_reverses_during_stability() -> None:
    recognizer = MediaPipeSystemGestureRecognizer()
    start = 35_000.0
    recognizer.process(_payload(0.40, "Open_Palm"), now_ms=start)
    recognizer.process(_payload(0.47, "Open_Palm"), now_ms=start + 150)
    swipe = recognizer.process(_payload(0.55, "Open_Palm"), now_ms=start + 300)
    recognizer.process(_payload(0.45, "Open_Palm"), now_ms=start + 450)
    wave = recognizer.process(_payload(0.35, "Open_Palm"), now_ms=start + 600)

    assert swipe["gestureCode"] == "Swipe_Left"
    assert wave["gestureCode"] == "Waving"
    assert wave["triggered"] is False


def test_open_palm_confirmation_tolerates_none_but_not_another_gesture() -> None:
    recognizer = MediaPipeSystemGestureRecognizer()
    start = 37_000.0
    recognizer.process(_payload(0.5, "Open_Palm", 0.95), now_ms=start)
    pending = None
    for offset in range(150, 1050, 150):
        pending = recognizer.process(_geometry_open_payload(0.5), now_ms=start + offset)
    ready = recognizer.process(_geometry_open_payload(0.5), now_ms=start + 1000)

    assert pending is not None
    assert pending["accepted"] is False
    assert ready["gestureCode"] == "Open_Palm"
    assert ready["accepted"] is True
    assert ready["triggered"] is True

    interrupted = MediaPipeSystemGestureRecognizer()
    interrupted.process(_payload(0.5, "Open_Palm"), now_ms=start)
    for offset in range(150, 1050, 150):
        interrupted.process(_geometry_open_payload(0.5), now_ms=start + offset)
    other = interrupted.process(
        _geometry_open_payload(0.5, "Victory"),
        now_ms=start + 950,
    )
    restarted = interrupted.process(_payload(0.5, "Open_Palm"), now_ms=start + 1000)

    assert other["accepted"] is False
    assert restarted["accepted"] is False
    assert restarted["pending"] is True


def test_open_palm_requires_one_second_while_fist_still_requires_1_2_seconds() -> None:
    open_recognizer = MediaPipeSystemGestureRecognizer()
    fist_recognizer = MediaPipeSystemGestureRecognizer()
    start = 40_000.0

    open_first = open_recognizer.process(_payload(0.5, "Open_Palm"), now_ms=start)
    fist_first = fist_recognizer.process(_payload(0.5, "Closed_Fist"), now_ms=start)
    open_pending = open_first
    for offset in range(150, 1050, 150):
        open_pending = open_recognizer.process(_payload(0.5, "Open_Palm"), now_ms=start + offset)

    fist_ready = fist_first
    fist_triggered = False
    for offset in range(150, 1350, 150):
        fist_ready = fist_recognizer.process(_payload(0.5, "Closed_Fist"), now_ms=start + offset)
        fist_triggered = fist_triggered or fist_ready["triggered"]

    assert open_first["gestureCode"] == "Open_Palm"
    assert open_first["accepted"] is False
    assert open_first["pending"] is True
    assert open_first["triggered"] is False
    assert open_pending["accepted"] is False
    assert open_pending["triggered"] is False
    open_ready = open_recognizer.process(_payload(0.5, "Open_Palm"), now_ms=start + 1000)
    assert open_ready["accepted"] is True
    assert open_ready["pending"] is False
    assert open_ready["triggered"] is True
    assert open_ready["stableHoldMs"] == 1000
    assert fist_first["gestureCode"] == "Closed_Fist"
    assert fist_first["triggered"] is False
    assert fist_triggered is True


def test_open_palm_confirmation_restarts_after_an_interruption() -> None:
    recognizer = MediaPipeSystemGestureRecognizer()
    start = 45_000.0
    for offset in range(0, 1050, 150):
        pending = recognizer.process(_payload(0.5, "Open_Palm"), now_ms=start + offset)
    assert pending["accepted"] is False

    recognizer.process(_payload(0.5, "Closed_Fist"), now_ms=start + 950)
    restarted = recognizer.process(_payload(0.5, "Open_Palm"), now_ms=start + 1050)
    almost_ready = restarted
    for offset in range(1200, 2100, 150):
        almost_ready = recognizer.process(_payload(0.5, "Open_Palm"), now_ms=start + offset)
    ready = recognizer.process(_payload(0.5, "Open_Palm"), now_ms=start + 2050)

    assert restarted["accepted"] is False
    assert almost_ready["accepted"] is False
    assert ready["accepted"] is True
    assert ready["triggered"] is True


def test_open_palm_confirmation_restarts_when_a_sampled_frame_is_missed() -> None:
    recognizer = MediaPipeSystemGestureRecognizer()
    start = 50_000.0
    recognizer.process(_payload(0.5, "Open_Palm"), now_ms=start)
    recognizer.process(_payload(0.5, "Open_Palm"), now_ms=start + 150)

    # 相邻有效帧间隔 300ms，超过 250ms 上限，必须从该帧重新计时。
    restarted = recognizer.process(_payload(0.5, "Open_Palm"), now_ms=start + 450)
    almost_ready = restarted
    for offset in range(600, 1500, 150):
        almost_ready = recognizer.process(_payload(0.5, "Open_Palm"), now_ms=start + offset)
    ready = recognizer.process(_payload(0.5, "Open_Palm"), now_ms=start + 1450)

    assert restarted["accepted"] is False
    assert almost_ready["accepted"] is False
    assert ready["accepted"] is True
    assert ready["triggered"] is True


def test_user_prototype_matching_only_runs_below_system_confidence_threshold(tmp_path) -> None:
    service = GestureRecognitionService(
        tmp_path / "config.json",
        tmp_path / "legacy.json",
        tmp_path / "unused.pt",
        tmp_path / "deep.json",
    )
    runtime = _CountingRuntime()
    service.deep_runtime = runtime
    service.active_algorithm = DINO_ALGORITHM_ID
    service.engine["config"]["activeAlgorithm"] = DINO_ALGORITHM_ID

    high = service.recognize(_payload(0.5, "Open_Palm", 0.99))
    other_payload = _geometry_open_payload(0.5, "Victory")
    low = service.recognize(other_payload)

    assert high["recognition"]["gestureCode"] == "Open_Palm"
    assert high["recognition"]["accepted"] is False
    assert high["recognition"]["pending"] is True
    assert runtime.observe_calls == 1
    assert runtime.process_calls == 1
    assert low["recognition"]["accepted"] is False
    assert low["systemRecognition"]["accepted"] is False


class _CountingRuntime:
    sequence_length = 12
    recording = None

    def __init__(self) -> None:
        self.observe_calls = 0
        self.process_calls = 0

    def observe(self, _payload: dict[str, Any]) -> None:
        self.observe_calls += 1

    def process(self, _payload: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        self.process_calls += 1
        return {
            "algorithm": self.algorithm_state(),
            "recognition": {"accepted": False, "name": "unknown", "score": 0.2, "triggered": False},
            "recording": self.recording_status(),
            "recordingComplete": None,
            "prototypes": [],
            "config": config,
        }

    def algorithm_state(self) -> dict[str, Any]:
        return {"active": DINO_ALGORITHM_ID}

    def recording_status(self) -> dict[str, Any]:
        return {"active": False, "count": 0, "target": self.sequence_length}

    def list_prototypes(self) -> list[dict[str, Any]]:
        return []
