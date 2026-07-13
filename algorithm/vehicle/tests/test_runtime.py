from collections import deque
from types import SimpleNamespace

from vehicle import config
from vehicle.runtime import MultiSourceIoUTracker, PPVehicleRuntime, TrackAttributeSmoother


def test_runtime_status_exposes_vehicle_type_threshold(monkeypatch):
    monkeypatch.setattr(config, "TYPE_THRESHOLD", 0.7)

    status = PPVehicleRuntime().status

    assert status["thresholds"]["vehicleType"] == 0.7


def test_parse_attributes_uses_official_ppvehicle_output():
    vehicle_type, color = PPVehicleRuntime._parse_attributes(
        ["Color: black", "Type: suv"]
    )

    assert vehicle_type == "suv"
    assert color == "black"


def test_track_attribute_smoother_keeps_majority_label():
    smoother = TrackAttributeSmoother(history_size=5)

    smoother.update(7, 1, "suv", "black")
    smoother.update(7, 2, "suv", "black")
    vehicle_type, color = smoother.update(7, 3, "sedan", "white")

    assert vehicle_type == "suv"
    assert color == "black"
    assert isinstance(smoother._types[7], deque)


def test_track_attribute_smoother_ignores_unknown_votes():
    smoother = TrackAttributeSmoother(history_size=3)

    smoother.update(12, 1, "truck", "red")
    vehicle_type, color = smoother.update(12, 2, "unknown", "unknown")

    assert vehicle_type == "truck"
    assert color == "red"


def test_multi_source_tracker_keeps_ids_separate_and_stable():
    tracker = MultiSourceIoUTracker()
    first = {"bbox": {"x1": 10, "y1": 10, "x2": 100, "y2": 80}, "vehicleType": "suv", "vehicleColor": "black"}
    moved = {"bbox": {"x1": 14, "y1": 12, "x2": 104, "y2": 82}, "vehicleType": "sedan", "vehicleColor": "white"}

    cam1_first = tracker.update("camera-1", [first])[0]
    cam1_next = tracker.update("camera-1", [moved])[0]
    cam2_first = tracker.update("camera-2", [first])[0]

    assert cam1_first["trackId"] == cam1_next["trackId"] == 1
    assert cam2_first["trackId"] == 1
    assert cam1_next["objectId"].startswith("camera-1-")
    assert cam2_first["objectId"].startswith("camera-2-")
    assert cam1_next["vehicleType"] == "suv"


def test_reset_tracker_clears_ocsort_state_without_reset_method():
    runtime = PPVehicleRuntime()
    tracker = SimpleNamespace(trackers=[object()], frame_count=18)
    mot_predictor = SimpleNamespace(
        tracker=tracker,
        previous_det_result={"boxes": [1]},
    )
    runtime._predictor = SimpleNamespace(mot_predictor=mot_predictor)

    runtime._reset_tracker_if_supported()

    assert tracker.trackers == []
    assert tracker.frame_count == 0
    assert mot_predictor.previous_det_result is None


def test_filter_mot_boxes_rejects_full_frame_false_positive():
    normal = [1, 0, 0.92, 100, 80, 420, 360]
    full_frame = [2, 0, 0.55, 0, 0, 1275, 719]
    invalid = [3, 0, 0.8, 50, 50, 50, 100]

    filtered = PPVehicleRuntime._filter_mot_boxes(
        [normal, full_frame, invalid],
        image_width=1280,
        image_height=720,
        max_area_ratio=0.9,
    )

    assert filtered == [normal]
