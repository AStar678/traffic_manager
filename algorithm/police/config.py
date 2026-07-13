"""交警手势识别服务配置。"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ALGORITHM_ROOT = BASE_DIR.parent
PROJECT_ROOT = ALGORITHM_ROOT.parent
TRAINING_ROOT = PROJECT_ROOT.parent.parent

load_dotenv(BASE_DIR / ".env")

HOST = os.getenv("POLICE_ALGORITHM_HOST", os.getenv("ALGORITHM_HOST", "0.0.0.0"))
PORT = int(os.getenv("POLICE_ALGORITHM_PORT", "8001"))
WORKERS = max(1, int(os.getenv("POLICE_ALGORITHM_WORKERS", "1")))
RELOAD = os.getenv("POLICE_ALGORITHM_RELOAD", os.getenv("ALGORITHM_RELOAD", "0")) == "1"
SOURCE_DIR = Path(os.getenv("POLICE_GESTURE_SOURCE_DIR", str(TRAINING_ROOT / "交警指令识别")))
POSE_INPUT_SIZE = max(128, int(os.getenv("POLICE_POSE_INPUT_SIZE", "512")))
TEMPORAL_STEPS = max(1, int(os.getenv("POLICE_TEMPORAL_STEPS", "15")))
