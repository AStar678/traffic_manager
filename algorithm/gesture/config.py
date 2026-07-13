"""车主手势识别服务配置。"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ALGORITHM_ROOT = BASE_DIR.parent
load_dotenv(BASE_DIR / ".env")

HOST = os.getenv("GESTURE_ALGORITHM_HOST", os.getenv("ALGORITHM_HOST", "0.0.0.0"))
PORT = int(os.getenv("GESTURE_ALGORITHM_PORT", "8002"))
# 该服务维护录入会话与车辆状态，必须保持单进程；并发请求由线程池处理。
WORKERS = 1
THREADS = max(1, int(os.getenv("GESTURE_ALGORITHM_THREADS", "40")))
RELOAD = os.getenv("GESTURE_ALGORITHM_RELOAD", os.getenv("ALGORITHM_RELOAD", "0")) == "1"

GESTURE_CONFIG_PATH = Path(
    os.getenv("GESTURE_CONFIG_PATH", str(BASE_DIR / "config" / "gesture-config.json"))
)
GESTURE_PROTOTYPE_STORE = Path(
    os.getenv("GESTURE_PROTOTYPE_STORE", str(BASE_DIR / "data" / "gesture_prototypes.json"))
)
DINO_GESTURE_DIR = ALGORITHM_ROOT / "gesture_dinov2_tcn"
DINO_GESTURE_CHECKPOINT = Path(
    os.getenv("GESTURE_DINOV2_CHECKPOINT", str(DINO_GESTURE_DIR / "checkpoints" / "best_model.pt"))
)
DINO_GESTURE_PROTOTYPE_STORE = Path(
    os.getenv(
        "GESTURE_DINOV2_PROTOTYPE_STORE",
        str(DINO_GESTURE_DIR / "data" / "gesture_prototypes.json"),
    )
)
