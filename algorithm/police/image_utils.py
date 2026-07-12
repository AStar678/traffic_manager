"""交警手势服务专用图像处理工具。"""
from __future__ import annotations

import base64
import io
import urllib.request
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError


def download_image(url: str) -> Image.Image:
    if not url:
        raise ValueError("image_url 不能为空")
    if url.startswith("data:image/"):
        _, encoded = url.split(",", 1)
        return _open_image(base64.b64decode(encoded))
    if url.startswith("file://"):
        return Image.open(Path(url[7:])).convert("RGB")
    if url.startswith(("http://", "https://")):
        if _looks_like_video(url):
            return _open_video_frame(url)
        request = urllib.request.Request(url, headers={"User-Agent": "VisionDrive-Police/2.0"})
        with urllib.request.urlopen(request, timeout=20) as response:
            return _open_image(response.read())
    path = Path(url).expanduser()
    if _looks_like_video(str(path)):
        return _open_video_frame(str(path))
    return Image.open(path).convert("RGB")


def draw_keypoints(
    image: Image.Image,
    detections: list[dict],
    bone_pairs: Iterable[tuple[str, str]] | None = None,
) -> str:
    canvas = image.copy().convert("RGB")
    draw = ImageDraw.Draw(canvas)
    font = _font(size=max(14, canvas.width // 70))
    pairs = list(bone_pairs or [])
    for detection in detections:
        keypoints = detection.get("keypoints") or []
        by_name = {item.get("name"): item for item in keypoints}
        for first, second in pairs:
            a = by_name.get(first)
            b = by_name.get(second)
            if a and b:
                draw.line((a["x"], a["y"], b["x"], b["y"]), fill=(0, 230, 118), width=max(2, canvas.width // 500))
        for point in keypoints:
            x = int(point.get("x", 0))
            y = int(point.get("y", 0))
            radius = max(3, canvas.width // 260)
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(0, 180, 216), outline=(8, 12, 20))
        label = detection.get("gestureName") or detection.get("objectType") or ""
        bbox = detection.get("bbox")
        if label and bbox:
            draw.text((int(bbox.get("x1", 0)), max(0, int(bbox.get("y1", 0)) - 24)), label, fill=(238, 242, 247), font=font)
    return image_to_data_url(canvas)


def image_to_data_url(image: Image.Image) -> str:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode('ascii')}"


def _open_image(raw: bytes) -> Image.Image:
    try:
        image = Image.open(io.BytesIO(raw)).convert("RGB")
        image.load()
        return image
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("无法读取图片") from exc


def _open_video_frame(source: str) -> Image.Image:
    try:
        import cv2  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise ValueError("读取视频/RTSP 需要安装 opencv-python") from exc
    cap = cv2.VideoCapture(source)
    try:
        ok, frame = cap.read()
        if not ok or frame is None:
            raise ValueError("无法读取视频首帧")
        return Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    finally:
        cap.release()


def _looks_like_video(value: str) -> bool:
    lowered = value.lower()
    return lowered.startswith("rtsp://") or lowered.endswith((".mp4", ".avi", ".mov", ".mkv", ".flv"))


def _font(size: int):
    for path in (
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
    ):
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size=size)
            except OSError:
                continue
    return ImageFont.load_default()
