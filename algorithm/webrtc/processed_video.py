"""Backend rendering for frame-synchronised recognition video and JPEG frames."""
from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import deque
from dataclasses import dataclass
from functools import lru_cache
from fractions import Fraction
from pathlib import Path
from typing import Any

import numpy as np
from aiortc import VideoStreamTrack
from av import VideoFrame
from PIL import ImageDraw, ImageFont

from . import config

log = logging.getLogger("visiondrive.webrtc.processed")

SUPPORTED_TASKS = {"license_plate", "vehicle_type", "police_gesture"}
POLICE_BONES = (
    ("nose", "neck"),
    ("neck", "right_shoulder"), ("right_shoulder", "right_elbow"), ("right_elbow", "right_wrist"),
    ("neck", "left_shoulder"), ("left_shoulder", "left_elbow"), ("left_elbow", "left_wrist"),
    ("right_shoulder", "left_shoulder"),
    ("right_shoulder", "right_hip"), ("right_hip", "right_knee"), ("right_knee", "right_ankle"),
    ("left_shoulder", "left_hip"), ("left_hip", "left_knee"), ("left_knee", "left_ankle"),
    ("right_hip", "left_hip"),
)


@dataclass(frozen=True)
class OverlaySnapshot:
    task_type: str
    slot_id: int
    frame_id: str | None
    frame_pts: int | None
    frame_time_base: str | None
    frame_captured_at_ms: int | None
    published_at_ms: int | None
    frame_path: str | None
    image_width: int
    image_height: int
    detections: tuple[dict[str, Any], ...]


class ProcessedResultStore:
    """Read atomic Java manifests and retain enough history for delayed playback."""

    def __init__(self, frame_dir: Path):
        self.result_dir = frame_dir / "processed-results"
        self._mtimes: dict[tuple[int, str], int] = {}
        self._history: dict[tuple[int, str], deque[OverlaySnapshot]] = {}

    def result_for(
        self,
        slot_id: int,
        task_type: str,
        frame: VideoFrame,
        source_type: str = "VIDEO",
    ) -> OverlaySnapshot | None:
        key = (slot_id, task_type)
        self._refresh(key)
        history = self._history.get(key, ())
        if not history:
            return None

        # A still image is repeated with new RTP timestamps although its pixels do
        # not change.  The latest inference therefore remains an exact visual match
        # and must stay visible instead of expiring like a video result.
        if source_type.upper() == "IMAGE":
            return history[-1]

        if frame.pts is None or frame.time_base is None:
            return None
        frame_time = Fraction(int(frame.pts)) * Fraction(frame.time_base)
        best: OverlaySnapshot | None = None
        best_delta_ms: float | None = None
        for snapshot in history:
            if snapshot.frame_pts is None or not snapshot.frame_time_base:
                continue
            try:
                snapshot_time = Fraction(snapshot.frame_pts) * Fraction(snapshot.frame_time_base)
            except (ValueError, ZeroDivisionError):
                continue
            delta_ms = abs(float(frame_time - snapshot_time) * 1000)
            if best_delta_ms is None or delta_ms < best_delta_ms:
                best = snapshot
                best_delta_ms = delta_ms
        if best_delta_ms is None or best_delta_ms > config.PROCESSED_FRAME_MATCH_TOLERANCE_MS:
            return None
        return best

    def latest(self, slot_id: int, task_type: str) -> OverlaySnapshot | None:
        key = (slot_id, task_type)
        self._refresh(key)
        history = self._history.get(key, ())
        return history[-1] if history else None

    def _refresh(self, key: tuple[int, str]) -> None:
        slot_id, task_type = key
        path = self.result_dir / f"{task_type}-camera-{slot_id}.json"
        try:
            mtime = path.stat().st_mtime_ns
            if self._mtimes.get(key) == mtime:
                return
            payload = json.loads(path.read_text(encoding="utf-8"))
            snapshot = self._snapshot(payload, slot_id, task_type)
        except FileNotFoundError:
            return
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            log.warning("读取后端叠框结果失败: task=%s slot=%s error=%s", task_type, slot_id, exc)
            return
        self._mtimes[key] = mtime
        history = self._history.setdefault(key, deque(maxlen=config.PROCESSED_RESULT_HISTORY))
        if history and history[-1].frame_pts == snapshot.frame_pts:
            history[-1] = snapshot
        else:
            history.append(snapshot)

    @staticmethod
    def _snapshot(payload: dict[str, Any], slot_id: int, task_type: str) -> OverlaySnapshot:
        image = payload.get("image") or {}
        frame_pts = payload.get("framePts")
        return OverlaySnapshot(
            task_type=task_type,
            slot_id=slot_id,
            frame_id=str(payload.get("frameId")) if payload.get("frameId") is not None else None,
            frame_pts=int(frame_pts) if frame_pts is not None else None,
            frame_time_base=payload.get("frameTimeBase"),
            frame_captured_at_ms=_optional_int(payload.get("frameCapturedAtMs")),
            published_at_ms=_optional_int(payload.get("publishedAtMs")),
            frame_path=str(payload.get("framePath")) if payload.get("framePath") else None,
            image_width=max(1, int(image.get("width") or config.PROCESSED_MAX_WIDTH)),
            image_height=max(1, int(image.get("height") or config.PROCESSED_MAX_HEIGHT)),
            detections=tuple(payload.get("detections") or ()),
        )


class ProcessedVideoTrack(VideoStreamTrack):
    """Delay source video, render matching inference data, and keep RTP continuous."""

    def __init__(
        self,
        source: VideoStreamTrack,
        slot_id: int,
        task_type: str,
        result_store: ProcessedResultStore,
        delay_ms: int,
        source_type: str = "VIDEO",
        initial_frames: list[VideoFrame] | None = None,
    ):
        if task_type not in SUPPORTED_TASKS:
            raise ValueError(f"unsupported processed task: {task_type}")
        super().__init__()
        self.source = source
        self.slot_id = slot_id
        self.task_type = task_type
        self.result_store = result_store
        self.source_type = source_type.upper()
        self.delay_frames = (
            0 if self.source_type == "IMAGE"
            else max(1, round(delay_ms * config.OUTPUT_FPS / 1000))
        )
        self._buffer: deque[VideoFrame] = deque(maxlen=self.delay_frames + 1)
        if self.delay_frames and initial_frames:
            # History is shared by future processed subscriptions.  Clone it now so
            # two annotator worker threads never read the same native AVFrame.
            self._buffer.extend(
                self.clone_frame(frame)
                for frame in initial_frames[-self.delay_frames:]
            )
        self._primed = self.delay_frames == 0 or len(self._buffer) >= self.delay_frames
        self._output_pts = 0
        self._output_time_base = Fraction(1, 90_000)
        self._output_pts_step = max(1, round(90_000 / config.OUTPUT_FPS))
        self.started_at = time.monotonic()
        self.frames_sent = 0
        self.last_frame_at: float | None = None
        self.last_error: str | None = None

    async def recv(self) -> VideoFrame:
        try:
            if not self._primed:
                while len(self._buffer) < self.delay_frames:
                    source_frame = await self.source.recv()
                    pixels, pts, time_base = self.detach_frame(source_frame)
                    self._buffer.append(await asyncio.to_thread(
                        self.compact_pixels, pixels, pts, time_base
                    ))
                self._primed = True
            source_frame = await self.source.recv()
            pixels, pts, time_base = self.detach_frame(source_frame)
            compact = await asyncio.to_thread(
                self.compact_pixels, pixels, pts, time_base
            )
            if self.delay_frames:
                self._buffer.append(compact)
                frame = self._buffer.popleft()
            else:
                frame = compact
            snapshot = await asyncio.to_thread(
                self.result_store.result_for,
                self.slot_id,
                self.task_type,
                frame,
                self.source_type,
            )
            rendered = await asyncio.to_thread(annotate_frame, frame, self.task_type, snapshot)

            # Source PTS may restart or jump when a looped file / RTSP source is
            # reconnected.  RTP senders require a strictly monotonic clock, so the
            # processed stream owns a stable 90 kHz output timeline.  Matching an
            # inference result still happens against the original source PTS above.
            rendered.pts = self._output_pts
            rendered.time_base = self._output_time_base
            self._output_pts += self._output_pts_step
            self.frames_sent += 1
            self.last_frame_at = time.monotonic()
            self.last_error = None
            return rendered
        except Exception as exc:  # noqa: BLE001
            self.last_error = f"{type(exc).__name__}: {exc}"
            log.exception(
                "后端处理视频读帧失败: task=%s slot=%s frames=%s",
                self.task_type,
                self.slot_id,
                self.frames_sent,
            )
            raise

    def diagnostics(self) -> dict[str, Any]:
        now = time.monotonic()
        return {
            "framesSent": self.frames_sent,
            "sourceType": self.source_type,
            "bufferedFrames": len(self._buffer),
            "strictFrameMatching": self.source_type != "IMAGE",
            "runningSeconds": round(now - self.started_at, 3),
            "lastFrameAgeMs": (
                round((now - self.last_frame_at) * 1000, 1)
                if self.last_frame_at is not None
                else None
            ),
            "lastError": self.last_error,
        }

    @staticmethod
    def detach_frame(frame: VideoFrame) -> tuple[np.ndarray, int | None, Fraction | None]:
        """Copy a relay-owned AVFrame before crossing an asyncio thread boundary."""
        pixels = frame.to_ndarray(format="rgb24").copy()
        pts = int(frame.pts) if frame.pts is not None else None
        time_base = Fraction(frame.time_base) if frame.time_base is not None else None
        return pixels, pts, time_base

    @staticmethod
    def compact_pixels(
        pixels: np.ndarray,
        pts: int | None,
        time_base: Fraction | None,
    ) -> VideoFrame:
        source = VideoFrame.from_ndarray(pixels, format="rgb24")
        scale = min(
            1.0,
            config.PROCESSED_MAX_WIDTH / max(source.width, 1),
            config.PROCESSED_MAX_HEIGHT / max(source.height, 1),
        )
        width = max(2, int(source.width * scale) // 2 * 2)
        height = max(2, int(source.height * scale) // 2 * 2)
        compact = source.reformat(width=width, height=height, format="rgb24")
        compact.pts = pts
        if time_base is not None:
            compact.time_base = time_base
        return compact

    @classmethod
    def compact_frame(cls, frame: VideoFrame) -> VideoFrame:
        pixels, pts, time_base = cls.detach_frame(frame)
        return cls.compact_pixels(pixels, pts, time_base)

    @staticmethod
    def clone_frame(frame: VideoFrame) -> VideoFrame:
        pixels, pts, time_base = ProcessedVideoTrack.detach_frame(frame)
        cloned = VideoFrame.from_ndarray(pixels, format="rgb24")
        cloned.pts = pts
        if time_base is not None:
            cloned.time_base = time_base
        return cloned

    def stop(self) -> None:
        self._buffer.clear()
        self.source.stop()
        super().stop()


def annotate_frame(
    frame: VideoFrame,
    task_type: str,
    snapshot: OverlaySnapshot | None,
) -> VideoFrame:
    image = annotate_image(frame.to_image(), task_type, snapshot)

    rendered = VideoFrame.from_ndarray(np.asarray(image, dtype=np.uint8), format="rgb24")
    rendered.pts = frame.pts
    if frame.time_base is not None:
        rendered.time_base = frame.time_base
    return rendered


def annotate_image(
    source: Any,
    task_type: str,
    snapshot: OverlaySnapshot | None,
):
    """Draw backend inference data onto the exact image used by the algorithm."""
    image = source.convert("RGB")
    draw = ImageDraw.Draw(image)
    scale_x = image.width / max(snapshot.image_width, 1) if snapshot else 1.0
    scale_y = image.height / max(snapshot.image_height, 1) if snapshot else 1.0
    line_width = max(2, image.width // 360)
    font = _font(max(14, image.width // 58))
    small_font = _font(max(12, image.width // 75))

    if snapshot:
        if task_type == "police_gesture":
            _draw_police(draw, snapshot.detections, scale_x, scale_y, line_width, font)
        else:
            _draw_boxes(draw, task_type, snapshot.detections, scale_x, scale_y, line_width, font)

    status = {
        "license_plate": "BACKEND AI · PLATE",
        "vehicle_type": "BACKEND AI · VEHICLE",
        "police_gesture": "BACKEND AI · POLICE POSE",
    }.get(task_type, "BACKEND AI")
    if snapshot is None:
        status += " · WAITING"
    _draw_badge(draw, (12, 12), status, small_font, (0, 180, 216))

    return image


def _draw_boxes(
    draw: ImageDraw.ImageDraw,
    task_type: str,
    detections: tuple[dict[str, Any], ...],
    scale_x: float,
    scale_y: float,
    line_width: int,
    font: ImageFont.ImageFont,
) -> None:
    for detection in detections:
        box = detection.get("bbox") or {}
        if not _valid_box(box):
            continue
        xy = _scaled_box(box, scale_x, scale_y)
        color = _plate_color(detection) if task_type == "license_plate" else (0, 229, 255)
        draw.rectangle(xy, outline=color, width=line_width)
        if task_type == "license_plate":
            label = "{} · {:.0f}%".format(
                detection.get("plateNumber") or "PLATE",
                100 * _confidence(detection),
            )
        else:
            vehicle_type = detection.get("vehicleTypeName") or detection.get("vehicleType") or "VEHICLE"
            label = "#{} · {} · {:.0f}%".format(
                detection.get("trackId", "--"), vehicle_type, 100 * _confidence(detection)
            )
        _draw_badge(draw, (xy[0], max(0, xy[1] - _text_height(draw, label, font) - 8)), label, font, color)


def _draw_police(
    draw: ImageDraw.ImageDraw,
    detections: tuple[dict[str, Any], ...],
    scale_x: float,
    scale_y: float,
    line_width: int,
    font: ImageFont.ImageFont,
) -> None:
    for detection in detections:
        points = {
            point.get("name"): (
                int(float(point.get("x", 0)) * scale_x),
                int(float(point.get("y", 0)) * scale_y),
            )
            for point in detection.get("keypoints") or ()
            if point.get("name") and float(point.get("score", 1) or 0) > 0.05
        }
        for first, second in POLICE_BONES:
            if first in points and second in points:
                draw.line((*points[first], *points[second]), fill=(0, 230, 118), width=line_width + 1)
        radius = max(3, line_width + 1)
        for x, y in points.values():
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(0, 180, 216), outline=(7, 11, 18))
        box = detection.get("bbox") or {}
        if _valid_box(box):
            xy = _scaled_box(box, scale_x, scale_y)
            label = "{} · {:.0f}%".format(
                detection.get("gestureName") or "POSE", 100 * _confidence(detection)
            )
            _draw_badge(draw, (xy[0], max(0, xy[1] - _text_height(draw, label, font) - 8)), label, font, (0, 230, 118))


def _draw_badge(
    draw: ImageDraw.ImageDraw,
    origin: tuple[int, int],
    text: str,
    font: ImageFont.ImageFont,
    accent: tuple[int, int, int],
) -> None:
    text = _safe_text(font, text)
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    width = right - left + 18
    height = bottom - top + 12
    x, y = origin
    draw.rounded_rectangle((x, y, x + width, y + height), radius=6, fill=(7, 11, 18), outline=accent, width=2)
    draw.text((x + 9, y + 5), text, fill=(238, 242, 247), font=font)


def _text_height(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    text = _safe_text(font, text)
    _, top, _, bottom = draw.textbbox((0, 0), text, font=font)
    return bottom - top


def _valid_box(box: dict[str, Any]) -> bool:
    try:
        return float(box["x2"]) > float(box["x1"]) and float(box["y2"]) > float(box["y1"])
    except (KeyError, TypeError, ValueError):
        return False


def _scaled_box(box: dict[str, Any], scale_x: float, scale_y: float) -> tuple[int, int, int, int]:
    return (
        int(float(box["x1"]) * scale_x), int(float(box["y1"]) * scale_y),
        int(float(box["x2"]) * scale_x), int(float(box["y2"]) * scale_y),
    )


def _confidence(detection: dict[str, Any]) -> float:
    for key in ("ocrConfidence", "confidence", "detectionConfidence"):
        try:
            value = float(detection.get(key))
        except (TypeError, ValueError):
            continue
        if np.isfinite(value):
            return max(0.0, min(1.0, value))
    return 0.0


def _plate_color(detection: dict[str, Any]) -> tuple[int, int, int]:
    value = str(detection.get("plateColor") or detection.get("plateType") or "").lower()
    if "blue" in value or "蓝" in value:
        return 77, 163, 255
    if "green" in value or "绿" in value:
        return 0, 230, 118
    if "yellow" in value or "黄" in value:
        return 255, 212, 59
    return 0, 229, 255


@lru_cache(maxsize=8)
def _font(size: int) -> ImageFont.ImageFont:
    for path in (
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        try:
            if Path(path).is_file():
                return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _safe_text(font: ImageFont.ImageFont, text: str) -> str:
    value = str(text or "")
    try:
        font.getmask(value)
        return value
    except UnicodeEncodeError:
        return value.encode("ascii", errors="replace").decode("ascii")


def _optional_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None
