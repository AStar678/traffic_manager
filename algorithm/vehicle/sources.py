"""视频输入校验与下载。"""
from __future__ import annotations

import ipaddress
import os
import socket
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from urllib.parse import urlparse

import httpx

from . import config


def validate_local_video(path_value: str) -> Path:
    path = Path(path_value).expanduser().resolve()
    if not any(path == root or root in path.parents for root in config.ALLOWED_VIDEO_ROOTS):
        roots = ", ".join(str(root) for root in config.ALLOWED_VIDEO_ROOTS)
        raise ValueError(f"视频路径不在允许目录中: {roots}")
    if not path.is_file():
        raise ValueError(f"视频文件不存在: {path}")
    if path.suffix.lower() not in config.SUPPORTED_VIDEO_EXTENSIONS:
        raise ValueError(f"不支持的视频格式: {path.suffix or '无扩展名'}")
    return path


def validate_local_image(path_value: str) -> Path:
    path = Path(path_value).expanduser().resolve()
    if not any(path == root or root in path.parents for root in config.ALLOWED_MEDIA_ROOTS):
        roots = ", ".join(str(root) for root in config.ALLOWED_MEDIA_ROOTS)
        raise ValueError(f"图片路径不在允许目录中: {roots}")
    if not path.is_file():
        raise ValueError(f"图片文件不存在: {path}")
    if path.suffix.lower() not in config.SUPPORTED_IMAGE_EXTENSIONS:
        raise ValueError(f"不支持的图片格式: {path.suffix or '无扩展名'}")
    return path


def validate_remote_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme in {"rtsp", "rtmp"}:
        if not parsed.hostname:
            raise ValueError("无效的视频流地址")
        return url
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("仅支持 http/https/rtsp/rtmp 视频地址")
    _reject_private_host(parsed.hostname)
    return url


def _reject_private_host(hostname: str) -> None:
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(hostname, None)}
    except socket.gaierror as exc:
        raise ValueError(f"无法解析视频地址: {hostname}") from exc
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise ValueError("远程视频地址不允许指向内网或本机")


@contextmanager
def materialize_video(video_path: str | None, video_url: str | None) -> Iterator[str]:
    if video_path:
        yield str(validate_local_video(video_path))
        return
    if not video_url:
        raise ValueError("video_path 或 video_url 不能为空")
    url = validate_remote_url(video_url)
    if url.startswith(("rtsp://", "rtmp://")):
        yield url
        return

    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix not in config.SUPPORTED_VIDEO_EXTENSIONS:
        suffix = ".mp4"
    config.WORK_DIR.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix="remote-", suffix=suffix, dir=config.WORK_DIR)
    try:
        downloaded = 0
        with os.fdopen(fd, "wb") as target:
            with httpx.stream(
                "GET",
                url,
                follow_redirects=False,
                timeout=config.DOWNLOAD_TIMEOUT_SECONDS,
            ) as response:
                response.raise_for_status()
                for chunk in response.iter_bytes():
                    downloaded += len(chunk)
                    if downloaded > config.MAX_UPLOAD_BYTES:
                        raise ValueError("远程视频超过最大允许大小")
                    target.write(chunk)
        yield temp_name
    finally:
        Path(temp_name).unlink(missing_ok=True)
