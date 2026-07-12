from __future__ import annotations

import asyncio
import contextlib
import time
from fractions import Fraction
from pathlib import Path
from typing import Literal

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, StreamingResponse
from pydantic import BaseModel, Field

from config import DEFAULT_FPS, HOST, JPEG_QUALITY, PORT
from services.sources import (
    BROWSER_CAMERA_SOURCE_ID,
    CameraManager,
    browser_frame_status,
    decode_data_url_image,
    decode_image_bytes,
    make_custom_source,
    resize_to_canvas,
)

try:
    from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
    from aiortc.mediastreams import MediaStreamError
    from av import VideoFrame
except ImportError:  # pragma: no cover - dependency is optional until installed from requirements.txt
    RTCPeerConnection = None
    RTCSessionDescription = None
    VideoStreamTrack = None
    MediaStreamError = Exception
    VideoFrame = None


app = FastAPI(title="VisionDrive Virtual Camera Service", version="1.0.0")
manager = CameraManager()
WEB_DIR = Path(__file__).resolve().parent / "web"
VIDEO_CLOCK_RATE = 90_000
VIDEO_TIME_BASE = Fraction(1, VIDEO_CLOCK_RATE)
WEBRTC_ICE_TIMEOUT_SECONDS = 3.0
peer_connections: set = set()
consumer_tasks: set[asyncio.Task] = set()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SetSourceRequest(BaseModel):
    sourceId: str | None = None
    sourceType: Literal["browser", "device", "image", "video", "rtsp"] | None = None
    path: str | None = None
    deviceIndex: int | None = None
    name: str | None = None
    fps: int = Field(default=DEFAULT_FPS, ge=1, le=30)
    loop: bool = True


class WebRtcOfferRequest(BaseModel):
    sdp: str
    type: Literal["offer"] = "offer"
    sourceId: str | None = None
    fps: int = Field(default=DEFAULT_FPS, ge=1, le=30)


if VideoStreamTrack is not None:

    class CameraVideoTrack(VideoStreamTrack):
        """A WebRTC video track backed by the active camera source."""

        kind = "video"

        def __init__(self, camera_manager: CameraManager, source_id: str | None, fps: int) -> None:
            super().__init__()
            self.camera_manager = camera_manager
            self.source_id = source_id
            self.fps = max(1, min(30, fps))
            self._start: float | None = None
            self._timestamp = 0

        async def recv(self):
            pts = await self._next_timestamp()
            frame, _ = await asyncio.to_thread(self.camera_manager.read_frame_with_meta, self.source_id)
            frame = await asyncio.to_thread(resize_to_canvas, frame)
            video_frame = VideoFrame.from_ndarray(frame, format="bgr24")
            video_frame.pts = pts
            video_frame.time_base = VIDEO_TIME_BASE
            return video_frame

        async def _next_timestamp(self) -> int:
            now = time.time()
            if self._start is None:
                self._start = now
                self._timestamp = 0
                return self._timestamp

            self._timestamp += max(1, int(VIDEO_CLOCK_RATE / self.fps))
            wait = self._start + (self._timestamp / VIDEO_CLOCK_RATE) - now
            if wait > 0:
                await asyncio.sleep(wait)
            return self._timestamp

else:
    CameraVideoTrack = None


@app.get("/")
def root() -> dict:
    return health()


@app.get("/ui", include_in_schema=False)
@app.get("/ui/", include_in_schema=False)
def camera_admin_ui() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html", headers={"Cache-Control": "no-store"})


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


@app.get("/api/v1/cameras/frame-info")
def camera_frame_info(sourceId: str | None = Query(default=None)) -> dict:
    try:
        meta = manager.get_frame_info(sourceId)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "success": True,
        "data": meta,
    }


@app.get("/api/v1/cameras/browser-frame-status")
def camera_browser_frame_status() -> dict:
    return {
        "success": True,
        "data": browser_frame_status(),
    }


@app.get("/api/v1/cameras/webrtc/status")
def camera_webrtc_status() -> dict:
    return {
        "success": True,
        "data": {
            "available": RTCPeerConnection is not None,
            "peerCount": len(peer_connections),
            "consumerCount": len(consumer_tasks),
            "transport": "webrtc",
        },
    }


@app.post("/api/v1/cameras/webrtc/offer")
async def camera_webrtc_offer(request: WebRtcOfferRequest) -> dict:
    ensure_webrtc_available()
    try:
        meta = await asyncio.to_thread(manager.get_frame_info, request.sourceId)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    pc = RTCPeerConnection()
    peer_connections.add(pc)
    fps = request.fps or int(meta.get("fps") or DEFAULT_FPS)
    pc.addTrack(CameraVideoTrack(manager, request.sourceId, fps))
    register_peer_cleanup(pc)

    await pc.setRemoteDescription(RTCSessionDescription(sdp=request.sdp, type=request.type))
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    await wait_for_ice_gathering_complete(pc)

    return {
        "success": True,
        "data": {
            "sdp": pc.localDescription.sdp,
            "type": pc.localDescription.type,
            "sourceId": request.sourceId or meta.get("sourceId"),
            "transport": "webrtc",
        },
    }


@app.post("/api/v1/cameras/webrtc/publish")
async def camera_webrtc_publish(request: WebRtcOfferRequest) -> dict:
    ensure_webrtc_available()
    source_id = request.sourceId or BROWSER_CAMERA_SOURCE_ID
    try:
        await asyncio.to_thread(manager.set_active, source_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    pc = RTCPeerConnection()
    peer_connections.add(pc)
    register_peer_cleanup(pc)

    @pc.on("track")
    def on_track(track):
        if track.kind != "video":
            return
        task = asyncio.create_task(consume_browser_video(track, source_id))
        consumer_tasks.add(task)
        task.add_done_callback(consumer_tasks.discard)

    await pc.setRemoteDescription(RTCSessionDescription(sdp=request.sdp, type=request.type))
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    await wait_for_ice_gathering_complete(pc)

    return {
        "success": True,
        "data": {
            "sdp": pc.localDescription.sdp,
            "type": pc.localDescription.type,
            "sourceId": source_id,
            "transport": "webrtc",
        },
    }


@app.post("/api/v1/cameras/source")
def set_source(request: SetSourceRequest, background_tasks: BackgroundTasks) -> dict:
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

    background_tasks.add_task(manager.warm_source, source.id)

    return {
        "success": True,
        "data": {
            "activeSourceId": source.id,
            "activeSource": source.to_dict(),
            "browserFrame": browser_frame_status(),
        },
    }


@app.post("/api/v1/cameras/browser-frame")
async def browser_frame(
    http_request: Request,
    sourceId: str = Query(default=BROWSER_CAMERA_SOURCE_ID),
    width: int = Query(default=0, ge=0),
    height: int = Query(default=0, ge=0),
    ack: bool = Query(default=True),
) -> dict:
    try:
        content_type = http_request.headers.get("content-type", "")
        if content_type.startswith("application/json"):
            payload = await http_request.json()
            frame = await asyncio.to_thread(decode_data_url_image, payload.get("image", ""))
            source_id = payload.get("sourceId") or sourceId
            source = await asyncio.to_thread(manager.update_browser_frame, frame, source_id)
        else:
            raw = await http_request.body()
            source_id = sourceId
            if content_type.startswith("image/jpeg"):
                source = await asyncio.to_thread(
                    manager.update_browser_frame_bytes,
                    raw,
                    source_id,
                    content_type=content_type,
                    width=width,
                    height=height,
                )
            else:
                frame = await asyncio.to_thread(decode_image_bytes, raw)
                source = await asyncio.to_thread(manager.update_browser_frame, frame, source_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not ack:
        return Response(status_code=204)

    return {
        "success": True,
        "data": {
            "activeSourceId": source.id,
            "activeSource": source.to_dict(),
            "browserFrame": browser_frame_status(),
        },
    }


def ensure_webrtc_available() -> None:
    if RTCPeerConnection is None or RTCSessionDescription is None or CameraVideoTrack is None or VideoFrame is None:
        raise HTTPException(
            status_code=503,
            detail="WebRTC 依赖未安装，请先安装 camera_service/requirements.txt 中的 aiortc",
        )


def register_peer_cleanup(pc) -> None:
    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        if pc.connectionState in {"failed", "closed", "disconnected"}:
            await close_peer_connection(pc)


async def close_peer_connection(pc) -> None:
    peer_connections.discard(pc)
    if pc.connectionState != "closed":
        await pc.close()


async def wait_for_ice_gathering_complete(pc) -> None:
    if pc.iceGatheringState == "complete":
        return

    loop = asyncio.get_running_loop()
    done = loop.create_future()

    @pc.on("icegatheringstatechange")
    def on_icegatheringstatechange():
        if pc.iceGatheringState == "complete" and not done.done():
            done.set_result(None)

    if pc.iceGatheringState == "complete" and not done.done():
        done.set_result(None)

    with contextlib.suppress(asyncio.TimeoutError):
        await asyncio.wait_for(done, timeout=WEBRTC_ICE_TIMEOUT_SECONDS)


async def consume_browser_video(track, source_id: str) -> None:
    while True:
        try:
            frame = await track.recv()
        except MediaStreamError:
            break
        except asyncio.CancelledError:
            raise

        image = frame.to_ndarray(format="bgr24")
        try:
            await asyncio.to_thread(manager.update_browser_video_frame, image, source_id)
        except (KeyError, ValueError):
            break


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
        meta = manager.get_frame_info(sourceId)
        if image_path:
            return FileResponse(
                image_path,
                media_type="image/jpeg",
                headers={
                    "Cache-Control": "no-store, max-age=0",
                    "X-Camera-Source": meta["sourceId"],
                    "X-Camera-Frame-Index": str(meta["frameIndex"]),
                    "X-Capture-Timestamp": str(meta["timestampMs"]),
                    "X-Image-Transport": "original-file",
                },
            )
        jpeg, meta = manager.read_jpeg_frame_with_meta(sourceId)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(
        content=jpeg,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "no-store, max-age=0",
            "X-Camera-Source": meta["sourceId"],
            "X-Camera-Frame-Index": str(meta["frameIndex"]),
            "X-Capture-Timestamp": str(meta["timestampMs"]),
        },
    )


@app.get("/api/v1/cameras/snapshot.png")
def snapshot_png(sourceId: str | None = Query(default=None)) -> Response:
    try:
        frame, meta = manager.read_snapshot_frame_with_meta(sourceId)
        png = manager.encode_png(frame)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(
        content=png,
        media_type="image/png",
        headers={
            "Cache-Control": "no-store, max-age=0",
            "X-Camera-Source": meta["sourceId"],
            "X-Camera-Frame-Index": str(meta["frameIndex"]),
            "X-Capture-Timestamp": str(meta["timestampMs"]),
            "X-Image-Transport": "lossless-png",
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
                jpeg, meta = await asyncio.to_thread(
                    manager.read_jpeg_frame_with_meta,
                    sourceId,
                    quality,
                    preview=preview,
                )
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    b"Cache-Control: no-cache\r\n"
                    + f"X-Camera-Source: {meta['sourceId']}\r\n".encode("utf-8")
                    + f"X-Camera-Frame-Index: {meta['frameIndex']}\r\n".encode("utf-8")
                    + f"X-Capture-Timestamp: {meta['timestampMs']}\r\n\r\n".encode("utf-8")
                    + jpeg + b"\r\n"
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


@app.on_event("shutdown")
async def on_shutdown() -> None:
    for task in list(consumer_tasks):
        task.cancel()
    if consumer_tasks:
        await asyncio.gather(*consumer_tasks, return_exceptions=True)
    await asyncio.gather(
        *(close_peer_connection(pc) for pc in list(peer_connections)),
        return_exceptions=True,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)
