"""NVGesture manifests, preprocessing and episodic video loading."""
from __future__ import annotations

import json
import math
import random
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Sequence

import cv2
import numpy as np
import torch
from torch.utils.data import Dataset, Sampler
from torchvision.transforms import functional as TF
from torchvision.transforms.functional import InterpolationMode

from .geometry import GEOMETRY_FEATURE_DIM, extract_geometry_features


@dataclass(frozen=True)
class NVGestureSample:
    sample_id: str
    video_path: Path
    frame_start: int
    frame_end: int
    label: int


def parse_official_list(list_path: Path, dataset_root: Path) -> list[NVGestureSample]:
    """Parse NVIDIA's ``key:value`` train/test list format."""
    samples: list[NVGestureSample] = []
    for raw_line in list_path.read_text(encoding="utf-8").splitlines():
        raw_line = raw_line.strip()
        if not raw_line or raw_line.startswith("#"):
            continue
        fields = dict(token.split(":", 1) for token in raw_line.split())
        relative_dir = fields["path"].removeprefix("./")
        color_name, start, end = fields["color"].split(":")
        video_path = dataset_root / relative_dir / f"{color_name}.avi"
        frame_directory = dataset_root / relative_dir / color_name
        if not video_path.exists() and frame_directory.is_dir():
            video_path = frame_directory
        samples.append(
            NVGestureSample(
                sample_id=relative_dir.replace("/", "__"),
                video_path=video_path,
                frame_start=int(start),
                frame_end=int(end),
                label=int(fields["label"]) - 1,
            )
        )
    return samples


def find_official_list(dataset_root: Path, split: str) -> Path:
    candidates = sorted(dataset_root.rglob(f"nvgesture_{split}*_v2.lst"))
    if not candidates:
        candidates = sorted(dataset_root.rglob(f"*{split}*.lst"))
    if not candidates:
        raise FileNotFoundError(f"cannot find the official {split} list below {dataset_root}")
    return candidates[0]


def uniform_frame_indices(start: int, end: int, count: int) -> np.ndarray:
    if end < start:
        start, end = end, start
    return np.rint(np.linspace(start, end, num=count)).astype(np.int32)


def decode_selected_frames(video_path: Path, indices: np.ndarray) -> list[np.ndarray]:
    if video_path.is_dir():
        image_paths = sorted(
            [
                path
                for path in video_path.iterdir()
                if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}
            ]
        )
        if not image_paths:
            raise OSError(f"frame directory contains no images: {video_path}")
        frames = []
        for index in indices.tolist():
            path = image_paths[min(max(int(index), 0), len(image_paths) - 1)]
            frame = cv2.imread(str(path), cv2.IMREAD_COLOR)
            if frame is None:
                raise OSError(f"cannot decode frame: {path}")
            frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        return frames

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise OSError(f"cannot open video: {video_path}")
    wanted = {int(index): offset for offset, index in enumerate(indices.tolist())}
    frames: list[np.ndarray | None] = [None] * len(indices)
    frame_index = 0
    last_frame: np.ndarray | None = None
    while capture.isOpened() and any(frame is None for frame in frames):
        ok, frame = capture.read()
        if not ok:
            break
        last_frame = frame
        if frame_index in wanted:
            frames[wanted[frame_index]] = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_index += 1
    capture.release()
    if last_frame is None:
        raise OSError(f"video contains no decodable frames: {video_path}")
    fallback = cv2.cvtColor(last_frame, cv2.COLOR_BGR2RGB)
    for index, frame in enumerate(frames):
        if frame is None:
            frames[index] = frames[index - 1] if index and frames[index - 1] is not None else fallback
    return [np.asarray(frame, dtype=np.uint8) for frame in frames]


def _recognizer_result(result) -> tuple[np.ndarray, np.ndarray, float, float] | None:
    if not result.hand_landmarks:
        return None
    best_index = 0
    best_score = -1.0
    for index, categories in enumerate(result.handedness or []):
        score = float(categories[0].score) if categories else 0.0
        if score > best_score:
            best_index, best_score = index, score
    landmarks = np.asarray(
        [[point.x, point.y, point.z] for point in result.hand_landmarks[best_index]],
        dtype=np.float32,
    )
    world = np.asarray(
        [[point.x, point.y, point.z] for point in result.hand_world_landmarks[best_index]],
        dtype=np.float32,
    )
    categories = result.handedness[best_index] if result.handedness else []
    category_name = categories[0].category_name.lower() if categories else ""
    handedness = 1.0 if category_name == "right" else -1.0 if category_name == "left" else 0.0
    return landmarks, world, max(best_score, 0.0), handedness


def _interpolate_missing(values: np.ndarray, valid: np.ndarray) -> np.ndarray:
    if valid.all() or not valid.any():
        return values
    positions = np.arange(len(values), dtype=np.float32)
    valid_positions = positions[valid]
    flat = values.reshape(len(values), -1)
    for column in range(flat.shape[1]):
        flat[:, column] = np.interp(positions, valid_positions, flat[valid, column])
    return flat.reshape(values.shape)


def _square_hand_crop(frame: np.ndarray, landmarks: np.ndarray | None, output_size: int, expansion: float) -> np.ndarray:
    height, width = frame.shape[:2]
    if landmarks is None:
        center_x, center_y = width / 2, height / 2
        side = float(min(width, height))
    else:
        xs = landmarks[:, 0] * width
        ys = landmarks[:, 1] * height
        center_x, center_y = float((xs.min() + xs.max()) / 2), float((ys.min() + ys.max()) / 2)
        side = max(float(xs.max() - xs.min()), float(ys.max() - ys.min()), 24.0) * expansion
    side = max(side, 24.0)
    x0, y0 = int(round(center_x - side / 2)), int(round(center_y - side / 2))
    x1, y1 = int(round(center_x + side / 2)), int(round(center_y + side / 2))
    pad_left, pad_top = max(-x0, 0), max(-y0, 0)
    pad_right, pad_bottom = max(x1 - width, 0), max(y1 - height, 0)
    if any((pad_left, pad_top, pad_right, pad_bottom)):
        frame = cv2.copyMakeBorder(
            frame, pad_top, pad_bottom, pad_left, pad_right, cv2.BORDER_REFLECT_101
        )
        x0, x1 = x0 + pad_left, x1 + pad_left
        y0, y1 = y0 + pad_top, y1 + pad_top
    crop = frame[max(y0, 0):max(y1, 1), max(x0, 0):max(x1, 1)]
    return cv2.resize(crop, (output_size, output_size), interpolation=cv2.INTER_AREA)


def prepare_sample(
    sample: NVGestureSample,
    recognizer,
    output_path: Path,
    *,
    samples_per_video: int,
    crop_size: int,
    crop_expansion: float,
) -> dict:
    import mediapipe as mp

    indices = uniform_frame_indices(sample.frame_start, sample.frame_end, samples_per_video)
    frames = decode_selected_frames(sample.video_path, indices)
    landmarks = np.zeros((samples_per_video, 21, 3), dtype=np.float32)
    world = np.zeros_like(landmarks)
    scores = np.zeros(samples_per_video, dtype=np.float32)
    hands = np.zeros(samples_per_video, dtype=np.float32)
    detected = np.zeros(samples_per_video, dtype=bool)

    for index, frame in enumerate(frames):
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(frame))
        parsed = _recognizer_result(recognizer.recognize(mp_image))
        if parsed is None:
            continue
        landmarks[index], world[index], scores[index], hands[index] = parsed
        detected[index] = True

    if detected.any():
        landmarks = _interpolate_missing(landmarks, detected)
        world = _interpolate_missing(world, detected)
        scores = _interpolate_missing(scores[:, None], detected).reshape(-1)
        hands = _interpolate_missing(hands[:, None], detected).reshape(-1)

    crops = np.stack(
        [
            _square_hand_crop(frame, landmarks[index] if detected.any() else None, crop_size, crop_expansion)
            for index, frame in enumerate(frames)
        ]
    )
    geometry = np.stack(
        [
            extract_geometry_features(
                landmarks[index], world[index], detection_score=scores[index], handedness=hands[index]
            )
            if detected.any()
            else np.zeros(GEOMETRY_FEATURE_DIM, dtype=np.float32)
            for index in range(samples_per_video)
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output_path,
        frames=crops,
        geometry=geometry,
        detected=detected.astype(np.uint8),
        frame_indices=indices,
        label=np.asarray(sample.label, dtype=np.int64),
    )
    return {
        "sample_id": sample.sample_id,
        "path": str(output_path.resolve()),
        "label": sample.label,
        "detected_ratio": float(detected.mean()),
        "source_video": str(sample.video_path),
    }


class ConsistentVideoAugment:
    """Apply spatial/photometric parameters consistently to the whole clip."""

    def __init__(
        self,
        image_size: int,
        *,
        scale_min: float = 0.72,
        scale_max: float = 1.30,
        blur_probability: float = 0.40,
        blur_sigma_min: float = 0.2,
        blur_sigma_max: float = 2.4,
        training: bool = True,
    ) -> None:
        self.image_size = image_size
        self.scale_min = scale_min
        self.scale_max = scale_max
        self.blur_probability = blur_probability
        self.blur_sigma_min = blur_sigma_min
        self.blur_sigma_max = blur_sigma_max
        self.training = training

    def __call__(self, frames: np.ndarray) -> torch.Tensor:
        tensors = [TF.to_tensor(frame) for frame in frames]
        if self.training:
            angle = random.uniform(-7.0, 7.0)
            scale = random.uniform(self.scale_min, self.scale_max)
            max_translate = int(round(self.image_size * 0.04))
            translate = [random.randint(-max_translate, max_translate), random.randint(-max_translate, max_translate)]
            brightness = random.uniform(0.82, 1.18)
            contrast = random.uniform(0.82, 1.18)
            saturation = random.uniform(0.88, 1.12)
            apply_blur = random.random() < self.blur_probability
            sigma = random.uniform(self.blur_sigma_min, self.blur_sigma_max)
            for index, tensor in enumerate(tensors):
                tensor = TF.resize(tensor, [self.image_size, self.image_size], antialias=True)
                tensor = TF.affine(
                    tensor,
                    angle=angle,
                    translate=translate,
                    scale=scale,
                    shear=[0.0, 0.0],
                    interpolation=InterpolationMode.BILINEAR,
                    fill=0.0,
                )
                tensor = TF.adjust_brightness(tensor, brightness)
                tensor = TF.adjust_contrast(tensor, contrast)
                tensor = TF.adjust_saturation(tensor, saturation)
                if apply_blur:
                    tensor = TF.gaussian_blur(tensor, kernel_size=[7, 7], sigma=[sigma, sigma])
                tensors[index] = tensor.clamp_(0.0, 1.0)
        else:
            tensors = [TF.resize(tensor, [self.image_size, self.image_size], antialias=True) for tensor in tensors]

        clip = torch.stack(tensors)
        mean = torch.tensor([0.485, 0.456, 0.406], dtype=clip.dtype).view(1, 3, 1, 1)
        std = torch.tensor([0.229, 0.224, 0.225], dtype=clip.dtype).view(1, 3, 1, 1)
        return (clip - mean) / std


class PreparedNVGestureDataset(Dataset):
    def __init__(
        self,
        manifest_path: Path,
        *,
        frames_per_video: int,
        image_size: int,
        training: bool,
        augmentation: dict | None = None,
    ) -> None:
        self.records = [json.loads(line) for line in manifest_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.frames_per_video = frames_per_video
        self.training = training
        self.augment = ConsistentVideoAugment(image_size, training=training, **(augmentation or {}))
        self.class_to_indices: dict[int, list[int]] = defaultdict(list)
        for index, record in enumerate(self.records):
            self.class_to_indices[int(record["label"])].append(index)

    def __len__(self) -> int:
        return len(self.records)

    def _temporal_indices(self, available: int) -> np.ndarray:
        if available <= self.frames_per_video:
            return np.rint(np.linspace(0, available - 1, self.frames_per_video)).astype(np.int64)
        if not self.training:
            return np.rint(np.linspace(0, available - 1, self.frames_per_video)).astype(np.int64)
        edges = np.linspace(0, available, self.frames_per_video + 1)
        return np.asarray(
            [random.randrange(int(math.floor(edges[i])), max(int(math.ceil(edges[i + 1])), int(math.floor(edges[i])) + 1)) for i in range(self.frames_per_video)],
            dtype=np.int64,
        ).clip(0, available - 1)

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        record = self.records[index]
        with np.load(record["path"]) as payload:
            frame_indices = self._temporal_indices(len(payload["frames"]))
            frames = payload["frames"][frame_indices]
            geometry = payload["geometry"][frame_indices].astype(np.float32)
            detected = payload["detected"][frame_indices].astype(np.float32)
        if self.training:
            geometry = geometry + np.random.normal(0.0, 0.006, size=geometry.shape).astype(np.float32)
        return {
            "frames": self.augment(frames),
            "geometry": torch.from_numpy(geometry),
            "detected": torch.from_numpy(detected),
            "label": torch.tensor(int(record["label"]), dtype=torch.long),
        }


class EpisodeBatchSampler(Sampler[list[int]]):
    def __init__(
        self,
        class_to_indices: dict[int, list[int]],
        *,
        episodes: int,
        n_way: int,
        n_support: int,
        n_query: int,
        seed: int,
    ) -> None:
        self.class_to_indices = {
            label: indices for label, indices in class_to_indices.items() if len(indices) >= n_support + n_query
        }
        self.episodes = episodes
        self.n_way = n_way
        self.n_support = n_support
        self.n_query = n_query
        self.seed = seed
        if len(self.class_to_indices) < n_way:
            raise ValueError(f"need {n_way} eligible classes, found {len(self.class_to_indices)}")

    def __len__(self) -> int:
        return self.episodes

    def __iter__(self) -> Iterator[list[int]]:
        rng = random.Random(self.seed + random.randint(0, 1_000_000))
        labels = list(self.class_to_indices)
        for _ in range(self.episodes):
            selected_labels = rng.sample(labels, self.n_way)
            batch: list[int] = []
            for label in selected_labels:
                batch.extend(rng.sample(self.class_to_indices[label], self.n_support + self.n_query))
            yield batch
