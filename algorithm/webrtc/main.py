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
from collections import deque
from contextlib import asynccontextmanager
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

import numpy as np
import uvicorn
from aioice import stun
from aiortc import RTCPeerConnection, RTCRtpSender, RTCSessionDescription, VideoStreamTrack
from aiortc.contrib.media import MediaRelay
from aiortc.mediastreams import MediaStreamError
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
    """Deep-copy relayed frames without changing the source resolution."""

    def __init__(self, source: VideoStreamTrack):
        super().__init__()
        self.source = source

    async def recv(self) -> VideoFrame:
        frame = await self.source.recv()
        # MediaRelay intentionally shares one AVFrame object.  The RTP encoder runs
        # on a worker thread while the snapshot path converts that same object, so
        # handing the shared native frame to the encoder can corrupt its refcount.
        # Materializing a new ndarray/VideoFrame gives each encoder sole ownership.
        pixels = frame.to_ndarray(format="rgb24")
        copied = VideoFrame.from_ndarray(pixels.copy(), format="rgb24")
        copied.pts = frame.pts
        if frame.time_base is not None:
            copied.time_base = frame.time_base
        return copied

    def stop(self) -> None:
        self.source.stop()
        super().stop()


class DelayedVideoTrack(VideoStreamTrack):
    """Hold a bounded number of source frames before releasing them to WebRTC."""

    def __init__(self, source: VideoStreamTrack, delay_ms: int):
        super().__init__()
        self.source = source
        self.delay_frames = max(0, round(delay_ms * config.OUTPUT_FPS / 1000))
        self._buffer: deque[VideoFrame] = deque(maxlen=self.delay_frames + 1)
        self._primed = False

    async def recv(self) -> VideoFrame:
        if not self._primed:
            while len(self._buffer) < self.delay_frames:
                self._buffer.append(await self.source.recv())
            self._primed = True
        self._buffer.append(await self.source.recv())
        return self._buffer.popleft()

    def stop(self) -> None:
        self._buffer.clear()
        self.source.stop()
        super().stop()


class FfmpegProcessTrack(VideoStreamTrack):
    """Decode one source in an isolated FFmpeg process to protect the gateway."""

    def __init__(self, input_args: list[str], probe_args: list[str] | None = None):
        super().__init__()
        self.input_args = input_args
        self.probe_args = probe_args or []
        self.process: asyncio.subprocess.Process | None = None
        self.output_width = config.FALLBACK_WIDTH
        self.output_height = config.FALLBACK_HEIGHT
        self.frame_size = self.output_width * self.output_height * 3
        self._preserving_source_resolution = False

    async def _probe_source_dimensions(self) -> tuple[int, int] | None:
        if not config.PRESERVE_SOURCE_RESOLUTION or not self.probe_args:
            return None
        process = await asyncio.create_subprocess_exec(
            config.FFPROBE_BINARY,
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=p=0:s=x",
            *self.probe_args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=config.PROBE_TIMEOUT_SECONDS,
            )
        except TimeoutError:
            process.kill()
            await process.wait()
            log.warning("FFprobe 探测视频源分辨率超时，已拒绝降采样")
            return None
        if process.returncode != 0:
            detail = stderr.decode("utf-8", errors="replace").strip()
            log.warning("FFprobe 探测视频源分辨率失败，已拒绝降采样: %s", detail)
            return None
        try:
            width_text, height_text = stdout.decode("ascii").strip().split("x", 1)
            width, height = int(width_text), int(height_text)
        except (ValueError, TypeError):
            log.warning("FFprobe 返回了无效分辨率 %r，已拒绝降采样", stdout)
            return None
        if width < 2 or height < 2:
            return None
        return width, height

    async def _start(self) -> None:
        dimensions = await self._probe_source_dimensions()
        if config.PRESERVE_SOURCE_RESOLUTION and self.probe_args and dimensions is None:
            raise RuntimeError("无法确认视频源原始分辨率，已拒绝降采样")
        self._preserving_source_resolution = dimensions is not None
        if dimensions is not None:
            self.output_width, self.output_height = dimensions
            filter_graph = f"fps={config.OUTPUT_FPS}"
        else:
            self.output_width = config.FALLBACK_WIDTH
            self.output_height = config.FALLBACK_HEIGHT
            filter_graph = (
                f"scale={self.output_width}:{self.output_height}:force_original_aspect_ratio=decrease,"
                f"pad={self.output_width}:{self.output_height}:(ow-iw)/2:(oh-ih)/2,fps={config.OUTPUT_FPS}"
            )
        self.frame_size = self.output_width * self.output_height * 3
        log.info(
            "WebRTC 视频源解码尺寸: %sx%s (%s)",
            self.output_width,
            self.output_height,
            "原始分辨率" if self._preserving_source_resolution else "保底分辨率",
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
        while self.readyState == "live":
            if self.process is None or self.process.returncode is not None:
                await self._start()
            try:
                payload = await asyncio.wait_for(
                    self.process.stdout.readexactly(self.frame_size),
                    timeout=config.FRAME_READ_TIMEOUT_SECONDS,
                )
            except (asyncio.IncompleteReadError, TimeoutError) as exc:
                reason = "超时" if isinstance(exc, TimeoutError) else "中断"
                log.warning("FFmpeg 视频源读帧%s，%.1fs 后未收到完整帧，正在重连", reason, config.FRAME_READ_TIMEOUT_SECONDS)
                await self._stop_process()
                await asyncio.sleep(0.2)
                continue
            pts, time_base = await self.next_timestamp()
            array = np.frombuffer(payload, dtype=np.uint8).reshape(self.output_height, self.output_width, 3)
            frame = VideoFrame.from_ndarray(array, format="rgb24")
            frame.pts = pts
            frame.time_base = time_base
            return frame
        raise MediaStreamError

    async def _stop_process(self) -> None:
        process, self.process = self.process, None
        if process is not None and process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=2)
            except TimeoutError:
                process.kill()
                await process.wait()

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

    async def subscribe(self, slot_id: int, delay_ms: int = 0) -> VideoStreamTrack:
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
            if delay_ms > 0:
                track = DelayedVideoTrack(track, delay_ms)
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
                await asyncio.to_thread(self._save_frame, slot_id, frame, output)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            log.warning("摄像头 %s 帧发布中断: %s", slot_id, exc)
            await close_slot_peers(slot_id)

    @staticmethod
    def _save_frame(slot_id: int, frame: VideoFrame, output: Path) -> None:
        """Publish a JPEG and a verifiable frame manifest for inference consumers.

        The Java service reads the manifest before and after copying the JPEG and
        verifies the checksum.  That prevents an inference request from opening a
        different frame after this continuously-updated file has been replaced.
        """
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_name(f".{output.name}.webrtc.tmp")
        buffer = BytesIO()
        frame.to_image().save(
            buffer,
            format="JPEG",
            quality=config.SNAPSHOT_JPEG_QUALITY,
            subsampling=0,
        )
        payload = buffer.getvalue()
        captured_at_ms = time.time_ns() // 1_000_000
        frame_pts = int(frame.pts) if frame.pts is not None else None
        frame_id = f"{slot_id}-{frame_pts if frame_pts is not None else 'na'}-{captured_at_ms}"
        metadata = {
            "frameId": frame_id,
            "framePts": frame_pts,
            "frameTimeBase": str(frame.time_base) if frame.time_base is not None else None,
            "frameCapturedAtMs": captured_at_ms,
            "sha256": hashlib.sha256(payload).hexdigest(),
        }

        temporary.write_bytes(payload)
        temporary.replace(output)
        metadata_output = output.with_suffix(".meta.json")
        metadata_temporary = metadata_output.with_name(f".{metadata_output.name}.webrtc.tmp")
        metadata_temporary.write_text(
            json.dumps(metadata, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        metadata_temporary.replace(metadata_output)

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
            device_path = f"/dev/video{device_index}"
            input_args = ["-f", "v4l2", "-framerate", str(config.OUTPUT_FPS), "-i", device_path]
            probe_args = ["-f", "v4l2", "-i", device_path]
        elif source_type == "VIDEO":
            if not Path(path).is_file():
                raise HTTPException(status_code=404, detail=f"视频不存在: {path}")
            input_args = ["-stream_loop", "-1", "-re", "-i", path]
            probe_args = [path]
        elif source_type in {"RTSP", "SANDBOX"}:
            input_args = [
                "-rtsp_transport", "tcp",
                "-fflags", "nobuffer",
                "-flags", "low_delay",
                "-analyzeduration", "500000",
                "-probesize", "500000",
                "-i", path,
            ]
            probe_args = ["-rtsp_transport", "tcp", path]
        else:
            raise HTTPException(status_code=400, detail=f"WebRTC 不支持输入类型: {source_type}")

        track = FfmpegProcessTrack(input_args, probe_args)
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
peer_delays: dict[str, int] = {}


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
    peer_delays.pop(session_id, None)
    if pc is not None:
        for sender in pc.getSenders():
            if sender.track is not None:
                sender.track.stop()
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
        peer_delays.clear()
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
            "delayMs": peer_delays.get(session_id, 0),
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
        "outputFps": config.OUTPUT_FPS,
        "preserveSourceResolution": config.PRESERVE_SOURCE_RESOLUTION,
        "fallbackResolution": {
            "width": config.FALLBACK_WIDTH,
            "height": config.FALLBACK_HEIGHT,
        },
        "snapshotJpegQuality": config.SNAPSHOT_JPEG_QUALITY,
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
async def offer(slot_id: int, request: dict[str, Any], http_request: Request) -> dict[str, Any]:
    if request.get("type") != "offer" or not request.get("sdp"):
        raise HTTPException(status_code=400, detail="需要有效的 WebRTC offer")

    client_ip = http_request.client.host if http_request.client else "unknown"
    try:
        delay_ms = max(0, min(2000, int(request.get("delayMs") or 0)))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="delayMs 必须是 0-2000 之间的整数") from exc
    client_key = f"{str(request.get('clientId') or client_ip)[:120]}:{delay_ms}"
    session_id = uuid.uuid4().hex
    pc = RTCPeerConnection()
    peer_connections[session_id] = pc
    peer_slots[session_id] = slot_id
    peer_clients[session_id] = client_key
    peer_delays[session_id] = delay_ms

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
        pc.addTrack(await registry.subscribe(slot_id, delay_ms=delay_ms))
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
        "delayMs": delay_ms,
    }


@app.delete("/api/v1/webrtc/session/{session_id}")
async def close_session(session_id: str) -> dict[str, str]:
    await close_peer(session_id)
    return {"status": "closed", "sessionId": session_id}


if __name__ == "__main__":
    uvicorn.run("webrtc.main:app", host=config.HOST, port=config.PORT, workers=1)
