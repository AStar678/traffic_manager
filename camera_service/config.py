"""Runtime settings for the virtual camera microservice."""

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

LICENSE_PLATE_SAMPLE_DIR = COURSE_ROOT / "车牌识别" / "image"
POLICE_GESTURE_SAMPLE_DIR = COURSE_ROOT / "交警指令识别" / "test"
OWNER_GESTURE_SOURCE_DIR = COURSE_ROOT / "手势识别"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
