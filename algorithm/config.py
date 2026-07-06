"""算法服务配置管理"""
import os
from dotenv import load_dotenv

load_dotenv()

HOST = os.getenv("ALGORITHM_HOST", "0.0.0.0")
PORT = int(os.getenv("ALGORITHM_PORT", 8000))

# 模型路径
LICENSE_PLATE_MODEL_PATH = os.getenv("LICENSE_PLATE_MODEL_PATH", "./models/license_plate/yolov8n.pt")
OCR_MODEL_DIR = os.getenv("OCR_MODEL_DIR", "./models/license_plate/ocr/")
POSE_MODEL_PATH = os.getenv("POSE_MODEL_PATH", "./models/police_gesture/")
HAND_MODEL_PATH = os.getenv("HAND_MODEL_PATH", "./models/owner_gesture/")

# LLM API
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")

# Java后端回调地址
CALLBACK_BASE_URL = os.getenv("CALLBACK_BASE_URL", "http://localhost:8080/internal/api/v1/algorithm/events")
