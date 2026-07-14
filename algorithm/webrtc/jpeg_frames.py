"""Bandwidth-bounded JPEG rendering for browser camera previews."""
from __future__ import annotations

import threading
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image

from . import config
from .processed_video import OverlaySnapshot, annotate_image


@dataclass(frozen=True)
class RenderedJpeg:
    payload: bytes
    frame_id: str
    source: str


class JpegFrameRenderer:
    """Render and cache display JPEGs without changing inference snapshots."""

    def __init__(self, frame_dir: Path):
        self.frame_dir = frame_dir.resolve()
        self.inference_dir = (self.frame_dir / "inference").resolve()
        self._raw_cache: dict[Path, tuple[int, RenderedJpeg]] = {}
        self._processed_cache: dict[tuple[int, str], tuple[str, RenderedJpeg]] = {}
        self._metadata_lock = threading.RLock()
        self._raw_locks: dict[Path, threading.Lock] = {}
        self._processed_locks: dict[tuple[int, str], threading.Lock] = {}

    def raw(self, path: Path) -> RenderedJpeg:
        resolved = path.resolve()
        mtime = resolved.stat().st_mtime_ns
        with self._metadata_lock:
            cached = self._raw_cache.get(resolved)
            if cached and cached[0] == mtime:
                return cached[1]

            render_lock = self._raw_locks.setdefault(resolved, threading.Lock())

        # Only serialize duplicate requests for the same camera frame. Different
        # camera slots are deliberately encoded in parallel by the JPEG executor.
        with render_lock:
            mtime = resolved.stat().st_mtime_ns
            with self._metadata_lock:
                cached = self._raw_cache.get(resolved)
                if cached and cached[0] == mtime:
                    return cached[1]
            image = _scaled_image(resolved)
            rendered = RenderedJpeg(
                payload=_encode_canvas(image),
                frame_id=f"raw-{mtime}",
                source="raw",
            )
            with self._metadata_lock:
                self._raw_cache[resolved] = (mtime, rendered)
            return rendered

    def preencoded(self, path: Path) -> RenderedJpeg:
        """Return an already display-sized JPEG without decoding or re-encoding it."""
        resolved = path.resolve()
        mtime = resolved.stat().st_mtime_ns
        with self._metadata_lock:
            cached = self._raw_cache.get(resolved)
            if cached and cached[0] == mtime:
                return cached[1]
            render_lock = self._raw_locks.setdefault(resolved, threading.Lock())

        with render_lock:
            mtime = resolved.stat().st_mtime_ns
            with self._metadata_lock:
                cached = self._raw_cache.get(resolved)
                if cached and cached[0] == mtime:
                    return cached[1]
            rendered = RenderedJpeg(
                payload=resolved.read_bytes(),
                frame_id=f"display-{mtime}",
                source="raw",
            )
            with self._metadata_lock:
                self._raw_cache[resolved] = (mtime, rendered)
            return rendered

    def processed(
        self,
        slot_id: int,
        task_type: str,
        snapshot: OverlaySnapshot | None,
        fallback_path: Path,
    ) -> RenderedJpeg:
        source_path = self._trusted_snapshot_path(snapshot)
        source = "processed" if source_path is not None else "waiting"
        if source_path is None:
            source_path = fallback_path.resolve()
        mtime = source_path.stat().st_mtime_ns
        frame_id = snapshot.frame_id if snapshot and source == "processed" else f"waiting-{mtime}"
        fingerprint = f"{frame_id}:{mtime}:{source}"
        cache_key = (slot_id, task_type)

        with self._metadata_lock:
            cached = self._processed_cache.get(cache_key)
            if cached and cached[0] == fingerprint:
                return cached[1]

            render_lock = self._processed_locks.setdefault(cache_key, threading.Lock())

        with render_lock:
            source_path = self._trusted_snapshot_path(snapshot)
            source = "processed" if source_path is not None else "waiting"
            if source_path is None:
                source_path = fallback_path.resolve()
            mtime = source_path.stat().st_mtime_ns
            frame_id = snapshot.frame_id if snapshot and source == "processed" else f"waiting-{mtime}"
            fingerprint = f"{frame_id}:{mtime}:{source}"
            with self._metadata_lock:
                cached = self._processed_cache.get(cache_key)
                if cached and cached[0] == fingerprint:
                    return cached[1]
            image = _scaled_image(source_path)
            annotated = annotate_image(
                image,
                task_type,
                snapshot if source == "processed" else None,
            )
            rendered = RenderedJpeg(
                payload=_encode_canvas(annotated),
                frame_id=str(frame_id),
                source=source,
            )
            with self._metadata_lock:
                self._processed_cache[cache_key] = (fingerprint, rendered)
            return rendered

    def _trusted_snapshot_path(self, snapshot: OverlaySnapshot | None) -> Path | None:
        if snapshot is None or not snapshot.frame_path:
            return None
        candidate = Path(snapshot.frame_path).resolve()
        if not candidate.is_relative_to(self.inference_dir) or not candidate.is_file():
            return None
        return candidate


def _scaled_image(path: Path) -> Image.Image:
    with Image.open(path) as source:
        image = source.convert("RGB")
    image.thumbnail(
        (config.DISPLAY_WIDTH, config.DISPLAY_HEIGHT),
        Image.Resampling.BILINEAR,
    )
    return image


def encode_display_pixels(pixels) -> bytes:
    """Encode owned full-resolution pixels into the bandwidth-bounded preview."""
    image = Image.fromarray(pixels, mode="RGB")
    image.thumbnail(
        (config.DISPLAY_WIDTH, config.DISPLAY_HEIGHT),
        Image.Resampling.BILINEAR,
    )
    return _encode_canvas(image)


def _encode_canvas(image: Image.Image) -> bytes:
    canvas = Image.new("RGB", (config.DISPLAY_WIDTH, config.DISPLAY_HEIGHT), "black")
    offset = (
        (config.DISPLAY_WIDTH - image.width) // 2,
        (config.DISPLAY_HEIGHT - image.height) // 2,
    )
    canvas.paste(image, offset)
    buffer = BytesIO()
    canvas.save(
        buffer,
        format="JPEG",
        quality=config.JPEG_DISPLAY_QUALITY,
        optimize=False,
        subsampling=2,
    )
    return buffer.getvalue()
