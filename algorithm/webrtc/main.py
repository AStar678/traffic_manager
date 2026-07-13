"""WebRTC gateway for the three camera slots managed by the Java main service."""
from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import uvicorn
from aioice import stun
from aiortc import RTCPeerConnection, RTCRtpSender, RTCSessionDescription, VideoStreamTrack
from aiortc.contrib.media import MediaRelay
from av import VideoFrame
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image

from . import config

log = logging.getLogger("visiondrive.webrtc")


class StunBindingProtocol(asyncio.DatagramProtocol):
    """Minimal unauthenticated STUN binding server for the private Tailscale network."""

    def connection_made(self, transport) -> None:
        self.transport = transport

    def datagram_received(self, data: bytes, address: tuple[str, int]) -> None:
        try:
            request = stun.parse_message(data)
        except ValueError:
            return
        if request.message_method != stun.Method.BINDING or request.message_class != stun.Class.REQUEST:
            return
        response = stun.Message(
            stun.Method.BINDING,
            stun.Class.RESPONSE,
            transaction_id=request.transaction_id,
            attributes={"XOR-MAPPED-ADDRESS": address},
        )
        response.attributes["FINGERPRINT"] = stun.message_fingerprint(bytes(response))
        self.transport.sendto(bytes(response), address)


class StaticImageTrack(VideoStreamTrack):
    """Repeat a still image as a low-rate WebRTC video track."""

    def __init__(self, path: str):
        super().__init__()
        rgb = np.asarray(Image.open(path).convert("RGB"), dtype=np.uint8)
        self.frame = VideoFrame.from_ndarray(rgb, format="rgb24")

    async def recv(self) -> VideoFrame:
        pts, time_base = await self.next_timestamp()
        frame = self.frame.reformat(format="yuv420p")
        frame.pts = pts
        frame.time_base = time_base
        return frame


class BoundedVideoTrack(VideoStreamTrack):
    """Deep-copy relayed frames and cap encode resolution."""

    def __init__(self, source: VideoStreamTrack):
        super().__init__()
        self.source = source

    async def recv(self) -> VideoFrame:
        frame = await self.source.recv()
        scale = min(1.0, config.MAX_WIDTH / frame.width, config.MAX_HEIGHT / frame.height)
        width = frame.width if scale >= 1.0 else max(2, int(frame.width * scale) // 2 * 2)
        height = frame.height if scale >= 1.0 else max(2, int(frame.height * scale) // 2 * 2)
        # MediaRelay intentionally shares one AVFrame object.  The RTP encoder runs
        # on a worker thread while the snapshot path converts that same object, so
        # handing the shared native frame to the encoder can corrupt its refcount.
        # Materializing a new ndarray/VideoFrame gives each encoder sole ownership.
        pixels = frame.to_ndarray(format="rgb24")
        if width != frame.width or height != frame.height:
            pixels = np.asarray(Image.fromarray(pixels).resize((width, height)), dtype=np.uint8)
        copied = VideoFrame.from_ndarray(pixels.copy(), format="rgb24")
        copied.pts = frame.pts
        if frame.time_base is not None:
            copied.time_base = frame.time_base
        return copied


class FfmpegProcessTrack(VideoStreamTrack):
    """Decode one source in an isolated FFmpeg process to protect the gateway."""

    def __init__(self, input_args: list[str]):
        super().__init__()
        self.input_args = input_args
        self.process: asyncio.subprocess.Process | None = None
        self.frame_size = config.MAX_WIDTH * config.MAX_HEIGHT * 3

    async def _start(self) -> None:
        filter_graph = (
            f"scale={config.MAX_WIDTH}:{config.MAX_HEIGHT}:force_original_aspect_ratio=decrease,"
            f"pad={config.MAX_WIDTH}:{config.MAX_HEIGHT}:(ow-iw)/2:(oh-ih)/2,fps={config.OUTPUT_FPS}"
        )
        self.process = await asyncio.create_subprocess_exec(
            config.FFMPEG_BINARY,
            "-hide_banner",
            "-loglevel", "error",
            "-nostdin",
            *self.input_args,
            "-an",
            "-vf", filter_graph,
            "-pix_fmt", "rgb24",
            "-f", "rawvideo",
            "pipe:1",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )

    async def recv(self) -> VideoFrame:
        for attempt in range(2):
            if self.process is None or self.process.returncode is not None:
                await self._start()
            try:
                payload = await self.process.stdout.readexactly(self.frame_size)
            except asyncio.IncompleteReadError:
                await self._stop_process()
                if attempt == 0:
                    await asyncio.sleep(0.2)
                    continue
                raise
            pts, time_base = await self.next_timestamp()
            array = np.frombuffer(payload, dtype=np.uint8).reshape(config.MAX_HEIGHT, config.MAX_WIDTH, 3)
            frame = VideoFrame.from_ndarray(array, format="rgb24")
            frame.pts = pts
            frame.time_base = time_base
            return frame
        raise RuntimeError("FFmpeg 视频源无法读取")

    async def _stop_process(self) -> None:
        process, self.process = self.process, None
        if process is not None and process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=2)
            except TimeoutError:
                process.kill()

    def stop(self) -> None:
        process, self.process = self.process, None
        if process is not None and process.returncode is None:
            process.terminate()
        super().stop()


@dataclass
class CameraSource:
    fingerprint: str
    player: Any | None
    relay: MediaRelay | None
    track: VideoStreamTrack
    snapshot_task: asyncio.Task | None = None

    def stop(self) -> None:
        if self.snapshot_task is not None:
            self.snapshot_task.cancel()
        self.track.stop()
        if self.player is not None:
            video = getattr(self.player, "video", None)
            audio = getattr(self.player, "audio", None)
            if video is not None:
                video.stop()
            if audio is not None:
                audio.stop()


class CameraRegistry:
    def __init__(self) -> None:
        self._sources: dict[int, CameraSource] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, slot_id: int) -> VideoStreamTrack:
        async with self._lock:
            slot = self._load_slot(slot_id)
            fingerprint = json.dumps(slot, ensure_ascii=False, sort_keys=True)
            source = self._sources.get(slot_id)
            if source is None or source.fingerprint != fingerprint or (source.snapshot_task and source.snapshot_task.done()):
                if source is not None:
                    source.stop()
                source = self._open_source(slot, fingerprint)
                self._sources[slot_id] = source
                source.snapshot_task = asyncio.create_task(self._publish_latest_frame(slot_id, source))
            track = source.relay.subscribe(source.track, buffered=False) if source.relay else source.track
            return BoundedVideoTrack(track)

    async def _publish_latest_frame(self, slot_id: int, source: CameraSource) -> None:
        track = source.relay.subscribe(source.track, buffered=False) if source.relay else source.track
        output = config.CAMERA_FRAME_DIR / f"camera-{slot_id}.jpg"
        interval = 1.0 / config.FRAME_PUBLISH_FPS
        last_saved = 0.0
        try:
            while True:
                frame = await track.recv()
                now = asyncio.get_running_loop().time()
                if now - last_saved < interval:
                    continue
                last_saved = now
                await asyncio.to_thread(self._save_frame, frame, output)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            log.warning("摄像头 %s 帧发布中断: %s", slot_id, exc)
            await close_slot_peers(slot_id)

    @staticmethod
    def _save_frame(frame: VideoFrame, output: Path) -> None:
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_name(f".{output.name}.webrtc.tmp")
        frame.to_image().save(temporary, format="JPEG", quality=88)
        temporary.replace(output)

    def _load_slot(self, slot_id: int) -> dict[str, Any]:
        if slot_id not in (1, 2, 3):
            raise HTTPException(status_code=404, detail="摄像头槽位必须是 1-3")
        try:
            slots = json.loads(config.CAMERA_STATE_FILE.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise HTTPException(status_code=503, detail="摄像头状态文件不存在") from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=503, detail=f"无法读取摄像头状态: {exc}") from exc
        slot = next((item for item in slots if int(item.get("slotId", 0)) == slot_id), None)
        if slot is None:
            raise HTTPException(status_code=404, detail=f"摄像头 {slot_id} 不存在")
        if str(slot.get("sourceType", "OFF")).upper() == "OFF":
            raise HTTPException(status_code=409, detail=f"摄像头 {slot_id} 已关闭")
        return slot

    def _open_source(self, slot: dict[str, Any], fingerprint: str) -> CameraSource:
        source_type = str(slot.get("sourceType", "OFF")).upper()
        path = str(slot.get("path") or "")
        if source_type == "IMAGE":
            if not Path(path).is_file():
                raise HTTPException(status_code=404, detail=f"图片不存在: {path}")
            return CameraSource(fingerprint, None, MediaRelay(), StaticImageTrack(path))

        if source_type == "SANDBOX":
            path = path if path.startswith(("rtsp://", "rtsps://")) else f"{config.SANDBOX_BASE_URL}/{path.lstrip('/')}"
        if source_type == "DEVICE":
            device_index = max(0, int(slot.get("deviceIndex") or 0))
            input_args = ["-f", "v4l2", "-framerate", str(config.OUTPUT_FPS), "-i", f"/dev/video{device_index}"]
        elif source_type == "VIDEO":
            if not Path(path).is_file():
                raise HTTPException(status_code=404, detail=f"视频不存在: {path}")
            input_args = ["-stream_loop", "-1", "-re", "-i", path]
        elif source_type in {"RTSP", "SANDBOX"}:
            input_args = [
                "-rtsp_transport", "tcp",
                "-fflags", "nobuffer",
                "-flags", "low_delay",
                "-analyzeduration", "500000",
                "-probesize", "500000",
                "-i", path,
            ]
        else:
            raise HTTPException(status_code=400, detail=f"WebRTC 不支持输入类型: {source_type}")

        track = FfmpegProcessTrack(input_args)
        return CameraSource(fingerprint, None, MediaRelay(), track)

    async def close(self) -> None:
        async with self._lock:
            for source in self._sources.values():
                source.stop()
            self._sources.clear()


registry = CameraRegistry()
peer_connections: dict[str, RTCPeerConnection] = {}
peer_slots: dict[str, int] = {}
peer_clients: dict[str, str] = {}


def prefer_vp8(pc: RTCPeerConnection) -> None:
    """Use aiortc's stable software VP8 path for concurrent camera sessions."""
    codecs = RTCRtpSender.getCapabilities("video").codecs
    preferred = [codec for codec in codecs if codec.mimeType.lower() == "video/vp8"]
    for transceiver in pc.getTransceivers():
        if transceiver.kind == "video" and preferred:
            transceiver.setCodecPreferences(preferred)


def expose_mdns_candidates(sdp: str, client_ip: str | None) -> str:
    """Replace browser-masked mDNS host candidates with the signaling peer IP."""
    if not client_ip or " typ srflx" in sdp:
        return sdp
    rewritten = []
    for line in sdp.splitlines(keepends=True):
        if line.startswith("a=candidate:"):
            ending = "\r\n" if line.endswith("\r\n") else ("\n" if line.endswith("\n") else "")
            fields = line.rstrip("\r\n").split(" ")
            if len(fields) >= 8 and fields[4].endswith(".local") and fields[7] == "host":
                fields[4] = client_ip
                line = " ".join(fields) + ending
        rewritten.append(line)
    return "".join(rewritten)


async def close_peer(session_id: str) -> None:
    pc = peer_connections.pop(session_id, None)
    peer_slots.pop(session_id, None)
    peer_clients.pop(session_id, None)
    if pc is not None:
        await pc.close()


async def close_slot_peers(slot_id: int) -> None:
    sessions = [session_id for session_id, current_slot in peer_slots.items() if current_slot == slot_id]
    await asyncio.gather(*(close_peer(session_id) for session_id in sessions), return_exceptions=True)


async def expire_unconnected_peer(session_id: str, timeout_seconds: float = 20) -> None:
    await asyncio.sleep(timeout_seconds)
    pc = peer_connections.get(session_id)
    if pc is not None and pc.connectionState != "connected":
        await close_peer(session_id)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    stun_transport = None
    if config.STUN_PORT > 0:
        loop = asyncio.get_running_loop()
        stun_transport, _ = await loop.create_datagram_endpoint(
            StunBindingProtocol,
            local_addr=(config.STUN_HOST, config.STUN_PORT),
        )
    for slot_id in (1, 2, 3):
        try:
            await registry.subscribe(slot_id)
        except HTTPException as exc:
            if exc.status_code != 409:
                log.warning("摄像头 %s 自动帧发布启动失败: %s", slot_id, exc.detail)
    try:
        yield
    finally:
        if stun_transport is not None:
            stun_transport.close()
        await asyncio.gather(*(pc.close() for pc in tuple(peer_connections.values())), return_exceptions=True)
        peer_connections.clear()
        peer_slots.clear()
        peer_clients.clear()
        await registry.close()


app = FastAPI(title="VisionDrive WebRTC Camera Gateway", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, Any]:
    session_details = []
    for session_id, pc in tuple(peer_connections.items()):
        stats = await pc.getStats()
        outbound = next((item for item in stats.values() if item.type == "outbound-rtp" and item.kind == "video"), None)
        session_details.append({
            "sessionId": session_id,
            "slotId": peer_slots.get(session_id),
            "connectionState": pc.connectionState,
            "iceConnectionState": pc.iceConnectionState,
            "packetsSent": getattr(outbound, "packetsSent", 0),
            "bytesSent": getattr(outbound, "bytesSent", 0),
        })
    return {
        "status": "ok",
        "service": "VisionDrive WebRTC Camera Gateway",
        "cameraStateFile": str(config.CAMERA_STATE_FILE),
        "sessions": len(peer_connections),
        "sessionDetails": session_details,
        "transport": "WebRTC/ICE (TURN TCP/UDP)",
        "stunPort": config.STUN_PORT,
        "framePublishFps": config.FRAME_PUBLISH_FPS,
    }


@app.get("/api/v1/webrtc/ice-config")
async def ice_config() -> dict[str, Any]:
    """Issue a short-lived coturn REST credential without exposing the shared secret."""
    if not config.TURN_SECRET:
        raise HTTPException(status_code=503, detail="TURN 中继凭证尚未配置")
    expires_at = int(time.time()) + config.TURN_TTL_SECONDS
    username = f"{expires_at}:visiondrive"
    digest = hmac.new(
        config.TURN_SECRET.encode("utf-8"),
        username.encode("utf-8"),
        hashlib.sha1,
    ).digest()
    credential = base64.b64encode(digest).decode("ascii")
    host = config.PUBLIC_HOST
    port = config.TURN_PORT
    return {
        "iceTransportPolicy": "relay" if config.TURN_FORCE_RELAY else "all",
        "expiresAt": expires_at,
        "iceServers": [{
            "urls": [
                f"turn:{host}:{port}?transport=tcp",
                f"turn:{host}:{port}?transport=udp",
            ],
            "username": username,
            "credential": credential,
        }],
    }


@app.post("/api/v1/webrtc/offer/{slot_id}")
async def offer(slot_id: int, request: dict[str, Any], http_request: Request) -> dict[str, str]:
    if request.get("type") != "offer" or not request.get("sdp"):
        raise HTTPException(status_code=400, detail="需要有效的 WebRTC offer")

    client_ip = http_request.client.host if http_request.client else "unknown"
    client_key = str(request.get("clientId") or client_ip)[:128]
    session_id = uuid.uuid4().hex
    pc = RTCPeerConnection()
    peer_connections[session_id] = pc
    peer_slots[session_id] = slot_id
    peer_clients[session_id] = client_key

    @pc.on("connectionstatechange")
    async def on_connectionstatechange() -> None:
        log.info("WebRTC session=%s slot=%s state=%s", session_id, slot_id, pc.connectionState)
        if pc.connectionState == "connected":
            superseded = [
                current_id for current_id, current_slot in tuple(peer_slots.items())
                if current_id != session_id
                and current_slot == slot_id
                and peer_clients.get(current_id) == client_key
                and peer_connections.get(current_id) is not None
                and peer_connections[current_id].connectionState == "connected"
            ]
            await asyncio.gather(*(close_peer(current_id) for current_id in superseded), return_exceptions=True)
        elif pc.connectionState in {"failed", "closed"}:
            await close_peer(session_id)

    try:
        remote_sdp = expose_mdns_candidates(request["sdp"], client_ip)
        await pc.setRemoteDescription(RTCSessionDescription(sdp=remote_sdp, type=request["type"]))
        pc.addTrack(await registry.subscribe(slot_id))
        prefer_vp8(pc)
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        asyncio.create_task(expire_unconnected_peer(session_id))
    except HTTPException:
        await close_peer(session_id)
        raise
    except Exception as exc:  # noqa: BLE001
        await close_peer(session_id)
        log.exception("创建 WebRTC 会话失败: slot=%s", slot_id)
        raise HTTPException(status_code=503, detail=f"创建 WebRTC 视频失败: {exc}") from exc

    return {
        "sessionId": session_id,
        "sdp": pc.localDescription.sdp,
        "type": pc.localDescription.type,
    }


@app.delete("/api/v1/webrtc/session/{session_id}")
async def close_session(session_id: str) -> dict[str, str]:
    await close_peer(session_id)
    return {"status": "closed", "sessionId": session_id}


if __name__ == "__main__":
    uvicorn.run("webrtc.main:app", host=config.HOST, port=config.PORT, workers=1)
