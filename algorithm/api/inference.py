"""统一图片推理接口。

车主手势使用关键点原型网络服务；交警手势保留图片姿态推理管线。
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException

import config
from services.license_plate.pipeline import LicensePlatePipeline
from services.police_gesture.pipeline import PoliceGesturePipeline

router = APIRouter()
_pipelines: dict[str, Any] = {}


@router.post("/inference/image")
async def inference_image(request: dict):
    """统一图片推理：支持车牌和交警手势；车主手势使用 owner-gestures API。"""
    task_type = request.get("task_type") or request.get("taskType")
    image_url = request.get("image_url") or request.get("imageUrl")
    if not task_type:
        raise HTTPException(status_code=400, detail="task_type 不能为空")
    if not image_url:
        raise HTTPException(status_code=400, detail="image_url 不能为空")

    if task_type not in {"license_plate", "police_gesture"}:
        raise HTTPException(
            status_code=400,
            detail=(
                "不支持的图片推理任务类型；车主手势请使用 "
                "/api/v1/owner-gestures/recognize 或 "
                "/api/v1/owner-gestures/recognition/stream"
            ),
        )

    started = time.perf_counter()
    request_id = request.get("request_id") or request.get("requestId") or f"alg_{uuid.uuid4().hex[:12]}"

    try:
        pipeline = _get_pipeline(task_type)
        data = pipeline.process(image_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"算法推理失败: {exc}") from exc

    data = {
        "taskType": task_type,
        "latencyMs": round((time.perf_counter() - started) * 1000),
        **data,
    }

    return {
        "code": 0,
        "message": "success",
        "requestId": request_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }


def _get_pipeline(task_type: str):
    if task_type not in _pipelines:
        _pipelines[task_type] = _create_pipeline(task_type)
    return _pipelines[task_type]


def _create_pipeline(task_type: str):
    if task_type == "license_plate":
        return LicensePlatePipeline({
            "source_dir": config.LICENSE_PLATE_SOURCE_DIR,
            "clprnet_source_dir": config.CLPRNET_SOURCE_DIR,
            "clprnet_model_path": config.CLPRNET_MODEL_PATH,
        })
    if task_type == "police_gesture":
        return PoliceGesturePipeline({
            "source_dir": config.POLICE_GESTURE_SOURCE_DIR,
        })
    raise ValueError(f"不支持的任务类型: {task_type}")
