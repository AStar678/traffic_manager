"""WebRTC camera transport configuration."""
from __future__ import annotations

import os
from pathlib import Path

CPU_COUNT = os.cpu_count() or 4

HOST = os.getenv("WEBRTC_HOST", "0.0.0.0")
PORT = int(os.getenv("WEBRTC_PORT", "8003"))
ENABLE_WEBRTC = os.getenv("WEBRTC_ENABLED", "false").lower() in {"1", "true", "yes", "on"}
STUN_HOST = os.getenv("WEBRTC_STUN_HOST", "0.0.0.0")
STUN_PORT = int(os.getenv("WEBRTC_STUN_PORT", "3478"))
PUBLIC_HOST = os.getenv("WEBRTC_PUBLIC_HOST", "127.0.0.1")
TURN_PORT = int(os.getenv("WEBRTC_TURN_PORT", "3478"))
TURN_SECRET = os.getenv("WEBRTC_TURN_SECRET", "")
TURN_TTL_SECONDS = max(300, int(os.getenv("WEBRTC_TURN_TTL_SECONDS", "3600")))
TURN_FORCE_RELAY = os.getenv("WEBRTC_TURN_FORCE_RELAY", "true").lower() in {"1", "true", "yes", "on"}
TURN_TCP_ONLY = os.getenv("WEBRTC_TURN_TCP_ONLY", "true").lower() in {"1", "true", "yes", "on"}
CAMERA_STATE_FILE = Path(os.getenv("WEBRTC_CAMERA_STATE_FILE", os.getenv("CAMERA_STATE_FILE", "./data/camera-slots.json")))
CAMERA_FRAME_DIR = Path(os.getenv("CAMERA_FRAME_DIR", "./uploads/camera-frames"))
JPEG_TARGET_FPS = max(20, int(os.getenv("JPEG_TARGET_FPS", "25")))
JPEG_ENCODER_WORKERS = max(
    3,
    min(
        32,
        int(os.getenv("JPEG_ENCODER_WORKERS", str(min(12, max(6, CPU_COUNT - 4))))),
    ),
)
FRAME_PUBLISH_FPS = max(20.0, float(os.getenv("WEBRTC_FRAME_PUBLISH_FPS", str(JPEG_TARGET_FPS))))
INFERENCE_SNAPSHOT_FPS = max(
    1.0,
    min(
        FRAME_PUBLISH_FPS,
        float(os.getenv("WEBRTC_INFERENCE_SNAPSHOT_FPS", "10")),
    ),
)
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
DISPLAY_WIDTH = max(320, int(os.getenv("WEBRTC_DISPLAY_WIDTH", "720"))) // 2 * 2
DISPLAY_HEIGHT = max(240, int(os.getenv("WEBRTC_DISPLAY_HEIGHT", "480"))) // 2 * 2
JPEG_DISPLAY_QUALITY = max(45, min(92, int(os.getenv("JPEG_DISPLAY_QUALITY", "60"))))
JPEG_FRAME_WAIT_SECONDS = max(1.0, float(os.getenv("JPEG_FRAME_WAIT_SECONDS", "5")))
OUTPUT_FPS = max(20, int(os.getenv("WEBRTC_OUTPUT_FPS", str(JPEG_TARGET_FPS))))
PROCESSED_STREAM_DELAY_MS = max(500, min(8000, int(os.getenv("WEBRTC_PROCESSED_STREAM_DELAY_MS", "1800"))))
PROCESSED_RESULT_MAX_AGE_MS = max(300, int(os.getenv("WEBRTC_PROCESSED_RESULT_MAX_AGE_MS", "1800")))
PROCESSED_RESULT_HISTORY = max(4, int(os.getenv("WEBRTC_PROCESSED_RESULT_HISTORY", "16")))
PROCESSED_FRAME_MATCH_TOLERANCE_MS = max(
    0.0,
    float(os.getenv("WEBRTC_PROCESSED_FRAME_MATCH_TOLERANCE_MS", "2")),
)
PROCESSED_MAX_WIDTH = max(320, int(os.getenv("WEBRTC_PROCESSED_MAX_WIDTH", "1280")))
PROCESSED_MAX_HEIGHT = max(240, int(os.getenv("WEBRTC_PROCESSED_MAX_HEIGHT", "720")))
FRAME_READ_TIMEOUT_SECONDS = max(1.0, float(os.getenv("WEBRTC_FRAME_READ_TIMEOUT_SECONDS", "5")))
PROBE_TIMEOUT_SECONDS = max(1.0, float(os.getenv("WEBRTC_PROBE_TIMEOUT_SECONDS", "10")))
SNAPSHOT_JPEG_QUALITY = max(90, min(100, int(os.getenv("WEBRTC_SNAPSHOT_JPEG_QUALITY", "100"))))
FFMPEG_BINARY = os.getenv("WEBRTC_FFMPEG_BINARY", "ffmpeg")
FFPROBE_BINARY = os.getenv("WEBRTC_FFPROBE_BINARY", "ffprobe")
