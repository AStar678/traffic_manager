from pathlib import Path

import pytest

from vehicle import config
from vehicle.sources import validate_local_video


def test_validate_local_video_accepts_shared_file(monkeypatch, tmp_path):
    video = tmp_path / "road.mp4"
    video.write_bytes(b"video")
    monkeypatch.setattr(config, "ALLOWED_VIDEO_ROOTS", (tmp_path.resolve(),))

    assert validate_local_video(str(video)) == video.resolve()


def test_validate_local_video_rejects_path_outside_roots(monkeypatch, tmp_path):
    video = tmp_path / "road.mp4"
    video.write_bytes(b"video")
    monkeypatch.setattr(config, "ALLOWED_VIDEO_ROOTS", (Path("/shared").resolve(),))

    with pytest.raises(ValueError, match="不在允许目录"):
        validate_local_video(str(video))
