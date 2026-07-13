"""交警手势识别管线回归测试。"""
from __future__ import annotations

import base64
import io

import numpy as np
from PIL import Image

from police.pipeline import PoliceGesturePipeline


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


def test_streams_keep_independent_lstm_state(tmp_path):
    import torch

    class FakePG:
        OUT_ARGMAX = "label"
        OUT_SCORES = "scores"
        COORD_NORM = "coordinates"

    class FakeModel:
        batch = 1
        num_hidden = 1
        device = torch.device("cpu")

    class FakePredictor:
        def __init__(self):
            self.g_model = FakeModel()
            self.h = torch.zeros((1, 1, 1))
            self.c = torch.zeros((1, 1, 1))

        def from_img(self, _image):
            label = int(self.h.item())
            self.h = self.h + 1
            self.c = self.c + 1
            return {
                "label": label,
                "scores": np.arange(9, dtype=float),
                "coordinates": np.full((2, 14), 0.5, dtype=float),
            }

    pipeline = PoliceGesturePipeline({"source_dir": tmp_path})
    pipeline.PG = FakePG
    pipeline.predictor = FakePredictor()
    image = np.zeros((8, 8, 3), dtype=np.uint8)

    first_a = pipeline._predict_stream_frame(image, "camera-slot-1")
    second_a = pipeline._predict_stream_frame(image, "camera-slot-1")
    first_b = pipeline._predict_stream_frame(image, "camera-slot-2")

    assert first_a["label"] == 0
    assert second_a["label"] == 1
    assert first_b["label"] == 0


def test_pose_preprocessing_preserves_landscape_coordinates(tmp_path):
    pipeline = PoliceGesturePipeline({"source_dir": tmp_path, "pose_input_size": 512})
    image = np.zeros((720, 1280, 3), dtype=np.uint8)

    resized, transform = pipeline._resize_pose_input(image)
    restored = pipeline._restore_coordinates(
        np.asarray([[0.5, 0.0], [0.5, 112 / 512]], dtype=np.float32),
        transform,
    )

    assert resized.shape == (512, 512, 3)
    assert np.allclose(restored[:, 0], [0.5, 0.5])
    assert np.allclose(restored[:, 1], [0.0, 0.0])


def _image_data_url() -> str:
    buffer = io.BytesIO()
    Image.new("RGB", (32, 24), color=(8, 12, 20)).save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"
