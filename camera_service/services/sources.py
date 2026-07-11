"""Camera source discovery and frame acquisition."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import threading
import time
from collections import OrderedDict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

os.environ.setdefault("OPENCV_AVFOUNDATION_SKIP_AUTH", "1")

import cv2
import numpy as np

from config import (
    CAMERA_STATE_FILE,
    DEFAULT_FPS,
    DEFAULT_HEIGHT,
    DEFAULT_WIDTH,
    IMAGE_EXTENSIONS,
    JPEG_QUALITY,
    LICENSE_PLATE_SAMPLE_DIR,
    OWNER_GESTURE_SOURCE_DIR,
    POLICE_GESTURE_SAMPLE_DIR,
    VIDEO_EXTENSIONS,
)


SourceType = Literal["browser", "device", "image", "video", "rtsp"]
BROWSER_CAMERA_SOURCE_ID = "browser-camera"
ALL_TASK_TYPES = ["license_plate", "police_gesture", "owner_gesture"]
MAX_OPEN_READERS = 12
_BROWSER_FRAME_LOCK = threading.RLock()
_BROWSER_FRAME: np.ndarray | None = None
_BROWSER_FRAME_BYTES: bytes | None = None
_BROWSER_FRAME_CONTENT_TYPE = "image/jpeg"
_BROWSER_FRAME_UPDATED_AT = 0.0
_BROWSER_FRAME_INDEX = -1
_BROWSER_FRAME_WIDTH = 0
_BROWSER_FRAME_HEIGHT = 0


@dataclass
class CameraSource:
    id: str
    name: str
    sourceType: SourceType
    taskTypes: list[str] = field(default_factory=list)
    path: str | None = None
    deviceIndex: int | None = None
    rtspUrl: str | None = None
    fps: int = DEFAULT_FPS
    loop: bool = True
    builtIn: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def build_default_sources() -> list[CameraSource]:
    sources = [
        CameraSource(
            id=BROWSER_CAMERA_SOURCE_ID,
            name="本机前置摄像头（浏览器推流）",
            sourceType="browser",
            taskTypes=ALL_TASK_TYPES,
            fps=DEFAULT_FPS,
            builtIn=True,
        ),
        CameraSource(
            id="front-camera-0",
            name="OpenCV 摄像头 0（备用）",
            sourceType="device",
            taskTypes=ALL_TASK_TYPES,
            deviceIndex=0,
            fps=DEFAULT_FPS,
            builtIn=True,
        )
    ]

    # 沙盘RTSP摄像头
    _RTSP = [
        ("live1","桥面","rtsp://10.126.59.120:8554/live/live1"),
        ("live2","停车场出口","rtsp://10.126.59.120:8554/live/live2"),
        ("live3","行人检测","rtsp://10.126.59.120:8554/live/live3"),
        ("live4","消防车识别","rtsp://10.126.59.120:8554/live/live4"),
        ("live5","桥出口","rtsp://10.126.59.120:8554/live/live5"),
        ("live6","桥入口","rtsp://10.126.59.120:8554/live/live6"),
        ("live7","道路2","rtsp://10.126.59.120:8554/live/live7"),
        ("live8","隧道(事故)","rtsp://10.126.59.120:8554/live/live8"),
        ("live9","隧道(计数)","rtsp://10.126.59.120:8554/live/live9"),
        ("live10","道路3","rtsp://10.126.59.120:8554/live/live10"),
        ("live11","停车场入口","rtsp://10.126.59.120:8554/live/live11"),
        ("live12","道路1","rtsp://10.126.59.120:8554/live/live12"),
    ]
    _PLATE = {"live1","live2","live4","live5","live6","live7","live10","live11","live12"}
    for cid, name, url in _RTSP:
        tasks = ["license_plate"] if cid in _PLATE else ALL_TASK_TYPES
        sources.append(CameraSource(
            id=f"rtsp-{cid}", name=f"沙盘-{name}",
            sourceType="rtsp", taskTypes=tasks,
            rtspUrl=url, fps=25, builtIn=True,
        ))

    sources.extend(_scan_media_sources(
        LICENSE_PLATE_SAMPLE_DIR,
        task_type="license_plate",
        prefix="license-plate",
        title="车牌测试图",
        limit=30,
    ))
    sources.extend(_scan_media_sources(
        POLICE_GESTURE_SAMPLE_DIR,
        task_type="police_gesture",
        prefix="police-gesture",
        title="交警测试视频",
        limit=200,
    ))
    sources.extend(_scan_media_sources(
        OWNER_GESTURE_SOURCE_DIR / "test",
        task_type="owner_gesture",
        prefix="owner-gesture",
        title="手势测试媒体",
        limit=200,
    ))
    return sources


def make_custom_source(
    source_type: SourceType,
    *,
    path: str | None = None,
    device_index: int | None = None,
    name: str | None = None,
    fps: int = DEFAULT_FPS,
    loop: bool = True,
) -> CameraSource:
    if source_type == "device":
        index = 0 if device_index is None else device_index
        return CameraSource(
            id=f"device-{index}",
            name=name or f"本机摄像头 {index}",
            sourceType="device",
            taskTypes=["license_plate", "police_gesture", "owner_gesture"],
            deviceIndex=index,
            fps=fps,
            loop=loop,
            builtIn=False,
        )

    if not path:
        raise ValueError("图片或视频源必须提供 path")

    media_path = Path(path).expanduser().resolve()
    if not media_path.exists():
        raise FileNotFoundError(f"源文件不存在: {media_path}")

    inferred_type = _source_type_from_path(media_path)
    if inferred_type != source_type:
        raise ValueError(f"path 扩展名与 sourceType 不匹配: {media_path.suffix}")

    digest = hashlib.md5(str(media_path).encode("utf-8")).hexdigest()[:10]
    return CameraSource(
        id=f"custom-{inferred_type}-{digest}",
        name=name or media_path.name,
        sourceType=inferred_type,
        path=str(media_path),
        fps=fps,
        loop=loop,
        builtIn=False,
    )


class CameraManager:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.sources: dict[str, CameraSource] = {src.id: src for src in build_default_sources()}
        self._readers: OrderedDict[str, FrameReader] = OrderedDict()
        saved_active_id = self._load_state()
        self.active_source_id = self._initial_active_source_id(saved_active_id)

    def list_sources(self) -> list[dict]:
        with self._lock:
            return [source.to_dict() for source in self.sources.values()]

    def get_active_source(self) -> CameraSource | None:
        with self._lock:
            return self.sources.get(self.active_source_id)

    def add_source(self, source: CameraSource) -> CameraSource:
        with self._lock:
            self.sources[source.id] = source
            self._save_state()
            return source

    def remove_source(self, source_id: str) -> CameraSource:
        with self._lock:
            if source_id not in self.sources:
                raise KeyError(f"未知摄像头源: {source_id}")
            source = self.sources[source_id]
            if source.builtIn:
                raise ValueError("内置摄像头源不能删除")
            removed = self.sources.pop(source_id)
            self._close_reader(source_id)
            if self.active_source_id == source_id:
                self.active_source_id = self._initial_active_source_id(None)
            self._save_state()
            return removed

    def set_active(self, source_id: str) -> CameraSource:
        with self._lock:
            if source_id not in self.sources:
                raise KeyError(f"未知摄像头源: {source_id}")
            if self.active_source_id != source_id:
                self.active_source_id = source_id
                self._save_state()
            return self.sources[source_id]

    def warm_source(self, source_id: str) -> None:
        with self._lock:
            source = self.sources.get(source_id)
            if not source or source.sourceType == "browser":
                return
            reader = self._reader_for(source)
        reader.meta()

    def read_frame(self, source_id: str | None = None) -> np.ndarray:
        frame, _ = self.read_frame_with_meta(source_id)
        return frame

    def read_frame_with_meta(self, source_id: str | None = None) -> tuple[np.ndarray, dict]:
        with self._lock:
            source = self._get_read_source(source_id)
            if not source:
                frame = placeholder_frame("未配置摄像头源")
                return frame, frame_meta(None, frame, 0)
            if source.sourceType == "browser":
                return read_browser_frame_with_meta(source)
            reader = self._reader_for(source)
        return reader.read_with_meta()

    def read_snapshot_frame(self, source_id: str | None = None) -> np.ndarray:
        frame, _ = self.read_snapshot_frame_with_meta(source_id)
        return frame

    def read_snapshot_frame_with_meta(self, source_id: str | None = None) -> tuple[np.ndarray, dict]:
        with self._lock:
            source = self._get_read_source(source_id)
            if not source:
                frame = placeholder_frame("未配置摄像头源")
                return frame, frame_meta(None, frame, 0)
            snapshot_source = source

        if snapshot_source.sourceType == "image" and snapshot_source.path:
            frame = read_image(snapshot_source.path)
            return frame, frame_meta(snapshot_source, frame, 0)
        return self.read_frame_with_meta(snapshot_source.id)

    def read_jpeg_frame_with_meta(
        self,
        source_id: str | None = None,
        quality: int | None = None,
        *,
        preview: bool = False,
    ) -> tuple[bytes, dict]:
        with self._lock:
            source = self._get_read_source(source_id)
            if not source:
                frame = placeholder_frame("未配置摄像头源")
                return encode_jpeg_frame(frame, quality), frame_meta(None, frame, 0)
            if source.sourceType == "browser":
                return read_browser_jpeg_with_meta(source, quality)
            resolved_source_id = source.id

        frame, meta = self.read_frame_with_meta(resolved_source_id)
        if preview:
            frame = resize_to_canvas(frame)
            meta = {**meta, "width": int(frame.shape[1]), "height": int(frame.shape[0])}
        return self.encode_jpeg(frame, quality), meta

    def get_frame_info(self, source_id: str | None = None) -> dict:
        with self._lock:
            source = self._get_read_source(source_id)
            if not source:
                return frame_meta(None, placeholder_frame("未配置摄像头源"), 0)
            if source.sourceType == "browser":
                _, meta = read_browser_frame_with_meta(source)
                return meta
            reader = self._reader_for(source)
        return reader.meta()

    def get_snapshot_image_path(self, source_id: str | None = None) -> Path | None:
        with self._lock:
            source = self._get_read_source(source_id)
            if not source or source.sourceType != "image" or not source.path:
                return None
            path = Path(source.path)
            if not path.exists() or path.suffix.lower() not in {".jpg", ".jpeg"}:
                return None
            return path

    def update_browser_frame(self, frame: np.ndarray, source_id: str = BROWSER_CAMERA_SOURCE_ID) -> CameraSource:
        with self._lock:
            source = self.sources.get(source_id)
            if not source:
                raise KeyError(f"未知摄像头源: {source_id}")
            if source.sourceType != "browser":
                raise ValueError("浏览器帧只能写入浏览器摄像头源")
            update_browser_frame(frame)
            if self.active_source_id != source_id:
                self.active_source_id = source_id
                self._save_state()
            return source

    def update_browser_frame_bytes(
        self,
        raw: bytes,
        source_id: str = BROWSER_CAMERA_SOURCE_ID,
        *,
        content_type: str = "image/jpeg",
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
    ) -> CameraSource:
        with self._lock:
            source = self.sources.get(source_id)
            if not source:
                raise KeyError(f"未知摄像头源: {source_id}")
            if source.sourceType != "browser":
                raise ValueError("浏览器帧只能写入浏览器摄像头源")
            update_browser_frame_bytes(
                raw,
                content_type=content_type,
                width=width,
                height=height,
            )
            if self.active_source_id != source_id:
                self.active_source_id = source_id
                self._save_state()
            return source

    def update_browser_video_frame(
        self,
        frame: np.ndarray,
        source_id: str = BROWSER_CAMERA_SOURCE_ID,
    ) -> CameraSource:
        with self._lock:
            source = self.sources.get(source_id)
            if not source:
                raise KeyError(f"未知摄像头源: {source_id}")
            if source.sourceType != "browser":
                raise ValueError("WebRTC 视频轨道只能写入浏览器摄像头源")
            update_browser_video_frame(frame)
            if self.active_source_id != source_id:
                self.active_source_id = source_id
                self._save_state()
            return source

    def encode_jpeg(self, frame: np.ndarray, quality: int | None = None) -> bytes:
        return encode_jpeg_frame(frame, quality)

    def encode_png(self, frame: np.ndarray) -> bytes:
        ok, buffer = cv2.imencode(".png", frame, [int(cv2.IMWRITE_PNG_COMPRESSION), 1])
        if not ok:
            raise RuntimeError("PNG 编码失败")
        return buffer.tobytes()

    def _reader_for(self, source: CameraSource) -> FrameReader:
        reader = self._readers.get(source.id)
        if reader is None:
            reader = FrameReader(source)
            self._readers[source.id] = reader
        else:
            self._readers.move_to_end(source.id)
        self._trim_readers()
        return reader

    def _close_reader(self, source_id: str | None = None) -> None:
        if source_id is None:
            readers = list(self._readers.values())
            self._readers.clear()
        else:
            reader = self._readers.pop(source_id, None)
            readers = [reader] if reader else []

        for reader in readers:
            reader.close()

    def _trim_readers(self) -> None:
        while len(self._readers) > MAX_OPEN_READERS:
            _, reader = self._readers.popitem(last=False)
            reader.close()

    def _get_read_source(self, source_id: str | None = None) -> CameraSource | None:
        if source_id:
            source = self.sources.get(source_id)
            if not source:
                raise KeyError(f"未知摄像头源: {source_id}")
            return source
        return self.sources.get(self.active_source_id)

    def _initial_active_source_id(self, preferred_source_id: str | None) -> str:
        if preferred_source_id in self.sources:
            preferred = self.sources[preferred_source_id]
            if preferred.sourceType != "device":
                return preferred.id

        for source_type in ("image", "video", "browser", "device"):
            for source in self.sources.values():
                if source.sourceType == source_type:
                    return source.id
        return next(iter(self.sources), "")

    def _load_state(self) -> str | None:
        if not CAMERA_STATE_FILE.exists():
            return None
        try:
            data = json.loads(CAMERA_STATE_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

        for item in data.get("customSources", []):
            try:
                source = CameraSource(
                    id=item["id"],
                    name=item["name"],
                    sourceType=item["sourceType"],
                    taskTypes=list(item.get("taskTypes") or []),
                    path=item.get("path"),
                    deviceIndex=item.get("deviceIndex"),
                    fps=int(item.get("fps") or DEFAULT_FPS),
                    loop=bool(item.get("loop", True)),
                    builtIn=False,
                )
            except (KeyError, TypeError, ValueError):
                continue
            if source.sourceType in {"image", "video"} and source.path and not Path(source.path).exists():
                continue
            self.sources[source.id] = source
        return data.get("activeSourceId")

    def _save_state(self) -> None:
        try:
            CAMERA_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            custom_sources = [
                source.to_dict()
                for source in self.sources.values()
                if not source.builtIn
            ]
            CAMERA_STATE_FILE.write_text(
                json.dumps(
                    {
                        "activeSourceId": self.active_source_id,
                        "customSources": custom_sources,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        except OSError:
            pass


class FrameReader:
    def __init__(self, source: CameraSource) -> None:
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self.source = source
        self.capture: cv2.VideoCapture | None = None
        self.image_frame: np.ndarray | None = None
        self.last_frame: np.ndarray | None = None
        self.frame_index = -1
        self.last_read_at = 0.0
        self.last_timestamp_ms = 0
        self._thread: threading.Thread | None = None
        self._open()

    def _open(self) -> None:
        if self.source.sourceType == "browser":
            self.last_frame = read_browser_frame()
            self._touch_frame(self.last_frame)
            return

        if self.source.sourceType == "image":
            self.image_frame = read_image(self.source.path or "")
            self.last_frame = self.image_frame
            self._touch_frame(self.last_frame, frame_index=0)
            return

        if self.source.sourceType == "rtsp":
            target = self.source.rtspUrl
        else:
            target = self.source.deviceIndex if self.source.sourceType == "device" else self.source.path
        self.capture = cv2.VideoCapture(target, cv2.CAP_FFMPEG if self.source.sourceType == "rtsp" else cv2.CAP_ANY)
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, DEFAULT_WIDTH)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, DEFAULT_HEIGHT)
        self.capture.set(cv2.CAP_PROP_FPS, self.source.fps)
        if self.source.sourceType == "video":
            detected_fps = self.capture.get(cv2.CAP_PROP_FPS) if self.capture else 0
            if detected_fps and np.isfinite(detected_fps):
                self.source.fps = max(1, min(30, int(round(detected_fps))))
        with self._lock:
            self._read_next_locked()
        self._thread = threading.Thread(target=self._run, name=f"camera-reader-{self.source.id}", daemon=True)
        self._thread.start()

    def read(self) -> np.ndarray:
        frame, _ = self.read_with_meta()
        return frame

    def read_with_meta(self) -> tuple[np.ndarray, dict]:
        with self._lock:
            if self.last_frame is None:
                self._read_next_locked()
            frame = self.last_frame.copy() if self.last_frame is not None else placeholder_frame("视频源读取失败")
            return frame, self.meta(frame=frame)

    def meta(self, frame: np.ndarray | None = None) -> dict:
        with self._lock:
            frame = frame if frame is not None else self.last_frame
            if frame is None:
                frame = placeholder_frame("视频源读取失败")
            return frame_meta(
                self.source,
                frame,
                max(0, self.frame_index),
                timestamp_ms=self.last_timestamp_ms or int(time.time() * 1000),
            )

    def close(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        with self._lock:
            if self.capture:
                self.capture.release()
                self.capture = None

    def _run(self) -> None:
        while not self._stop_event.is_set():
            started = time.time()
            with self._lock:
                self._read_next_locked()
            interval = 1 / max(1, self.source.fps)
            self._stop_event.wait(max(0.001, interval - (time.time() - started)))

    def _read_next_locked(self) -> None:
        if self.source.sourceType == "browser":
            self._touch_frame(read_browser_frame())
            return

        if self.source.sourceType == "image":
            frame = self.image_frame if self.image_frame is not None else placeholder_frame("图片源读取失败")
            self._touch_frame(frame, frame_index=0)
            return

        if not self.capture or not self.capture.isOpened():
            self._touch_frame(placeholder_frame(f"{self.source.name} 不可用"))
            return

        ok, frame = self.capture.read()
        if not ok or frame is None:
            if self.source.sourceType == "video" and self.source.loop:
                self.capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ok, frame = self.capture.read()
            if not ok or frame is None:
                if self.last_frame is None:
                    self._touch_frame(placeholder_frame("视频源读取结束"))
                return

        frame_index = None
        if self.source.sourceType == "video":
            frame_index = max(0, int(self.capture.get(cv2.CAP_PROP_POS_FRAMES)) - 1)
        self._touch_frame(resize_to_canvas(frame), frame_index=frame_index)

    def _touch_frame(self, frame: np.ndarray, frame_index: int | None = None) -> None:
        self.last_frame = frame
        self.last_read_at = time.time()
        self.last_timestamp_ms = int(self.last_read_at * 1000)
        if frame_index is None:
            self.frame_index = self.frame_index + 1 if self.frame_index >= 0 else 0
        else:
            self.frame_index = frame_index


def read_image(path: str, *, resize: bool = True) -> np.ndarray:
    data = np.fromfile(path, dtype=np.uint8)
    frame = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if frame is None:
        return placeholder_frame("图片源读取失败")
    if resize:
        return pad_to_16_9(frame)
    return frame


def decode_data_url_image(image: str) -> np.ndarray:
    payload = image.split(",", 1)[1] if "," in image else image
    raw = base64.b64decode(payload)
    return decode_image_bytes(raw)


def decode_image_bytes(raw: bytes) -> np.ndarray:
    frame = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError("浏览器摄像头帧解码失败")
    return frame


def update_browser_frame(frame: np.ndarray) -> None:
    global _BROWSER_FRAME, _BROWSER_FRAME_BYTES, _BROWSER_FRAME_CONTENT_TYPE
    global _BROWSER_FRAME_UPDATED_AT, _BROWSER_FRAME_INDEX, _BROWSER_FRAME_WIDTH, _BROWSER_FRAME_HEIGHT
    frame = resize_to_canvas(frame)
    with _BROWSER_FRAME_LOCK:
        _BROWSER_FRAME = frame
        _BROWSER_FRAME_BYTES = encode_jpeg_frame(frame, 96)
        _BROWSER_FRAME_CONTENT_TYPE = "image/jpeg"
        _BROWSER_FRAME_UPDATED_AT = time.time()
        _BROWSER_FRAME_INDEX += 1
        _BROWSER_FRAME_WIDTH = int(frame.shape[1])
        _BROWSER_FRAME_HEIGHT = int(frame.shape[0])


def update_browser_frame_bytes(
    raw: bytes,
    *,
    content_type: str = "image/jpeg",
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
) -> None:
    global _BROWSER_FRAME, _BROWSER_FRAME_BYTES, _BROWSER_FRAME_CONTENT_TYPE
    global _BROWSER_FRAME_UPDATED_AT, _BROWSER_FRAME_INDEX, _BROWSER_FRAME_WIDTH, _BROWSER_FRAME_HEIGHT
    if not raw:
        raise ValueError("浏览器摄像头帧为空")
    with _BROWSER_FRAME_LOCK:
        _BROWSER_FRAME = None
        _BROWSER_FRAME_BYTES = bytes(raw)
        _BROWSER_FRAME_CONTENT_TYPE = content_type.split(";", 1)[0].strip().lower() or "image/jpeg"
        _BROWSER_FRAME_UPDATED_AT = time.time()
        _BROWSER_FRAME_INDEX += 1
        _BROWSER_FRAME_WIDTH = int(width or DEFAULT_WIDTH)
        _BROWSER_FRAME_HEIGHT = int(height or DEFAULT_HEIGHT)


def update_browser_video_frame(frame: np.ndarray) -> None:
    global _BROWSER_FRAME, _BROWSER_FRAME_BYTES, _BROWSER_FRAME_CONTENT_TYPE
    global _BROWSER_FRAME_UPDATED_AT, _BROWSER_FRAME_INDEX, _BROWSER_FRAME_WIDTH, _BROWSER_FRAME_HEIGHT
    frame = resize_to_canvas(frame)
    with _BROWSER_FRAME_LOCK:
        _BROWSER_FRAME = frame
        _BROWSER_FRAME_BYTES = None
        _BROWSER_FRAME_CONTENT_TYPE = "video/raw"
        _BROWSER_FRAME_UPDATED_AT = time.time()
        _BROWSER_FRAME_INDEX += 1
        _BROWSER_FRAME_WIDTH = int(frame.shape[1])
        _BROWSER_FRAME_HEIGHT = int(frame.shape[0])


def browser_frame_status() -> dict:
    with _BROWSER_FRAME_LOCK:
        return {
            "hasFrame": _BROWSER_FRAME is not None or _BROWSER_FRAME_BYTES is not None,
            "timestampMs": int(_BROWSER_FRAME_UPDATED_AT * 1000) if _BROWSER_FRAME_UPDATED_AT else 0,
            "frameIndex": _BROWSER_FRAME_INDEX,
            "width": int(_BROWSER_FRAME_WIDTH),
            "height": int(_BROWSER_FRAME_HEIGHT),
        }


def read_browser_frame_with_meta(source: CameraSource) -> tuple[np.ndarray, dict]:
    global _BROWSER_FRAME
    with _BROWSER_FRAME_LOCK:
        if _BROWSER_FRAME is None and _BROWSER_FRAME_BYTES is not None:
            decoded = decode_image_bytes(_BROWSER_FRAME_BYTES)
            _BROWSER_FRAME = resize_to_canvas(decoded)
        frame = (
            _BROWSER_FRAME.copy()
            if _BROWSER_FRAME is not None
            else placeholder_frame("等待管理台启动浏览器摄像头")
        )
        return frame, frame_meta(
            source,
            frame,
            max(0, _BROWSER_FRAME_INDEX),
            timestamp_ms=int(_BROWSER_FRAME_UPDATED_AT * 1000) if _BROWSER_FRAME_UPDATED_AT else None,
        )


def read_browser_jpeg_with_meta(source: CameraSource, quality: int | None = None) -> tuple[bytes, dict]:
    with _BROWSER_FRAME_LOCK:
        if _BROWSER_FRAME_BYTES is not None and _BROWSER_FRAME_CONTENT_TYPE == "image/jpeg":
            frame = _BROWSER_FRAME if _BROWSER_FRAME is not None else None
            if frame is not None:
                height, width = frame.shape[:2]
            else:
                width = _BROWSER_FRAME_WIDTH or DEFAULT_WIDTH
                height = _BROWSER_FRAME_HEIGHT or DEFAULT_HEIGHT
            meta = {
                "sourceId": source.id,
                "sourceName": source.name,
                "sourceType": source.sourceType,
                "frameIndex": max(0, int(_BROWSER_FRAME_INDEX)),
                "timestampMs": int(_BROWSER_FRAME_UPDATED_AT * 1000) if _BROWSER_FRAME_UPDATED_AT else int(time.time() * 1000),
                "fps": int(source.fps),
                "width": int(width),
                "height": int(height),
            }
            return bytes(_BROWSER_FRAME_BYTES), meta

    frame, meta = read_browser_frame_with_meta(source)
    return encode_jpeg_frame(frame, quality), meta


def read_browser_frame() -> np.ndarray:
    global _BROWSER_FRAME
    with _BROWSER_FRAME_LOCK:
        if _BROWSER_FRAME is None and _BROWSER_FRAME_BYTES is not None:
            decoded = decode_image_bytes(_BROWSER_FRAME_BYTES)
            _BROWSER_FRAME = resize_to_canvas(decoded)
        if _BROWSER_FRAME is None:
            return placeholder_frame("等待管理台启动浏览器摄像头")
        return _BROWSER_FRAME.copy()


def encode_jpeg_frame(frame: np.ndarray, quality: int | None = None) -> bytes:
    jpeg_quality = max(1, min(100, JPEG_QUALITY if quality is None else quality))
    ok, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality])
    if not ok:
        raise RuntimeError("JPEG 编码失败")
    return buffer.tobytes()


def resize_to_canvas(frame: np.ndarray) -> np.ndarray:
    height, width = frame.shape[:2]
    if width == DEFAULT_WIDTH and height == DEFAULT_HEIGHT:
        return frame
    scale = min(DEFAULT_WIDTH / width, DEFAULT_HEIGHT / height)
    new_width = max(1, int(width * scale))
    new_height = max(1, int(height * scale))
    resized = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)

    canvas = np.zeros((DEFAULT_HEIGHT, DEFAULT_WIDTH, 3), dtype=np.uint8)
    y = (DEFAULT_HEIGHT - new_height) // 2
    x = (DEFAULT_WIDTH - new_width) // 2
    canvas[y:y + new_height, x:x + new_width] = resized
    return canvas


def pad_to_16_9(frame: np.ndarray) -> np.ndarray:
    height, width = frame.shape[:2]
    target_width = width
    target_height = height
    if width * 9 < height * 16:
        target_width = int(np.ceil(height * 16 / 9))
    elif width * 9 > height * 16:
        target_height = int(np.ceil(width * 9 / 16))

    if target_width == width and target_height == height:
        return frame

    canvas = np.zeros((target_height, target_width, 3), dtype=frame.dtype)
    y = (target_height - height) // 2
    x = (target_width - width) // 2
    canvas[y:y + height, x:x + width] = frame
    return canvas


def placeholder_frame(message: str) -> np.ndarray:
    frame = np.zeros((DEFAULT_HEIGHT, DEFAULT_WIDTH, 3), dtype=np.uint8)
    frame[:] = (12, 18, 30)
    cv2.rectangle(frame, (40, 40), (DEFAULT_WIDTH - 40, DEFAULT_HEIGHT - 40), (40, 52, 72), 2)
    cv2.putText(frame, "VisionDrive Virtual Camera", (72, 110), cv2.FONT_HERSHEY_SIMPLEX, 1.25, (0, 180, 216), 3)
    cv2.putText(frame, message, (72, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (210, 220, 235), 2)
    cv2.putText(frame, "Use image/video samples or connect a local camera source.", (72, 235), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (150, 162, 184), 2)
    return frame


def frame_meta(
    source: CameraSource | None,
    frame: np.ndarray,
    frame_index: int,
    *,
    timestamp_ms: int | None = None,
) -> dict:
    height, width = frame.shape[:2]
    return {
        "sourceId": source.id if source else "",
        "sourceName": source.name if source else "",
        "sourceType": source.sourceType if source else "",
        "frameIndex": int(frame_index),
        "timestampMs": int(timestamp_ms or time.time() * 1000),
        "fps": int(source.fps if source else DEFAULT_FPS),
        "width": int(width),
        "height": int(height),
    }


def _scan_media_sources(
    root: Path,
    *,
    task_type: str,
    prefix: str,
    title: str,
    limit: int,
) -> list[CameraSource]:
    if not root.exists():
        return []

    files = sorted(
        path for path in root.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS | VIDEO_EXTENSIONS
    )[:limit]

    sources: list[CameraSource] = []
    for path in files:
        source_type = _source_type_from_path(path)
        fps = media_fps(path) if source_type == "video" else DEFAULT_FPS
        sources.append(CameraSource(
            id=f"{prefix}-{path.stem}",
            name=f"{title} {path.name}",
            sourceType=source_type,
            taskTypes=[task_type],
            path=str(path),
            fps=fps,
            loop=True,
            builtIn=True,
        ))
    return sources


def _source_type_from_path(path: Path) -> SourceType:
    suffix = path.suffix.lower()
    if suffix in IMAGE_EXTENSIONS:
        return "image"
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    raise ValueError(f"不支持的媒体类型: {suffix}")


def media_fps(path: Path) -> int:
    cap = cv2.VideoCapture(str(path))
    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps and np.isfinite(fps):
            return max(1, min(30, int(round(fps))))
    finally:
        cap.release()
    return DEFAULT_FPS
