"""车牌识别服务配置。"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ALGORITHM_ROOT = BASE_DIR.parent
PROJECT_ROOT = ALGORITHM_ROOT.parent
TRAINING_ROOT = PROJECT_ROOT.parent.parent

load_dotenv(BASE_DIR / ".env")

HOST = os.getenv("LICENSE_ALGORITHM_HOST", os.getenv("ALGORITHM_HOST", "0.0.0.0"))
PORT = int(os.getenv("LICENSE_ALGORITHM_PORT", "8000"))
WORKERS = max(1, int(os.getenv("LICENSE_ALGORITHM_WORKERS", "2")))
RELOAD = os.getenv("LICENSE_ALGORITHM_RELOAD", os.getenv("ALGORITHM_RELOAD", "0")) == "1"

SOURCE_DIR = Path(os.getenv("LICENSE_PLATE_SOURCE_DIR", str(TRAINING_ROOT / "车牌识别")))
CLPRNET_SOURCE_DIR = Path(os.getenv("CLPRNET_SOURCE", str(SOURCE_DIR / "CLPRNet-main")))
CLPRNET_MODEL_PATH = Path(
    os.getenv("CLPRNET_MODEL", str(CLPRNET_SOURCE_DIR / "resource" / "CLPRNet.pth"))
)
