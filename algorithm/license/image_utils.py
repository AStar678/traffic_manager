"""车牌服务专用图像处理工具。"""
from __future__ import annotations

import base64
import io
import os
import urllib.request
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError


VISUAL_JPEG_QUALITY = max(55, min(92, int(os.getenv("LICENSE_VISUAL_JPEG_QUALITY", "80"))))


def download_image(url: str) -> Image.Image:
    """读取 HTTP URL、file URL、data URL 或本地路径图片。"""
    if not url:
        raise ValueError("image_url 不能为空")

    if url.startswith("data:image/"):
        _, encoded = url.split(",", 1)
        raw = base64.b64decode(encoded)
        return _open_image(raw)

    if url.startswith("file://"):
        return Image.open(Path(url[7:])).convert("RGB")

    if url.startswith(("http://", "https://")):
        if _looks_like_video(url):
            return _open_video_frame(url)
        request = urllib.request.Request(url, headers={"User-Agent": "VisionDrive-Algorithm/1.0"})
        with urllib.request.urlopen(request, timeout=20) as response:
            return _open_image(response.read())

    path = Path(url).expanduser()
    if _looks_like_video(str(path)):
        return _open_video_frame(str(path))
    return Image.open(path).convert("RGB")


def draw_detections(image: Image.Image, detections: list[dict]) -> str:
    """绘制检测框/标签，并返回适合连续刷新的 JPEG data URL。"""
    canvas = image.copy().convert("RGB")
    draw = ImageDraw.Draw(canvas)
    font = _font(size=max(14, canvas.width // 70))

    for detection in detections:
        bbox = detection.get("bbox") or {}
        if not bbox:
            continue
        x1 = int(bbox.get("x1", 0))
        y1 = int(bbox.get("y1", 0))
        x2 = int(bbox.get("x2", x1))
        y2 = int(bbox.get("y2", y1))
        label = _detection_label(detection)
        color = _color_for(detection)

        draw.rectangle((x1, y1, x2, y2), outline=color, width=max(2, canvas.width // 400))
        if label:
            left, top, right, bottom = draw.textbbox((0, 0), label, font=font)
            label_width = right - left + 14
            label_height = bottom - top + 10
            label_y = max(0, y1 - label_height)
            draw.rounded_rectangle(
                (x1, label_y, x1 + label_width, label_y + label_height),
                radius=6,
                fill=color,
            )
            draw.text((x1 + 7, label_y + 4), label, fill=_text_color_for(color), font=font)

    return image_to_data_url(canvas, image_format="JPEG", jpeg_quality=VISUAL_JPEG_QUALITY)


def draw_keypoints(
    image: Image.Image,
    detections: list[dict],
    bone_pairs: Iterable[tuple[str, str]] | None = None,
) -> str:
    """绘制关键点和骨架，并返回 PNG data URL。"""
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
            if not a or not b:
                continue
            draw.line((a["x"], a["y"], b["x"], b["y"]), fill=(0, 230, 118), width=max(2, canvas.width // 500))
        for point in keypoints:
            x = int(point.get("x", 0))
            y = int(point.get("y", 0))
            radius = max(3, canvas.width // 260)
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(0, 180, 216), outline=(8, 12, 20))

        label = _detection_label(detection)
        bbox = detection.get("bbox")
        if label and bbox:
            x1 = int(bbox.get("x1", 0))
            y1 = int(bbox.get("y1", 0))
            draw.text((x1, max(0, y1 - 24)), label, fill=(238, 242, 247), font=font)

    return image_to_data_url(canvas)


def image_to_data_url(
    image: Image.Image,
    *,
    image_format: str = "PNG",
    jpeg_quality: int = VISUAL_JPEG_QUALITY,
) -> str:
    buffer = io.BytesIO()
    normalized_format = image_format.upper()
    if normalized_format == "JPEG":
        image.convert("RGB").save(
            buffer,
            format="JPEG",
            quality=max(55, min(92, int(jpeg_quality))),
            subsampling=2,
        )
        media_type = "jpeg"
    else:
        image.save(buffer, format="PNG")
        media_type = "png"
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/{media_type};base64,{encoded}"


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
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb)
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


def _detection_label(detection: dict) -> str:
    return (
        detection.get("plateNumber")
        or detection.get("gestureName")
        or detection.get("objectType")
        or ""
    )


def _color_for(detection: dict) -> tuple[int, int, int]:
    object_type = detection.get("objectType")
    if object_type == "license_plate":
        plate_color = _normalize_plate_color(detection)
        return {
            "blue": (26, 115, 232),
            "green": (0, 230, 118),
            "yellow": (255, 212, 59),
            "white": (248, 250, 252),
            "black": (17, 24, 39),
        }.get(plate_color, (0, 230, 118))
    if object_type == "traffic_police":
        return (234, 67, 53)
    return (0, 180, 216)


def _normalize_plate_color(detection: dict) -> str:
    value = str(detection.get("plateColor") or detection.get("plateType") or "").lower()
    if "yellow" in value or "黄" in value:
        return "yellow"
    if "blue" in value or "蓝" in value:
        return "blue"
    if "green" in value or "绿" in value or "新能源" in value:
        return "green"
    if "white" in value or "白" in value:
        return "white"
    if "black" in value or "黑" in value:
        return "black"
    return "unknown"


def _text_color_for(bg_color: tuple[int, int, int]) -> tuple[int, int, int]:
    brightness = bg_color[0] * 0.299 + bg_color[1] * 0.587 + bg_color[2] * 0.114
    return (8, 12, 20) if brightness > 150 else (248, 250, 252)
