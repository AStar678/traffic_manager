"""VisionDrive 车牌识别独立微服务。"""
from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from threading import Lock

import uvicorn
from fastapi import FastAPI, HTTPException
from starlette.concurrency import run_in_threadpool

from . import config
from .pipeline import LicensePlatePipeline

TASK_TYPE = "license_plate"
_pipeline: LicensePlatePipeline | None = None
_pipeline_lock = Lock()


def get_pipeline() -> LicensePlatePipeline:
    global _pipeline
    if _pipeline is None:
        with _pipeline_lock:
            if _pipeline is None:
                _pipeline = LicensePlatePipeline({
                    "source_dir": config.SOURCE_DIR,
                    "clprnet_source_dir": config.CLPRNET_SOURCE_DIR,
                    "clprnet_model_path": config.CLPRNET_MODEL_PATH,
                })
    return _pipeline


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Uvicorn worker 启动后再加载模型，避免父进程提前占用一份模型内存。
    await run_in_threadpool(get_pipeline)
    yield

app = FastAPI(
    title="VisionDrive License Plate Service",
    description="独立车牌检测、OCR 与颜色识别服务",
    version="2.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    pipeline = get_pipeline()
    return {
        "status": "ok",
        "service": "VisionDrive License Plate Service",
        "models": {
            "licensePlate": {
                "sourceDir": str(config.SOURCE_DIR),
                "clprnetModel": str(config.CLPRNET_MODEL_PATH),
                "modelExists": config.CLPRNET_MODEL_PATH.exists(),
                "status": pipeline.status,
            }
        },
        "concurrency": {"workers": config.WORKERS, "offload": "threadpool"},
    }


@app.post("/api/v1/inference/image")
async def inference_image(request: dict):
    task_type = request.get("task_type") or request.get("taskType")
    image_path = request.get("image_path") or request.get("imagePath")
    image_url = image_path or request.get("image_url") or request.get("imageUrl")
    if not task_type:
        raise HTTPException(status_code=400, detail="task_type 不能为空")
    if task_type != TASK_TYPE:
        raise HTTPException(status_code=400, detail=f"车牌服务不支持任务类型: {task_type}")
    if not image_url:
        raise HTTPException(status_code=400, detail="image_path 或 image_url 不能为空")

    started = time.perf_counter()
    request_id = request.get("request_id") or request.get("requestId") or f"alg_{uuid.uuid4().hex[:12]}"
    try:
        data = await run_in_threadpool(get_pipeline().process, image_url, not bool(image_path))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"算法推理失败: {exc}") from exc

    return {
        "code": 0,
        "message": "success",
        "requestId": request_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {
            "taskType": TASK_TYPE,
            "latencyMs": round((time.perf_counter() - started) * 1000),
            **data,
        },
    }


if __name__ == "__main__":
    uvicorn.run(
        "license.main:app",
        host=config.HOST,
        port=config.PORT,
        workers=1 if config.RELOAD else config.WORKERS,
        reload=config.RELOAD,
    )
