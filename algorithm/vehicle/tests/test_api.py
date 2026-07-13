import json
from pathlib import Path

from fastapi.testclient import TestClient

from vehicle import main


class FakeRuntime:
    status = {
        "ready": True,
        "mode": "ppvehicle",
        "device": "CPU",
        "runMode": "paddle",
        "message": "ready",
    }

    def ensure_ready(self):
        return None

    def analyze_video(self, source):
        assert Path(source).is_file()
        yield {
            "event": "meta",
            "video": {"width": 1280, "height": 720, "fps": 25, "frameCount": 1},
        }
        yield {
            "event": "frame",
            "frameIndex": 0,
            "timestampMs": 0,
            "detectionCount": 1,
            "detections": [{"trackId": 9, "vehicleType": "suv"}],
        }
        yield {
            "event": "complete",
            "summary": {"processedFrames": 1, "uniqueVehicleCount": 1},
        }

    def analyze_image(self, source, source_id):
        assert Path(source).is_file()
        assert source_id == "camera-slot-1"
        return {
            "taskType": "vehicle_type",
            "image": {"width": 640, "height": 360},
            "detections": [{"trackId": 3, "vehicleType": "suv"}],
            "detectionCount": 1,
        }


def test_health_and_frontend(monkeypatch):
    monkeypatch.setattr(main, "_runtime", FakeRuntime())
    client = TestClient(main.app)

    health = client.get("/health")
    page = client.get("/")

    assert health.status_code == 200
    assert health.json()["taskType"] == "vehicle_type"
    assert page.status_code == 200
    assert "PP-Vehicle" in page.text


def test_upload_returns_ndjson_stream(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "_runtime", FakeRuntime())
    monkeypatch.setattr(main.config, "WORK_DIR", tmp_path)
    client = TestClient(main.app)

    response = client.post(
        "/api/v1/inference/video/upload",
        files={"file": ("road.mp4", b"fake-video", "video/mp4")},
    )
    events = [json.loads(line) for line in response.text.splitlines()]

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-ndjson")
    assert [item["event"] for item in events] == ["meta", "frame", "complete"]
    assert events[1]["detections"][0]["trackId"] == 9
    assert not list(tmp_path.glob("upload-*"))


def test_upload_rejects_unsupported_extension(monkeypatch):
    monkeypatch.setattr(main, "_runtime", FakeRuntime())
    client = TestClient(main.app)

    response = client.post(
        "/api/v1/inference/video/upload",
        files={"file": ("notes.txt", b"not-video", "text/plain")},
    )

    assert response.status_code == 400


def test_json_path_is_validated_before_model_load(monkeypatch, tmp_path):
    runtime = FakeRuntime()
    monkeypatch.setattr(main, "_runtime", runtime)
    monkeypatch.setattr(main.config, "ALLOWED_VIDEO_ROOTS", (tmp_path.resolve(),))
    client = TestClient(main.app)

    response = client.post(
        "/api/v1/inference/video",
        json={"task_type": "vehicle_type", "video_path": str(tmp_path / "missing.mp4")},
    )

    assert response.status_code == 400
    assert "不存在" in response.json()["detail"]


def test_image_endpoint_returns_standard_envelope(monkeypatch, tmp_path):
    image = tmp_path / "camera-1.jpg"
    image.write_bytes(b"fake-image")
    monkeypatch.setattr(main, "_runtime", FakeRuntime())
    monkeypatch.setattr(main.config, "ALLOWED_MEDIA_ROOTS", (tmp_path.resolve(),))
    client = TestClient(main.app)

    response = client.post(
        "/api/v1/inference/image",
        json={
            "taskType": "vehicle_type",
            "imagePath": str(image),
            "sourceId": "camera-slot-1",
        },
    )

    assert response.status_code == 200
    assert response.json()["data"]["detections"][0]["trackId"] == 3
