"""交警手势识别管线回归测试。"""
from __future__ import annotations

import base64
import io

import numpy as np
from PIL import Image

from services.police_gesture.pipeline import PoliceGesturePipeline


def test_pipeline_reports_missing_model_without_rejecting_image(tmp_path):
    pipeline = PoliceGesturePipeline({"source_dir": tmp_path})
    image_url = _image_data_url()

    result = pipeline.process(image_url)

    assert result["image"] == {"width": 32, "height": 24}
    assert result["detections"] == []
    assert result["detectionCount"] == 0
    assert result["modelStatus"]["ready"] is False
    assert "未找到交警识别源码目录" in result["modelStatus"]["message"]


def test_softmax_and_gesture_mapping_are_complete():
    probabilities = PoliceGesturePipeline._softmax(np.arange(9, dtype=float))

    assert np.isclose(probabilities.sum(), 1.0)
    assert len(PoliceGesturePipeline.GESTURE_MAP) == 9
    assert PoliceGesturePipeline.GESTURE_MAP[1][0] == "STOP"
    assert PoliceGesturePipeline.GESTURE_MAP[8][0] == "PULL_OVER"


def test_keypoints_support_model_coordinate_layout(tmp_path):
    pipeline = PoliceGesturePipeline({"source_dir": tmp_path})
    coords = np.full((2, 14), 0.5, dtype=float)

    keypoints = pipeline._keypoints(coords, width=1280, height=720)

    assert len(keypoints) == 14
    assert keypoints[0]["name"] == "right_shoulder"
    assert keypoints[0]["x"] == 640
    assert keypoints[0]["y"] == 360


def test_sample_reference_uses_camera_source_and_frame_index(tmp_path):
    coord_dir = tmp_path / "generated" / "coords" / "test"
    coord_dir.mkdir(parents=True)
    (coord_dir / "004.pkl").write_bytes(b"placeholder")
    pipeline = PoliceGesturePipeline({"source_dir": tmp_path})

    reference = pipeline._sample_reference(
        "http://127.0.0.1:8010/api/v1/cameras/snapshot.png"
        "?sourceId=police-gesture-004&frameIndex=3124&captureTs=123"
    )

    assert reference == ("004", 3124)


def test_stable_predictions_reduce_single_frame_noise():
    labels = np.asarray([2, 2, 2, 0, 2], dtype=np.int16)

    stable = PoliceGesturePipeline._stable_predictions(labels, window=5)

    assert stable.tolist() == [2, 2, 2, 2, 2]


def test_pipeline_keeps_skeleton_when_no_gesture_is_detected(tmp_path):
    class FakePG:
        OUT_ARGMAX = "label"
        OUT_SCORES = "scores"
        COORD_NORM = "coordinates"

    class FakePredictor:
        def from_img(self, _image):
            return {
                "label": 0,
                "scores": np.asarray([8.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
                "coordinates": np.full((2, 14), 0.5, dtype=float),
            }

    pipeline = PoliceGesturePipeline({"source_dir": tmp_path})
    pipeline.PG = FakePG
    pipeline.predictor = FakePredictor()

    result = pipeline.process(_image_data_url())

    assert result["detectionCount"] == 1
    assert result["detections"][0]["gestureCode"] is None
    assert result["detections"][0]["gestureName"] == "无手势"
    assert len(result["detections"][0]["keypoints"]) == 14


def _image_data_url() -> str:
    buffer = io.BytesIO()
    Image.new("RGB", (32, 24), color=(8, 12, 20)).save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"
