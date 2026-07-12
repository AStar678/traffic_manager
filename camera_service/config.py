"""Runtime settings for the virtual camera microservice."""

import os
from pathlib import Path


SERVICE_DIR = Path(__file__).resolve().parent
APP_ROOT = SERVICE_DIR.parent
WORKSPACE_ROOT = APP_ROOT.parent
COURSE_ROOT = WORKSPACE_ROOT.parent
STATE_DIR = SERVICE_DIR / "data"
CAMERA_STATE_FILE = STATE_DIR / "camera_state.json"

HOST = "127.0.0.1"
PORT = 8010
DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 720
DEFAULT_FPS = 15
JPEG_QUALITY = 96

SANDBOX_RTSP_BASE_URL = os.getenv(
    "SANDBOX_RTSP_BASE_URL",
    "rtsp://10.126.59.120:8554/live",
).rstrip("/")
SANDBOX_CAMERAS = (
    ("live1", "桥面"),
    ("live2", "停车场出口"),
    ("live3", "行人检测"),
    ("live4", "消防车识别"),
    ("live5", "桥出口"),
    ("live6", "桥入口"),
    ("live7", "道路2"),
    ("live8", "隧道（事故识别）"),
    ("live9", "隧道（车辆数量）"),
    ("live10", "道路3"),
    ("live11", "停车场入口"),
    ("live12", "道路1"),
)

LICENSE_PLATE_SAMPLE_DIR = COURSE_ROOT / "车牌识别" / "image"
POLICE_GESTURE_SAMPLE_DIR = COURSE_ROOT / "交警指令识别" / "test"
OWNER_GESTURE_SOURCE_DIR = COURSE_ROOT / "手势识别"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
