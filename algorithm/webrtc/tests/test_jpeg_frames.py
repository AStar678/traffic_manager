"""Regression tests for stateless JPEG camera transport."""
from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

import numpy as np
from PIL import Image

from webrtc import config
from webrtc import jpeg_frames
from webrtc.jpeg_frames import JpegFrameRenderer
from webrtc.processed_video import ProcessedResultStore


def test_raw_display_jpeg_is_720_by_480_without_changing_source(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DISPLAY_WIDTH", 720)
    monkeypatch.setattr(config, "DISPLAY_HEIGHT", 480)
    source = tmp_path / "camera-1.jpg"
    Image.new("RGB", (1920, 1080), color=(20, 40, 60)).save(source, quality=100)

    rendered = JpegFrameRenderer(tmp_path).raw(source)

    with Image.open(BytesIO(rendered.payload)) as display:
        assert display.size == (720, 480)
    with Image.open(source) as original:
        assert original.size == (1920, 1080)
    assert rendered.source == "raw"


def test_preencoded_display_jpeg_is_served_without_reencoding(tmp_path):
    source = tmp_path / "camera-1.display.jpg"
    payload = b"already-encoded-display-jpeg"
    source.write_bytes(payload)

    rendered = JpegFrameRenderer(tmp_path).preencoded(source)

    assert rendered.payload == payload
    assert rendered.frame_id.startswith("display-")
    assert rendered.source == "raw"


def test_processed_jpeg_uses_exact_inference_snapshot_and_backend_boxes(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DISPLAY_WIDTH", 720)
    monkeypatch.setattr(config, "DISPLAY_HEIGHT", 480)
    inference_dir = tmp_path / "inference"
    result_dir = tmp_path / "processed-results"
    inference_dir.mkdir()
    result_dir.mkdir()
    exact = inference_dir / "camera-1-exact.jpg"
    fallback = tmp_path / "camera-1.jpg"
    Image.new("RGB", (1280, 720), color=(12, 12, 12)).save(exact, quality=100)
    Image.new("RGB", (1280, 720), color=(220, 220, 220)).save(fallback, quality=100)
    (result_dir / "license_plate-camera-1.json").write_text(json.dumps({
        "taskType": "license_plate",
        "slotId": 1,
        "frameId": "1-90000-exact",
        "framePts": 90_000,
        "frameTimeBase": "1/90000",
        "framePath": str(exact),
        "image": {"width": 1280, "height": 720},
        "detections": [{
            "plateNumber": "TEST123",
            "confidence": 0.99,
            "bbox": {"x1": 160, "y1": 120, "x2": 640, "y2": 360},
        }],
    }), encoding="utf-8")
    snapshot = ProcessedResultStore(tmp_path).latest(1, "license_plate")

    rendered = JpegFrameRenderer(tmp_path).processed(
        1, "license_plate", snapshot, fallback
    )

    with Image.open(BytesIO(rendered.payload)) as display:
        pixels = np.asarray(display.convert("RGB"))
        assert display.size == (720, 480)
        assert pixels.mean() < 80
        assert np.any(pixels != pixels[240, 360])
    assert rendered.frame_id == "1-90000-exact"
    assert rendered.source == "processed"


def test_processed_jpeg_rejects_snapshot_outside_inference_directory(tmp_path):
    result_dir = tmp_path / "processed-results"
    result_dir.mkdir()
    fallback = tmp_path / "camera-1.jpg"
    untrusted = tmp_path / "outside.jpg"
    Image.new("RGB", (640, 360), color=(80, 90, 100)).save(fallback)
    Image.new("RGB", (640, 360), color=(200, 10, 10)).save(untrusted)
    (result_dir / "vehicle_type-camera-1.json").write_text(json.dumps({
        "taskType": "vehicle_type",
        "slotId": 1,
        "frameId": "untrusted",
        "framePath": str(untrusted),
        "image": {"width": 640, "height": 360},
        "detections": [],
    }), encoding="utf-8")
    snapshot = ProcessedResultStore(tmp_path).latest(1, "vehicle_type")

    rendered = JpegFrameRenderer(tmp_path).processed(
        1, "vehicle_type", snapshot, fallback
    )

    assert rendered.source == "waiting"
    assert rendered.frame_id.startswith("waiting-")


def test_different_camera_slots_encode_concurrently(tmp_path, monkeypatch):
    first = tmp_path / "camera-1.jpg"
    second = tmp_path / "camera-2.jpg"
    Image.new("RGB", (1280, 720), color=(10, 20, 30)).save(first)
    Image.new("RGB", (1280, 720), color=(40, 50, 60)).save(second)
    render_barrier = threading.Barrier(2)

    def synchronized_encode(_image):
        render_barrier.wait(timeout=2)
        return b"jpeg"

    monkeypatch.setattr(jpeg_frames, "_encode_canvas", synchronized_encode)
    renderer = JpegFrameRenderer(tmp_path)
    with ThreadPoolExecutor(max_workers=2) as executor:
        rendered = list(executor.map(renderer.raw, (first, second)))

    assert [item.payload for item in rendered] == [b"jpeg", b"jpeg"]
