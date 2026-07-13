"""PP-Vehicle 微服务配置。"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

HOST = os.getenv("VEHICLE_ALGORITHM_HOST", "0.0.0.0")
PORT = int(os.getenv("VEHICLE_ALGORITHM_PORT", "8003"))
RELOAD = os.getenv("VEHICLE_ALGORITHM_RELOAD", "0") == "1"
PRELOAD_MODEL = os.getenv("VEHICLE_PRELOAD_MODEL", "0") == "1"

PADDLE_DETECTION_DIR = Path(
    os.getenv("PADDLE_DETECTION_DIR", "/opt/PaddleDetection")
).expanduser()
MOT_MODEL_DIR = os.getenv("PPVEHICLE_MOT_MODEL_DIR", "/models/ppvehicle/mot")
ATTR_MODEL_DIR = os.getenv("PPVEHICLE_ATTR_MODEL_DIR", "/models/ppvehicle/attr")
TRACKER_CONFIG = Path(
    os.getenv(
        "PPVEHICLE_TRACKER_CONFIG",
        str(BASE_DIR / "config/tracker_config.yml"),
    )
).expanduser()

DEVICE = os.getenv("PPVEHICLE_DEVICE", "CPU").upper()
RUN_MODE = os.getenv("PPVEHICLE_RUN_MODE", "paddle")
CPU_THREADS = max(1, int(os.getenv("PPVEHICLE_CPU_THREADS", "4")))
ENABLE_MKLDNN = os.getenv("PPVEHICLE_ENABLE_MKLDNN", "1") == "1"
MOT_SKIP_FRAME_NUM = max(1, int(os.getenv("PPVEHICLE_SKIP_FRAME_NUM", "1")))
STREAM_EVERY_N_FRAMES = max(1, int(os.getenv("VEHICLE_STREAM_EVERY_N_FRAMES", "1")))
TYPE_THRESHOLD = float(os.getenv("PPVEHICLE_TYPE_THRESHOLD", "0.7"))
COLOR_THRESHOLD = float(os.getenv("PPVEHICLE_COLOR_THRESHOLD", "0.5"))
ATTRIBUTE_HISTORY = max(1, int(os.getenv("PPVEHICLE_ATTRIBUTE_HISTORY", "12")))
MAX_BOX_AREA_RATIO = min(
    1.0,
    max(0.1, float(os.getenv("PPVEHICLE_MAX_BOX_AREA_RATIO", "0.9"))),
)

MAX_UPLOAD_BYTES = int(os.getenv("VEHICLE_MAX_UPLOAD_BYTES", str(500 * 1024 * 1024)))
DOWNLOAD_TIMEOUT_SECONDS = float(os.getenv("VEHICLE_DOWNLOAD_TIMEOUT_SECONDS", "30"))
WORK_DIR = Path(os.getenv("VEHICLE_WORK_DIR", "/tmp/visiondrive-vehicle")).expanduser()
_default_roots = f"{WORK_DIR},/shared,/app/uploads"
ALLOWED_MEDIA_ROOTS = tuple(
    Path(item.strip()).expanduser().resolve()
    for item in os.getenv(
        "VEHICLE_ALLOWED_MEDIA_ROOTS",
        os.getenv("VEHICLE_ALLOWED_VIDEO_ROOTS", _default_roots),
    ).split(",")
    if item.strip()
)
ALLOWED_VIDEO_ROOTS = ALLOWED_MEDIA_ROOTS

ALLOWED_ORIGINS = tuple(
    item.strip()
    for item in os.getenv("VEHICLE_ALLOWED_ORIGINS", "*").split(",")
    if item.strip()
)

SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
