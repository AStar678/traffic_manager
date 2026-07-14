"""Regression tests for backend-rendered recognition streams."""
from __future__ import annotations

import asyncio
import json
from fractions import Fraction

import numpy as np
from av import VideoFrame

from webrtc import config
from webrtc.processed_video import ProcessedResultStore, ProcessedVideoTrack, annotate_frame


def _frame(pts: int, color: int = 0) -> VideoFrame:
    frame = VideoFrame.from_ndarray(np.full((48, 64, 3), color, dtype=np.uint8), format="rgb24")
    frame.pts = pts
    frame.time_base = Fraction(1, 90_000)
    return frame


def test_result_store_matches_manifest_to_exact_video_frame(tmp_path):
    result_dir = tmp_path / "processed-results"
    result_dir.mkdir()
    (result_dir / "license_plate-camera-1.json").write_text(json.dumps({
        "taskType": "license_plate",
        "slotId": 1,
        "framePts": 90_000,
        "frameTimeBase": "1/90000",
        "image": {"width": 64, "height": 48},
        "detections": [{
            "objectId": "plate_001",
            "plateNumber": "TEST123",
            "confidence": 0.98,
            "bbox": {"x1": 8, "y1": 12, "x2": 42, "y2": 30},
        }],
    }), encoding="utf-8")
    store = ProcessedResultStore(tmp_path)

    snapshot = store.result_for(1, "license_plate", _frame(90_000))

    assert snapshot is not None
    assert snapshot.frame_pts == 90_000
    assert snapshot.detections[0]["plateNumber"] == "TEST123"


def test_result_store_rejects_stale_box_on_later_video_frame(tmp_path):
    result_dir = tmp_path / "processed-results"
    result_dir.mkdir()
    (result_dir / "license_plate-camera-1.json").write_text(json.dumps({
        "taskType": "license_plate",
        "slotId": 1,
        "framePts": 90_000,
        "frameTimeBase": "1/90000",
        "image": {"width": 64, "height": 48},
        "detections": [{"bbox": {"x1": 8, "y1": 12, "x2": 42, "y2": 30}}],
    }), encoding="utf-8")

    snapshot = ProcessedResultStore(tmp_path).result_for(
        1, "license_plate", _frame(135_000), source_type="VIDEO"
    )

    assert snapshot is None


def test_result_store_keeps_latest_box_for_repeated_static_image(tmp_path):
    result_dir = tmp_path / "processed-results"
    result_dir.mkdir()
    (result_dir / "license_plate-camera-1.json").write_text(json.dumps({
        "taskType": "license_plate",
        "slotId": 1,
        "framePts": 90_000,
        "frameTimeBase": "1/90000",
        "image": {"width": 64, "height": 48},
        "detections": [{
            "plateNumber": "STATIC88",
            "bbox": {"x1": 8, "y1": 12, "x2": 42, "y2": 30},
        }],
    }), encoding="utf-8")

    snapshot = ProcessedResultStore(tmp_path).result_for(
        1, "license_plate", _frame(900_000), source_type="IMAGE"
    )

    assert snapshot is not None
    assert snapshot.detections[0]["plateNumber"] == "STATIC88"


def test_annotation_is_burned_into_video_pixels(tmp_path):
    result_dir = tmp_path / "processed-results"
    result_dir.mkdir()
    (result_dir / "vehicle_type-camera-2.json").write_text(json.dumps({
        "taskType": "vehicle_type",
        "slotId": 2,
        "framePts": 90_000,
        "image": {"width": 64, "height": 48},
        "detections": [{
            "trackId": 7,
            "vehicleTypeName": "SUV",
            "confidence": 0.92,
            "bbox": {"x1": 8, "y1": 12, "x2": 42, "y2": 30},
        }],
    }), encoding="utf-8")
    source = _frame(90_000, color=8)
    snapshot = ProcessedResultStore(tmp_path).result_for(2, "vehicle_type", source)

    rendered = annotate_frame(source, "vehicle_type", snapshot)

    pixels = rendered.to_ndarray(format="rgb24")
    assert rendered.pts == source.pts
    assert np.any(pixels != 8)


def test_processed_track_delays_without_dropping_frame_sequence(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUT_FPS", 10)
    monkeypatch.setattr(config, "PROCESSED_MAX_WIDTH", 64)
    monkeypatch.setattr(config, "PROCESSED_MAX_HEIGHT", 48)

    class Source:
        def __init__(self):
            self.next_pts = 0
            self.stopped = False

        async def recv(self):
            frame = _frame(self.next_pts, color=self.next_pts)
            self.next_pts += 1
            return frame

        def stop(self):
            self.stopped = True

    async def exercise():
        source = Source()
        track = ProcessedVideoTrack(
            source, 1, "police_gesture", ProcessedResultStore(tmp_path), delay_ms=200
        )
        first = await track.recv()
        second = await track.recv()
        assert track.delay_frames == 2
        assert first.pts == 0
        assert second.pts == 9_000
        assert first.time_base == Fraction(1, 90_000)
        assert second.time_base == Fraction(1, 90_000)
        assert source.next_pts == 4
        assert track.diagnostics()["framesSent"] == 2
        assert track.diagnostics()["lastError"] is None
        track.stop()
        assert source.stopped

    asyncio.run(exercise())


def test_processed_track_uses_prewarmed_delay_history(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUT_FPS", 10)
    monkeypatch.setattr(config, "PROCESSED_MAX_WIDTH", 64)
    monkeypatch.setattr(config, "PROCESSED_MAX_HEIGHT", 48)

    class Source:
        def __init__(self):
            self.next_pts = 2

        async def recv(self):
            frame = _frame(self.next_pts)
            self.next_pts += 1
            return frame

        def stop(self):
            pass

    class CaptureStore:
        def __init__(self):
            self.frame_pts = []

        def result_for(self, _slot_id, _task_type, frame, _source_type):
            self.frame_pts.append(frame.pts)
            return None

    async def exercise():
        source = Source()
        store = CaptureStore()
        track = ProcessedVideoTrack(
            source,
            1,
            "vehicle_type",
            store,
            delay_ms=200,
            initial_frames=[_frame(0), _frame(1)],
        )

        await track.recv()

        assert source.next_pts == 3
        assert store.frame_pts == [0]
        assert track.diagnostics()["bufferedFrames"] == 2

    asyncio.run(exercise())


def test_detached_frame_pixels_do_not_share_native_avframe_memory():
    source = _frame(90_000, color=17)

    pixels, pts, time_base = ProcessedVideoTrack.detach_frame(source)
    pixels[0, 0] = 99
    original = source.to_ndarray(format="rgb24")
    compact = ProcessedVideoTrack.compact_pixels(pixels, pts, time_base)

    assert np.all(original[0, 0] == 17)
    assert np.all(compact.to_ndarray(format="rgb24")[0, 0] == 99)
    assert compact.pts == 90_000
    assert compact.time_base == Fraction(1, 90_000)
