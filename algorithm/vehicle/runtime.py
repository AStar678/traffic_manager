"""PP-Vehicle 的常驻模型适配器。

这里不复制 PaddleDetection 源码，而是直接复用官方 PP-Vehicle 的
PP-YOLOE + OC-SORT + PP-LCNet 流水线。
"""
from __future__ import annotations

import copy
import sys
import threading
import time
from collections import Counter, defaultdict, deque
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterator

import cv2

from . import config

VEHICLE_TYPE_NAMES = {
    "sedan": "轿车",
    "suv": "SUV",
    "van": "面包车",
    "hatchback": "两厢车",
    "mpv": "MPV",
    "pickup": "皮卡",
    "bus": "客车",
    "truck": "货车",
    "estate": "旅行车",
    "unknown": "未知车型",
}


class RuntimeNotReadyError(RuntimeError):
    """模型或 PaddleDetection 未准备完成。"""


class RuntimeBusyError(RuntimeError):
    """当前单实例模型正在处理其他视频。"""


class MultiSourceIoUTracker:
    """用一份 GPU 模型为多路摄像头维护相互隔离的轨迹。"""

    def __init__(self, iou_threshold: float = 0.25, max_missed: int = 12):
        self.iou_threshold = iou_threshold
        self.max_missed = max_missed
        self._sources: dict[str, dict[int, dict[str, Any]]] = defaultdict(dict)
        self._next_ids: dict[str, int] = defaultdict(lambda: 1)

    def update(self, source_id: str, detections: list[dict[str, Any]]) -> list[dict[str, Any]]:
        tracks = self._sources[source_id]
        unmatched_tracks = set(tracks)
        matches: dict[int, int] = {}
        candidates: list[tuple[float, int, int]] = []
        for detection_index, detection in enumerate(detections):
            for track_id, track in tracks.items():
                iou = self._iou(detection["bbox"], track["bbox"])
                if iou >= self.iou_threshold:
                    candidates.append((iou, detection_index, track_id))
        for _, detection_index, track_id in sorted(candidates, reverse=True):
            if detection_index in matches or track_id not in unmatched_tracks:
                continue
            matches[detection_index] = track_id
            unmatched_tracks.remove(track_id)

        for track_id in unmatched_tracks:
            tracks[track_id]["missed"] += 1

        results: list[dict[str, Any]] = []
        for index, detection in enumerate(detections):
            track_id = matches.get(index)
            if track_id is None:
                track_id = self._next_ids[source_id]
                self._next_ids[source_id] += 1
                tracks[track_id] = {
                    "bbox": detection["bbox"],
                    "missed": 0,
                    "types": deque(maxlen=config.ATTRIBUTE_HISTORY),
                    "colors": deque(maxlen=config.ATTRIBUTE_HISTORY),
                }
            track = tracks[track_id]
            track["bbox"] = detection["bbox"]
            track["missed"] = 0
            self._append_vote(track["types"], detection.get("vehicleType"))
            self._append_vote(track["colors"], detection.get("vehicleColor"))
            vehicle_type = self._winner(track["types"])
            vehicle_color = self._winner(track["colors"])
            results.append({
                **detection,
                "trackId": track_id,
                "objectId": f"{source_id.replace(' ', '-')}-vehicle-{track_id:04d}",
                "vehicleType": vehicle_type,
                "vehicleTypeName": VEHICLE_TYPE_NAMES.get(vehicle_type, vehicle_type),
                "vehicleColor": vehicle_color,
            })

        for track_id in [key for key, value in tracks.items() if value["missed"] > self.max_missed]:
            tracks.pop(track_id, None)
        return results

    @staticmethod
    def _append_vote(values: deque[str], value: Any) -> None:
        normalized = str(value or "unknown").lower()
        if normalized != "unknown":
            values.append(normalized)

    @staticmethod
    def _winner(values: deque[str]) -> str:
        return Counter(values).most_common(1)[0][0] if values else "unknown"

    @staticmethod
    def _iou(first: dict[str, Any], second: dict[str, Any]) -> float:
        left = max(float(first["x1"]), float(second["x1"]))
        top = max(float(first["y1"]), float(second["y1"]))
        right = min(float(first["x2"]), float(second["x2"]))
        bottom = min(float(first["y2"]), float(second["y2"]))
        intersection = max(0.0, right - left) * max(0.0, bottom - top)
        first_area = max(0.0, float(first["x2"]) - float(first["x1"])) * max(0.0, float(first["y2"]) - float(first["y1"]))
        second_area = max(0.0, float(second["x2"]) - float(second["x1"])) * max(0.0, float(second["y2"]) - float(second["y1"]))
        union = first_area + second_area - intersection
        return intersection / union if union > 0 else 0.0


class TrackAttributeSmoother:
    """对同一 trackId 的颜色和车型做有界多数投票。"""

    def __init__(self, history_size: int = 12):
        self.history_size = history_size
        self._types: dict[int, deque[str]] = defaultdict(
            lambda: deque(maxlen=self.history_size)
        )
        self._colors: dict[int, deque[str]] = defaultdict(
            lambda: deque(maxlen=self.history_size)
        )
        self._last_seen: dict[int, int] = {}

    def update(self, track_id: int, frame_index: int, vehicle_type: str, color: str) -> tuple[str, str]:
        if vehicle_type and vehicle_type != "unknown":
            self._types[track_id].append(vehicle_type)
        if color and color != "unknown":
            self._colors[track_id].append(color)
        self._last_seen[track_id] = frame_index
        self._expire(frame_index)
        return self._winner(self._types[track_id]), self._winner(self._colors[track_id])

    @staticmethod
    def _winner(values: deque[str]) -> str:
        return Counter(values).most_common(1)[0][0] if values else "unknown"

    def _expire(self, frame_index: int) -> None:
        stale_ids = [
            track_id for track_id, last_seen in self._last_seen.items()
            if frame_index - last_seen > 300
        ]
        for track_id in stale_ids:
            self._last_seen.pop(track_id, None)
            self._types.pop(track_id, None)
            self._colors.pop(track_id, None)


class PPVehicleRuntime:
    """延迟加载、单实例的 PP-Vehicle 推理运行时。"""

    def __init__(self) -> None:
        self._predictor: Any | None = None
        self._pipeline_module: Any | None = None
        self._load_lock = threading.Lock()
        self._inference_lock = threading.Lock()
        self._init_error = ""
        self._camera_tracker = MultiSourceIoUTracker()

    @property
    def status(self) -> dict[str, Any]:
        ready = self._predictor is not None
        return {
            "ready": ready,
            "mode": "ppvehicle" if ready else "not_loaded",
            "device": config.DEVICE,
            "runMode": config.RUN_MODE,
            "thresholds": {
                "vehicleType": config.TYPE_THRESHOLD,
                "vehicleColor": config.COLOR_THRESHOLD,
            },
            "paddleDetectionDir": str(config.PADDLE_DETECTION_DIR),
            "motModelDir": config.MOT_MODEL_DIR,
            "attributeModelDir": config.ATTR_MODEL_DIR,
            "message": "PP-Vehicle 已就绪" if ready else (
                self._init_error or "模型将在首次推理时加载"
            ),
        }

    def ensure_ready(self) -> None:
        if self._predictor is not None:
            return
        with self._load_lock:
            if self._predictor is not None:
                return
            try:
                self._validate_paths()
                pipeline_module = self._import_pipeline()
                self._predictor = self._create_predictor(pipeline_module)
                self._pipeline_module = pipeline_module
                self._init_error = ""
            except Exception as exc:  # noqa: BLE001
                self._init_error = str(exc)
                raise RuntimeNotReadyError(str(exc)) from exc

    def analyze_video(self, source: str) -> Iterator[dict[str, Any]]:
        self.ensure_ready()
        if not self._inference_lock.acquire(blocking=False):
            raise RuntimeBusyError("模型正在处理另一路视频，请稍后重试")

        capture: Any | None = None
        try:
            capture = cv2.VideoCapture(source)
            if not capture.isOpened():
                raise ValueError(f"无法打开视频源: {source}")
            width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = float(capture.get(cv2.CAP_PROP_FPS)) or 25.0
            frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
            duration_ms = round(frame_count / fps * 1000) if frame_count > 0 else None
            yield {
                "event": "meta",
                "taskType": "vehicle_type",
                "video": {
                    "width": width,
                    "height": height,
                    "fps": round(fps, 3),
                    "frameCount": frame_count if frame_count > 0 else None,
                    "durationMs": duration_ms,
                },
                "model": "PP-Vehicle (PP-YOLOE + OC-SORT + PP-LCNet)",
            }

            smoother = TrackAttributeSmoother(config.ATTRIBUTE_HISTORY)
            unique_ids: set[int] = set()
            track_types: dict[int, str] = {}
            frame_index = 0
            emitted_frames = 0
            started = time.perf_counter()
            self._reset_tracker_if_supported()

            while True:
                ok, frame_bgr = capture.read()
                if not ok:
                    break
                frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
                detections = self._predict_frame(frame_rgb, frame_index, smoother)
                for detection in detections:
                    track_id = detection["trackId"]
                    unique_ids.add(track_id)
                    track_types[track_id] = detection["vehicleType"]

                if frame_index % config.STREAM_EVERY_N_FRAMES == 0:
                    emitted_frames += 1
                    elapsed = max(time.perf_counter() - started, 1e-6)
                    yield {
                        "event": "frame",
                        "frameIndex": frame_index,
                        "timestampMs": round(frame_index / fps * 1000),
                        "progress": round((frame_index + 1) / frame_count, 4) if frame_count > 0 else None,
                        "processingFps": round((frame_index + 1) / elapsed, 2),
                        "detectionCount": len(detections),
                        "detections": detections,
                    }
                frame_index += 1

            elapsed_ms = round((time.perf_counter() - started) * 1000)
            type_counts = Counter(track_types.values())
            yield {
                "event": "complete",
                "summary": {
                    "processedFrames": frame_index,
                    "emittedFrames": emitted_frames,
                    "uniqueVehicleCount": len(unique_ids),
                    "vehicleTypeCounts": dict(type_counts),
                    "latencyMs": elapsed_ms,
                    "averageFps": round(frame_index / max(elapsed_ms / 1000, 1e-6), 2),
                },
            }
        finally:
            if capture is not None:
                capture.release()
            self._inference_lock.release()

    def analyze_image(self, source: str, source_id: str) -> dict[str, Any]:
        """识别单个摄像头帧，并保持该摄像头自己的 trackId。"""
        self.ensure_ready()
        image_bgr = cv2.imread(source)
        if image_bgr is None:
            raise ValueError(f"无法读取图片: {source}")
        height, width = image_bgr.shape[:2]
        with self._inference_lock:
            self._reset_tracker_if_supported()
            image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
            detections = self._predict_frame(
                image_rgb,
                0,
                TrackAttributeSmoother(config.ATTRIBUTE_HISTORY),
            )
            tracked = self._camera_tracker.update(source_id, detections)
        return {
            "taskType": "vehicle_type",
            "image": {"width": width, "height": height},
            "detections": tracked,
            "detectionCount": len(tracked),
            "modelStatus": self.status,
        }

    def _predict_frame(
        self,
        frame_rgb: Any,
        frame_index: int,
        smoother: TrackAttributeSmoother,
    ) -> list[dict[str, Any]]:
        reuse = (
            config.MOT_SKIP_FRAME_NUM > 1
            and frame_index > 0
            and frame_index % config.MOT_SKIP_FRAME_NUM > 0
        )
        raw_mot = self._predictor.mot_predictor.predict_image(
            [copy.deepcopy(frame_rgb)],
            visual=False,
            reuse_det_result=reuse,
            frame_count=frame_index,
        )
        mot_result = self._pipeline_module.parse_mot_res(raw_mot)
        height, width = frame_rgb.shape[:2]
        boxes = self._filter_mot_boxes(
            mot_result.get("boxes", []),
            width,
            height,
            config.MAX_BOX_AREA_RATIO,
        )
        if len(boxes) == 0:
            return []
        mot_result["boxes"] = boxes

        crops, _, _ = self._pipeline_module.crop_image_with_mot(frame_rgb, mot_result)
        attr_output = self._predictor.vehicle_attr_predictor.predict_image(
            crops, visual=False
        ).get("output", []) if len(crops) > 0 else []

        labels = getattr(self._predictor.mot_predictor.pred_config, "labels", [])
        detections: list[dict[str, Any]] = []
        for index, row in enumerate(boxes):
            values = row.tolist() if hasattr(row, "tolist") else list(row)
            if len(values) < 7:
                continue
            track_id, class_id = int(values[0]), int(values[1])
            score = float(values[2])
            x1, y1, x2, y2 = (max(0, round(float(value))) for value in values[3:7])
            raw_type, raw_color = self._parse_attributes(
                attr_output[index] if index < len(attr_output) else []
            )
            vehicle_type, color = smoother.update(
                track_id, frame_index, raw_type, raw_color
            )
            class_name = labels[class_id] if 0 <= class_id < len(labels) else "vehicle"
            detections.append({
                "objectId": f"vehicle_{track_id:04d}",
                "trackId": track_id,
                "objectType": "vehicle",
                "detectionClass": class_name,
                "vehicleType": vehicle_type,
                "vehicleTypeName": VEHICLE_TYPE_NAMES.get(vehicle_type, vehicle_type),
                "vehicleColor": color,
                "confidence": round(score, 4),
                "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
            })
        return detections

    @staticmethod
    def _parse_attributes(attributes: Any) -> tuple[str, str]:
        vehicle_type = "unknown"
        color = "unknown"
        for item in attributes or []:
            key, _, value = str(item).partition(":")
            normalized = value.strip().lower() or "unknown"
            if key.strip().lower() == "type":
                vehicle_type = normalized
            elif key.strip().lower() == "color":
                color = normalized
        return vehicle_type, color

    def _reset_tracker_if_supported(self) -> None:
        mot_predictor = getattr(self._predictor, "mot_predictor", None)
        tracker = getattr(mot_predictor, "tracker", None)
        reset = getattr(tracker, "reset", None)
        if callable(reset):
            reset()
        elif tracker is not None:
            # PaddleDetection 2.9 的 OCSORTTracker 没有 reset()。图片接口若不
            # 显式清空这里的状态，三个摄像头会被当作同一段连续视频处理，
            # 不同画面之间的轨迹会互相污染并最终持续返回空结果。
            for name in (
                "trackers",
                "tracked_stracks",
                "lost_stracks",
                "removed_stracks",
            ):
                collection = getattr(tracker, name, None)
                clear = getattr(collection, "clear", None)
                if callable(clear):
                    clear()
            if hasattr(tracker, "frame_count"):
                tracker.frame_count = 0
        if mot_predictor is not None and hasattr(mot_predictor, "previous_det_result"):
            mot_predictor.previous_det_result = None

    @staticmethod
    def _filter_mot_boxes(
        boxes: Any,
        image_width: int,
        image_height: int,
        max_area_ratio: float,
    ) -> list[Any]:
        """过滤无效框和几乎覆盖整幅图像的沙盘误检框。"""
        image_area = max(1.0, float(image_width * image_height))
        filtered: list[Any] = []
        for row in boxes:
            values = row.tolist() if hasattr(row, "tolist") else list(row)
            if len(values) < 7:
                continue
            x1 = max(0.0, min(float(image_width), float(values[3])))
            y1 = max(0.0, min(float(image_height), float(values[4])))
            x2 = max(0.0, min(float(image_width), float(values[5])))
            y2 = max(0.0, min(float(image_height), float(values[6])))
            area = max(0.0, x2 - x1) * max(0.0, y2 - y1)
            if area <= 0 or area / image_area > max_area_ratio:
                continue
            filtered.append(row)
        return filtered

    def _create_predictor(self, pipeline_module: Any) -> Any:
        """加载官方历史格式权重。

        PaddleDetection 2.9 在 Paddle 3.x 下默认只寻找 PIR `model.json`，
        但 PP-Vehicle 官方下载包仍是 `model.pdmodel + model.pdiparams`。
        Paddle 3.x 的 Config 仍能读取该格式，因此仅在创建 predictor 期间
        走 PaddleDetection 的兼容分支，完成后立即恢复真实版本号。
        """
        paddle_module = pipeline_module.paddle
        actual_version = str(getattr(paddle_module, "__version__", ""))
        legacy_weights = all(
            not self._is_url(model_dir)
            and (Path(model_dir).expanduser() / "model.pdmodel").is_file()
            and not (Path(model_dir).expanduser() / "model.json").is_file()
            for model_dir in (config.MOT_MODEL_DIR, config.ATTR_MODEL_DIR)
        )
        use_legacy_branch = actual_version.startswith("3.") and legacy_weights
        try:
            if use_legacy_branch:
                paddle_module.__version__ = "2.6.2"
            return pipeline_module.PipePredictor(
                self._build_args(), self._build_pipeline_config(), is_video=True
            )
        finally:
            if use_legacy_branch:
                paddle_module.__version__ = actual_version

    def _validate_paths(self) -> None:
        pipeline_file = config.PADDLE_DETECTION_DIR / "deploy/pipeline/pipeline.py"
        if not pipeline_file.is_file():
            raise RuntimeNotReadyError(
                f"未找到 PaddleDetection PP-Vehicle: {pipeline_file}"
            )
        for label, value in (
            ("MOT 跟踪模型", config.MOT_MODEL_DIR),
            ("车辆属性模型", config.ATTR_MODEL_DIR),
        ):
            if not self._is_url(value) and not Path(value).expanduser().is_dir():
                raise RuntimeNotReadyError(f"未找到{label}: {value}")
        if not config.TRACKER_CONFIG.is_file():
            raise RuntimeNotReadyError(f"未找到跟踪器配置: {config.TRACKER_CONFIG}")

    @staticmethod
    def _is_url(value: str) -> bool:
        return value.startswith(("http://", "https://"))

    def _import_pipeline(self) -> Any:
        root = str(config.PADDLE_DETECTION_DIR)
        deploy = str(config.PADDLE_DETECTION_DIR / "deploy")
        pipeline_dir = str(config.PADDLE_DETECTION_DIR / "deploy/pipeline")
        # 官方 pipeline.py 同时使用 `pipeline.*` 包导入和
        # `datacollector` 这类同目录导入，三层路径都需要可见。
        desired_order = (deploy, pipeline_dir, root)
        for path in desired_order:
            if path in sys.path:
                sys.path.remove(path)
        for path in reversed(desired_order):
            sys.path.insert(0, path)
        from pipeline import pipeline as pipeline_module  # type: ignore

        return pipeline_module

    @staticmethod
    def _build_args() -> SimpleNamespace:
        return SimpleNamespace(
            device=config.DEVICE,
            run_mode=config.RUN_MODE,
            trt_min_shape=1,
            trt_max_shape=1280,
            trt_opt_shape=640,
            trt_calib_mode=False,
            cpu_threads=config.CPU_THREADS,
            enable_mkldnn=config.ENABLE_MKLDNN,
            output_dir=str(config.WORK_DIR / "output"),
            pushurl="",
            draw_center_traj=False,
            secs_interval=10,
            do_entrance_counting=False,
            do_break_in_counting=False,
            region_type="horizontal",
            region_polygon=[],
            illegal_parking_time=-1,
        )

    @staticmethod
    def _build_pipeline_config() -> dict[str, Any]:
        return {
            "crop_thresh": 0.5,
            "visual": False,
            "warmup_frame": 0,
            "MOT": {
                "model_dir": config.MOT_MODEL_DIR,
                "tracker_config": str(config.TRACKER_CONFIG),
                "batch_size": 1,
                "skip_frame_num": config.MOT_SKIP_FRAME_NUM,
                "enable": True,
            },
            "VEHICLE_ATTR": {
                "model_dir": config.ATTR_MODEL_DIR,
                "batch_size": 8,
                "color_threshold": config.COLOR_THRESHOLD,
                "type_threshold": config.TYPE_THRESHOLD,
                "enable": True,
            },
        }
