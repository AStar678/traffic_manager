"""WebRTC camera transport configuration."""
from __future__ import annotations

import os
from pathlib import Path

HOST = os.getenv("WEBRTC_HOST", "0.0.0.0")
PORT = int(os.getenv("WEBRTC_PORT", "8003"))
STUN_HOST = os.getenv("WEBRTC_STUN_HOST", "0.0.0.0")
STUN_PORT = int(os.getenv("WEBRTC_STUN_PORT", "3478"))
PUBLIC_HOST = os.getenv("WEBRTC_PUBLIC_HOST", "127.0.0.1")
TURN_PORT = int(os.getenv("WEBRTC_TURN_PORT", "3478"))
TURN_SECRET = os.getenv("WEBRTC_TURN_SECRET", "")
TURN_TTL_SECONDS = max(300, int(os.getenv("WEBRTC_TURN_TTL_SECONDS", "3600")))
TURN_FORCE_RELAY = os.getenv("WEBRTC_TURN_FORCE_RELAY", "true").lower() in {"1", "true", "yes", "on"}
CAMERA_STATE_FILE = Path(os.getenv("WEBRTC_CAMERA_STATE_FILE", os.getenv("CAMERA_STATE_FILE", "./data/camera-slots.json")))
CAMERA_FRAME_DIR = Path(os.getenv("CAMERA_FRAME_DIR", "./uploads/camera-frames"))
FRAME_PUBLISH_FPS = max(1.0, float(os.getenv("WEBRTC_FRAME_PUBLISH_FPS", "4")))
SANDBOX_BASE_URL = os.getenv("CAMERA_SANDBOX_BASE_URL", "rtsp://10.126.59.120:8554/live").rstrip("/")
PRESERVE_SOURCE_RESOLUTION = os.getenv("WEBRTC_PRESERVE_SOURCE_RESOLUTION", "true").lower() in {
    "1", "true", "yes", "on",
}
FALLBACK_WIDTH = max(
    320,
    int(os.getenv("WEBRTC_FALLBACK_WIDTH", os.getenv("WEBRTC_MAX_WIDTH", "1280"))),
)
FALLBACK_HEIGHT = max(
    240,
    int(os.getenv("WEBRTC_FALLBACK_HEIGHT", os.getenv("WEBRTC_MAX_HEIGHT", "720"))),
)
OUTPUT_FPS = max(5, int(os.getenv("WEBRTC_OUTPUT_FPS", "15")))
FRAME_READ_TIMEOUT_SECONDS = max(1.0, float(os.getenv("WEBRTC_FRAME_READ_TIMEOUT_SECONDS", "5")))
PROBE_TIMEOUT_SECONDS = max(1.0, float(os.getenv("WEBRTC_PROBE_TIMEOUT_SECONDS", "10")))
SNAPSHOT_JPEG_QUALITY = max(90, min(100, int(os.getenv("WEBRTC_SNAPSHOT_JPEG_QUALITY", "100"))))
FFMPEG_BINARY = os.getenv("WEBRTC_FFMPEG_BINARY", "ffmpeg")
FFPROBE_BINARY = os.getenv("WEBRTC_FFPROBE_BINARY", "ffprobe")
