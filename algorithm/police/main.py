"""VisionDrive 交警手势识别独立微服务。"""
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
from .pipeline import PoliceGesturePipeline

TASK_TYPE = "police_gesture"
_pipeline: PoliceGesturePipeline | None = None
_pipeline_lock = Lock()


def get_pipeline() -> PoliceGesturePipeline:
    global _pipeline
    if _pipeline is None:
        with _pipeline_lock:
            if _pipeline is None:
                _pipeline = PoliceGesturePipeline({
                    "source_dir": config.SOURCE_DIR,
                    "pose_input_size": config.POSE_INPUT_SIZE,
                    "temporal_steps": config.TEMPORAL_STEPS,
                })
    return _pipeline


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # 每个 Uvicorn worker 独立加载模型，提供模型级并行并避免父进程副本。
    await run_in_threadpool(get_pipeline)
    yield

app = FastAPI(
    title="VisionDrive Police Gesture Service",
    description="独立人体关键点与交警手势识别服务",
    version="2.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    pipeline = get_pipeline()
    pose_model = config.SOURCE_DIR / "checkpoints" / "pose_model.pt"
    lstm_model = config.SOURCE_DIR / "checkpoints" / "lstm.pt"
    return {
        "status": "ok",
        "service": "VisionDrive Police Gesture Service",
        "models": {
            "policeGesture": {
                "sourceDir": str(config.SOURCE_DIR),
                "poseModel": str(pose_model),
                "lstmModel": str(lstm_model),
                "modelExists": pose_model.exists() and lstm_model.exists(),
                "mode": "ctpgr-pytorch pose + LSTM",
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
    source_id = request.get("source_id") or request.get("sourceId") or "default"
    include_visuals = request.get("include_visuals", request.get("includeVisuals"))
    if not task_type:
        raise HTTPException(status_code=400, detail="task_type 不能为空")
    if task_type != TASK_TYPE:
        raise HTTPException(status_code=400, detail=f"交警手势服务不支持任务类型: {task_type}")
    if not image_url:
        raise HTTPException(status_code=400, detail="image_path 或 image_url 不能为空")

    started = time.perf_counter()
    request_id = request.get("request_id") or request.get("requestId") or f"alg_{uuid.uuid4().hex[:12]}"
    try:
        if include_visuals is None:
            include_visuals = not bool(image_path)
        data = await run_in_threadpool(get_pipeline().process, image_url, bool(include_visuals), source_id)
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
        "police.main:app",
        host=config.HOST,
        port=config.PORT,
        workers=1 if config.RELOAD else config.WORKERS,
        reload=config.RELOAD,
    )
