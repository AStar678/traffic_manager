"""车牌识别完整流水线。

融合外部 `车牌识别` 目录中的 CLPRNet 常驻识别服务，当前模块只负责
VisionDrive 统一 API 的输入下载和结果格式转换。
"""
from __future__ import annotations

import sys
import os
from pathlib import Path
from threading import RLock
from typing import Any

from .image_utils import download_image, draw_detections


class LicensePlatePipeline:
    def __init__(self, config: dict):
        self.source_dir = Path(config["source_dir"])
        self.model_source_dir = Path(config["clprnet_source_dir"])
        self.model_path = Path(config["clprnet_model_path"])
        self.service = None
        self.init_error = ""
        self._lock = RLock()
        self._init_external_service()

    def process(self, image_url: str, include_visuals: bool = True) -> dict[str, Any]:
        """完整流水线：检测→OCR→颜色分类→结果组装"""
        image = download_image(image_url)
        detections: list[dict[str, Any]] = []

        if self.service is None or not getattr(self.service, "ready", False):
            return {
                "image": {"width": image.width, "height": image.height},
                "detections": detections,
                "detectionCount": 0,
                "annotatedImageUrl": draw_detections(image, detections) if include_visuals else None,
                "modelStatus": self.status,
            }

        # 外部 CLPRNet 服务未声明线程安全；单进程内保护模型状态，服务通过
        # 多个 Uvicorn worker 实现模型级并行。
        with self._lock:
            candidates = self.service.recognize(image, source_name=image_url)
        for index, item in enumerate(candidates, 1):
            x, y, width, height = item.bbox
            confidence = float(item.score)
            detections.append({
                "objectId": f"plate_{index:03d}",
                "objectType": "license_plate",
                "bbox": {
                    "x1": int(x),
                    "y1": int(y),
                    "x2": int(x + width),
                    "y2": int(y + height),
                },
                "position": {
                    "centerX": int(x + width / 2),
                    "centerY": int(y + height / 2),
                    "width": int(width),
                    "height": int(height),
                },
                "plateNumber": item.text,
                "plateColor": self._normalize_color(item.color),
                "plateType": item.color,
                "confidence": round(confidence, 4),
                "detectionConfidence": round(confidence, 4),
                "ocrConfidence": round(confidence, 4),
                "colorRatios": item.color_ratios,
            })

        return {
            "image": {"width": image.width, "height": image.height},
            "detections": detections,
            "detectionCount": len(detections),
            "annotatedImageUrl": draw_detections(image, detections) if include_visuals else None,
            "modelStatus": self.status,
        }

    @property
    def status(self) -> dict[str, Any]:
        if self.service is None:
            return {
                "ready": False,
                "mode": "unavailable",
                "message": self.init_error or "车牌识别服务未初始化",
            }
        status = dict(self.service.status)
        device = getattr(getattr(self.service.recognizer, "clprnet", None), "device", None)
        status["device"] = str(device or "unknown")
        status["cuda"] = str(device).startswith("cuda")
        return status

    def _init_external_service(self) -> None:
        if not self.source_dir.exists():
            self.init_error = f"未找到车牌识别目录: {self.source_dir}"
            return
        os.environ.setdefault("CLPRNET_SOURCE", str(self.model_source_dir))
        os.environ.setdefault("CLPRNET_MODEL", str(self.model_path))
        if str(self.source_dir) not in sys.path:
            sys.path.insert(0, str(self.source_dir))
        try:
            from recognition_service import PlateRecognitionService  # type: ignore

            self.service = PlateRecognitionService()
            if not self.service.ready:
                self.init_error = str(self.service.status.get("model", {}).get("message", "CLPRNet 不可用"))
        except Exception as exc:  # noqa: BLE001
            self.service = None
            self.init_error = f"加载 CLPRNet 车牌识别服务失败: {exc}"

    @staticmethod
    def _normalize_color(label: str) -> str:
        if "蓝" in label:
            return "blue"
        if "绿" in label:
            return "green"
        if "黄" in label:
            return "yellow"
        if "白" in label:
            return "white"
        if "黑" in label:
            return "black"
        return "unknown"
