from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, StreamingResponse
from pydantic import BaseModel, Field

from config import DEFAULT_FPS, HOST, JPEG_QUALITY, PORT
from services.sources import (
    BROWSER_CAMERA_SOURCE_ID,
    CameraManager,
    decode_data_url_image,
    decode_image_bytes,
    make_custom_source,
    resize_to_canvas,
)


app = FastAPI(title="VisionDrive Virtual Camera Service", version="1.0.0")
manager = CameraManager()
WEB_DIR = Path(__file__).resolve().parent / "web"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SetSourceRequest(BaseModel):
    sourceId: str | None = None
    sourceType: Literal["browser", "device", "image", "video"] | None = None
    path: str | None = None
    deviceIndex: int | None = None
    name: str | None = None
    fps: int = Field(default=DEFAULT_FPS, ge=1, le=30)
    loop: bool = True


@app.get("/")
def root() -> dict:
    return health()


@app.get("/ui", include_in_schema=False)
@app.get("/ui/", include_in_schema=False)
def camera_admin_ui() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/health")
def health() -> dict:
    active = manager.get_active_source()
    return {
        "status": "ok",
        "service": "virtual-camera",
        "sourceCount": len(manager.sources),
        "activeSourceId": active.id if active else None,
        "activeSource": active.to_dict() if active else None,
    }


@app.get("/api/v1/cameras/sources")
def list_sources() -> dict:
    return {
        "success": True,
        "data": {
            "sources": manager.list_sources(),
            "activeSourceId": manager.active_source_id,
        },
    }


@app.get("/api/v1/cameras/state")
def camera_state() -> dict:
    active = manager.get_active_source()
    return {
        "success": True,
        "data": {
            "activeSourceId": active.id if active else None,
            "activeSource": active.to_dict() if active else None,
        },
    }


@app.post("/api/v1/cameras/source")
def set_source(request: SetSourceRequest) -> dict:
    try:
        if request.sourceId:
            source = manager.set_active(request.sourceId)
        else:
            if not request.sourceType:
                raise ValueError("sourceId 或 sourceType 至少提供一个")
            source = make_custom_source(
                request.sourceType,
                path=request.path,
                device_index=request.deviceIndex,
                name=request.name,
                fps=request.fps,
                loop=request.loop,
            )
            manager.add_source(source)
            manager.set_active(source.id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "success": True,
        "data": {
            "activeSourceId": source.id,
            "activeSource": source.to_dict(),
        },
    }


@app.post("/api/v1/cameras/browser-frame")
async def browser_frame(
    http_request: Request,
    sourceId: str = Query(default=BROWSER_CAMERA_SOURCE_ID),
) -> dict:
    try:
        content_type = http_request.headers.get("content-type", "")
        if content_type.startswith("application/json"):
            payload = await http_request.json()
            frame = await asyncio.to_thread(decode_data_url_image, payload.get("image", ""))
            source_id = payload.get("sourceId") or sourceId
        else:
            raw = await http_request.body()
            frame = await asyncio.to_thread(decode_image_bytes, raw)
            source_id = sourceId
        source = await asyncio.to_thread(manager.update_browser_frame, frame, source_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "success": True,
        "data": {
            "activeSourceId": source.id,
            "activeSource": source.to_dict(),
        },
    }


@app.delete("/api/v1/cameras/source/{source_id}")
def delete_source(source_id: str) -> dict:
    try:
        removed = manager.remove_source(source_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    active = manager.get_active_source()
    return {
        "success": True,
        "data": {
            "removedSource": removed.to_dict(),
            "activeSourceId": active.id if active else None,
            "activeSource": active.to_dict() if active else None,
        },
    }


@app.get("/api/v1/cameras/snapshot.jpg")
def snapshot(sourceId: str | None = Query(default=None)) -> Response:
    try:
        image_path = manager.get_snapshot_image_path(sourceId)
        if image_path:
            return FileResponse(
                image_path,
                media_type="image/jpeg",
                headers={
                    "Cache-Control": "no-store, max-age=0",
                    "X-Camera-Source": manager.active_source_id,
                    "X-Capture-Timestamp": str(int(time.time() * 1000)),
                    "X-Image-Transport": "original-file",
                },
            )
        frame = manager.read_snapshot_frame(sourceId)
        jpeg = manager.encode_jpeg(frame)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(
        content=jpeg,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "no-store, max-age=0",
            "X-Camera-Source": manager.active_source_id,
            "X-Capture-Timestamp": str(int(time.time() * 1000)),
        },
    )


@app.get("/api/v1/cameras/stream.mjpg")
async def mjpeg_stream(
    sourceId: str | None = Query(default=None),
    fps: int = Query(default=DEFAULT_FPS, ge=1, le=30),
    preview: bool = Query(default=False),
    quality: int = Query(default=JPEG_QUALITY, ge=50, le=100),
) -> StreamingResponse:
    async def generator():
        while True:
            try:
                frame = await asyncio.to_thread(manager.read_frame, sourceId)
                if preview:
                    frame = await asyncio.to_thread(resize_to_canvas, frame)
                jpeg = await asyncio.to_thread(manager.encode_jpeg, frame, quality)
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    b"Cache-Control: no-cache\r\n\r\n" + jpeg + b"\r\n"
                )
            except Exception as exc:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: text/plain\r\n\r\n" + str(exc).encode("utf-8") + b"\r\n"
                )
            await asyncio.sleep(1 / max(1, fps))

    return StreamingResponse(
        generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-store"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)
