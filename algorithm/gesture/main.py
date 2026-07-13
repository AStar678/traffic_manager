"""VisionDrive 车主手势识别独立微服务。"""
from __future__ import annotations

from contextlib import asynccontextmanager

import anyio.to_thread
import uvicorn
from fastapi import FastAPI

from . import config
from .api import router, source_router
from .service import gesture_service


@asynccontextmanager
async def lifespan(_app: FastAPI):
    anyio.to_thread.current_default_thread_limiter().total_tokens = config.THREADS
    yield


app = FastAPI(
    title="VisionDrive Owner Gesture Service",
    description="可切换 MediaPipe 关键点原型与 DINOv2-TCN 视频原型的录入服务",
    version="3.0.0",
    lifespan=lifespan,
)
app.include_router(router, prefix="/api/v1/owner-gestures", tags=["OwnerGesture"])
app.include_router(source_router, prefix="/api", tags=["OwnerGestureSource"])


@app.get("/health")
async def health_check():
    health = gesture_service.health()
    return {
        "status": "ok",
        "service": "VisionDrive Owner Gesture Service",
        "models": {
            "gestureRecognition": {
                "configPath": str(config.GESTURE_CONFIG_PATH),
                "configExists": config.GESTURE_CONFIG_PATH.exists(),
                "mode": "switchable MediaPipe or DINOv2 + geometry + TCN prototype engine",
                **health,
            }
        },
        "concurrency": {"workers": 1, "threads": config.THREADS, "stateMode": "single-process"},
    }


if __name__ == "__main__":
    uvicorn.run(
        "gesture.main:app",
        host=config.HOST,
        port=config.PORT,
        workers=1,
        reload=config.RELOAD,
    )
