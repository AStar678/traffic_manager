"""算法服务配置管理"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

HOST = os.getenv("ALGORITHM_HOST", "0.0.0.0")
PORT = int(os.getenv("ALGORITHM_PORT", 8000))

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
TRAINING_ROOT = PROJECT_ROOT.parent.parent

# 模型路径
LICENSE_PLATE_SOURCE_DIR = Path(os.getenv(
    "LICENSE_PLATE_SOURCE_DIR",
    str(TRAINING_ROOT / "车牌识别")
))
CLPRNET_SOURCE_DIR = Path(os.getenv(
    "CLPRNET_SOURCE",
    str(LICENSE_PLATE_SOURCE_DIR / "CLPRNet-main")
))
CLPRNET_MODEL_PATH = Path(os.getenv(
    "CLPRNET_MODEL",
    str(CLPRNET_SOURCE_DIR / "resource" / "CLPRNet.pth")
))

GESTURE_RECOGNITION_APP_DIR = Path(os.getenv(
    "GESTURE_RECOGNITION_APP_DIR",
    str(BASE_DIR / "gesture_recognition_app")
))
GESTURE_CONFIG_PATH = Path(os.getenv(
    "GESTURE_CONFIG_PATH",
    str(GESTURE_RECOGNITION_APP_DIR / "config" / "gesture-config.json")
))
GESTURE_PROTOTYPE_STORE = Path(os.getenv(
    "GESTURE_PROTOTYPE_STORE",
    str(BASE_DIR / "data" / "gesture_prototypes.json")
))

OUTPUT_DIR = Path(os.getenv("ALGORITHM_OUTPUT_DIR", str(BASE_DIR / "outputs")))

# LLM API
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")

# Java后端回调地址
CALLBACK_BASE_URL = os.getenv("CALLBACK_BASE_URL", "http://localhost:8080/internal/api/v1/algorithm/events")
