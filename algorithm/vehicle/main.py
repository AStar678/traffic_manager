"""VisionDrive PP-Vehicle 车辆类别识别微服务。"""
from __future__ import annotations

import json
import os
import tempfile
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator
from starlette.concurrency import run_in_threadpool

from . import __version__, config
from .runtime import PPVehicleRuntime, RuntimeNotReadyError
from .sources import materialize_video, validate_local_image, validate_local_video, validate_remote_url

TASK_TYPE = "vehicle_type"
_runtime = PPVehicleRuntime()


class VideoInferenceRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    task_type: str = Field(default=TASK_TYPE, alias="taskType")
    video_path: str | None = Field(default=None, alias="videoPath")
    video_url: str | None = Field(default=None, alias="videoUrl")
    request_id: str | None = Field(default=None, alias="requestId")

    @model_validator(mode="after")
    def validate_input(self) -> "VideoInferenceRequest":
        if self.task_type != TASK_TYPE:
            raise ValueError(f"车辆类别服务不支持任务类型: {self.task_type}")
        if bool(self.video_path) == bool(self.video_url):
            raise ValueError("video_path 和 video_url 必须且只能传一个")
        return self


class ImageInferenceRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    task_type: str = Field(default=TASK_TYPE, alias="taskType")
    image_path: str = Field(alias="imagePath")
    source_id: str = Field(default="camera-default", alias="sourceId")
    request_id: str | None = Field(default=None, alias="requestId")

    @model_validator(mode="after")
    def validate_task(self) -> "ImageInferenceRequest":
        if self.task_type != TASK_TYPE:
            raise ValueError(f"车辆类别服务不支持任务类型: {self.task_type}")
        if not self.image_path.strip():
            raise ValueError("image_path 不能为空")
        if not self.source_id.strip():
            raise ValueError("source_id 不能为空")
        return self


@asynccontextmanager
async def lifespan(_app: FastAPI):
    config.WORK_DIR.mkdir(parents=True, exist_ok=True)
    if config.PRELOAD_MODEL:
        try:
            await run_in_threadpool(_runtime.ensure_ready)
        except RuntimeNotReadyError:
            # 健康检查会显示精确原因，服务仍可启动以便排障。
            pass
    yield


app = FastAPI(
    title="VisionDrive Vehicle Type Service",
    description="PP-Vehicle 车辆类别识别与实时多目标跟踪微服务",
    version=__version__,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(config.ALLOWED_ORIGINS),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
async def test_page():
    return FileResponse(config.BASE_DIR / "web/index.html")


@app.get("/health")
async def health_check():
    status = _runtime.status
    return {
        "status": "ok" if status["ready"] else "degraded",
        "service": "VisionDrive Vehicle Type Service",
        "version": __version__,
        "taskType": TASK_TYPE,
        "model": status,
    }


@app.post("/api/v1/inference/image")
async def inference_image(payload: ImageInferenceRequest):
    request_id = payload.request_id or f"veh_{uuid.uuid4().hex[:12]}"
    started = time.perf_counter()
    try:
        image_path = await run_in_threadpool(validate_local_image, payload.image_path)
        await _ensure_runtime_ready()
        data = await run_in_threadpool(
            _runtime.analyze_image,
            str(image_path),
            payload.source_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeNotReadyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"车辆类别推理失败: {exc}") from exc
    return {
        "code": 0,
        "message": "success",
        "requestId": request_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {
            **data,
            "latencyMs": round((time.perf_counter() - started) * 1000),
        },
    }


@app.post("/api/v1/inference/video")
async def inference_video(payload: VideoInferenceRequest):
    request_id = payload.request_id or f"veh_{uuid.uuid4().hex[:12]}"
    try:
        if payload.video_path:
            await run_in_threadpool(validate_local_video, payload.video_path)
        else:
            await run_in_threadpool(validate_remote_url, payload.video_url or "")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await _ensure_runtime_ready()

    def events() -> Iterator[bytes]:
        try:
            with materialize_video(payload.video_path, payload.video_url) as source:
                yield from _encode_events(_runtime.analyze_video(source), request_id)
        except Exception as exc:  # noqa: BLE001
            yield _encode_event({"event": "error", "requestId": request_id, "message": str(exc)})

    return _streaming_response(events())


@app.post("/api/v1/inference/video/upload")
async def inference_video_upload(file: UploadFile = File(...)):
    suffix = Path(file.filename or "upload.mp4").suffix.lower()
    if suffix not in config.SUPPORTED_VIDEO_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"不支持的视频格式: {suffix or '无扩展名'}")
    await _ensure_runtime_ready()
    temp_path = await _save_upload(file, suffix)
    request_id = f"veh_{uuid.uuid4().hex[:12]}"

    def events() -> Iterator[bytes]:
        try:
            yield from _encode_events(_runtime.analyze_video(str(temp_path)), request_id)
        except Exception as exc:  # noqa: BLE001
            yield _encode_event({"event": "error", "requestId": request_id, "message": str(exc)})
        finally:
            temp_path.unlink(missing_ok=True)

    return _streaming_response(events())


async def _ensure_runtime_ready() -> None:
    try:
        await run_in_threadpool(_runtime.ensure_ready)
    except RuntimeNotReadyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


async def _save_upload(file: UploadFile, suffix: str) -> Path:
    config.WORK_DIR.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix="upload-", suffix=suffix, dir=config.WORK_DIR)
    path = Path(name)
    written = 0
    try:
        with os.fdopen(fd, "wb") as target:
            while chunk := await file.read(1024 * 1024):
                written += len(chunk)
                if written > config.MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="上传视频超过最大允许大小")
                target.write(chunk)
        return path
    except Exception:
        path.unlink(missing_ok=True)
        raise
    finally:
        await file.close()


def _encode_events(events: Iterator[dict[str, Any]], request_id: str) -> Iterator[bytes]:
    for event in events:
        yield _encode_event({"requestId": request_id, **event})


def _encode_event(event: dict[str, Any]) -> bytes:
    return (json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def _streaming_response(events: Iterator[bytes]) -> StreamingResponse:
    return StreamingResponse(
        events,
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    uvicorn.run(
        "vehicle.main:app",
        host=config.HOST,
        port=config.PORT,
        workers=1,
        reload=config.RELOAD,
    )
