"""Owner gesture recognition API replacing the old gesture pipelines."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from starlette.concurrency import run_in_threadpool

from .service import gesture_service

router = APIRouter()
source_router = APIRouter()


def envelope(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "code": 0,
        "message": "success",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }


def handle_value_error(exc: ValueError) -> HTTPException:
    detail = str(exc) or "bad_request"
    status = 400 if detail != "手势不存在" else 404
    return HTTPException(status_code=status, detail=detail)


@router.get("")
async def legacy_library():
    return envelope(gesture_service.legacy_library())


@router.post("/enroll")
async def legacy_enroll(request: dict):
    try:
        return envelope(gesture_service.enroll(request))
    except ValueError as exc:
        raise handle_value_error(exc) from exc


@router.get("/control-settings")
async def legacy_control_settings():
    return envelope(gesture_service.control_settings())


@router.post("/control-settings")
async def legacy_save_control_settings(request: dict):
    return envelope(gesture_service.save_control_settings(request))


@router.get("/health")
async def health():
    return gesture_service.health()


@router.get("/state")
async def state():
    return gesture_service.state()


@router.get("/config")
async def get_config():
    return gesture_service.get_config()


@router.patch("/config")
async def patch_config(request: dict):
    return gesture_service.update_config(request, replace=False)


@router.put("/config")
async def put_config(request: dict):
    return gesture_service.update_config(request, replace=True)


@router.get("/prototypes")
async def list_prototypes():
    return gesture_service.list_prototypes()


@router.delete("/prototypes")
async def delete_all_prototypes():
    return gesture_service.clear_prototypes()


@router.delete("/prototypes/{prototype_id}")
async def delete_one_prototype(prototype_id: str):
    try:
        return gesture_service.delete_prototype(prototype_id)
    except ValueError as exc:
        raise handle_value_error(exc) from exc


@router.post("/recordings/start")
async def start_recording(request: dict):
    try:
        return gesture_service.start_recording(request)
    except ValueError as exc:
        raise handle_value_error(exc) from exc


@router.post("/recordings/cancel")
async def cancel_recording():
    return gesture_service.cancel_recording()


@router.post("/recognize")
async def recognize(request: dict):
    try:
        return await run_in_threadpool(gesture_service.recognize, request)
    except ValueError as exc:
        raise handle_value_error(exc) from exc


@router.put("/{prototype_id}")
async def legacy_update(prototype_id: str, request: dict):
    try:
        return envelope(gesture_service.update(prototype_id, request))
    except ValueError as exc:
        raise handle_value_error(exc) from exc


@router.delete("/{prototype_id}")
async def legacy_delete(prototype_id: str):
    try:
        return envelope(gesture_service.delete(prototype_id))
    except ValueError as exc:
        raise handle_value_error(exc) from exc


@router.websocket("/recognition/stream")
async def recognition_stream(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_json(gesture_service.state())
    try:
        while True:
            payload = await websocket.receive_json()
            if payload.get("type") != "frame" or not isinstance(payload.get("vector"), list):
                continue
            await websocket.send_json(gesture_service.process_frame(payload["vector"]))
    except WebSocketDisconnect:
        return


@source_router.get("/health")
async def source_health():
    return await health()


@source_router.get("/state")
async def source_state():
    return await state()


@source_router.get("/config")
async def source_get_config():
    return await get_config()


@source_router.patch("/config")
async def source_patch_config(request: dict):
    return await patch_config(request)


@source_router.put("/config")
async def source_put_config(request: dict):
    return await put_config(request)


@source_router.get("/prototypes")
async def source_list_prototypes():
    return await list_prototypes()


@source_router.delete("/prototypes")
async def source_delete_all_prototypes():
    return await delete_all_prototypes()


@source_router.delete("/prototypes/{prototype_id}")
async def source_delete_one_prototype(prototype_id: str):
    return await delete_one_prototype(prototype_id)


@source_router.post("/recordings/start")
async def source_start_recording(request: dict):
    return await start_recording(request)


@source_router.post("/recordings/cancel")
async def source_cancel_recording():
    return await cancel_recording()


@source_router.post("/recognize")
async def source_recognize(request: dict):
    return await recognize(request)


@source_router.websocket("/recognition/stream")
async def source_recognition_stream(websocket: WebSocket):
    await recognition_stream(websocket)
