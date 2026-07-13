"""Hand geometry features derived from MediaPipe's 21 hand landmarks."""
from __future__ import annotations

import numpy as np


HAND_EDGES: tuple[tuple[int, int], ...] = (
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (0, 9), (9, 10), (10, 11), (11, 12),
    (0, 13), (13, 14), (14, 15), (15, 16),
    (0, 17), (17, 18), (18, 19), (19, 20),
)
FINGER_CHAINS: tuple[tuple[int, ...], ...] = (
    (0, 1, 2, 3, 4),
    (0, 5, 6, 7, 8),
    (0, 9, 10, 11, 12),
    (0, 13, 14, 15, 16),
    (0, 17, 18, 19, 20),
)
FINGERTIPS: tuple[int, ...] = (4, 8, 12, 16, 20)

# 63 landmarks + 60 bone vectors + 15 finger directions + 15 joint
# angles + 10 fingertip distances + 6 palm normals + 6 global values.
GEOMETRY_FEATURE_DIM = 175


def _safe_unit(vector: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    return vector / max(float(np.linalg.norm(vector)), eps)


def _palm_normal(points: np.ndarray) -> np.ndarray:
    return _safe_unit(np.cross(points[5] - points[0], points[17] - points[0]))


def _joint_cosine(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    return float(np.clip(np.dot(_safe_unit(a - b), _safe_unit(c - b)), -1.0, 1.0))


def extract_geometry_features(
    landmarks: np.ndarray,
    world_landmarks: np.ndarray | None = None,
    *,
    detection_score: float = 1.0,
    handedness: float = 0.0,
) -> np.ndarray:
    points = np.asarray(landmarks, dtype=np.float32)
    if points.shape != (21, 3):
        raise ValueError(f"expected landmarks with shape (21, 3), got {points.shape}")

    wrist = points[0]
    scale = max(float(np.linalg.norm(points[9] - wrist)), 1e-6)
    normalized = (points - wrist) / scale
    bone_vectors = np.concatenate([(points[end] - points[start]) / scale for start, end in HAND_EDGES])
    finger_vectors = np.concatenate([_safe_unit(points[tip] - wrist) for tip in FINGERTIPS])
    joint_angles = np.asarray(
        [
            _joint_cosine(points[chain[index - 1]], points[chain[index]], points[chain[index + 1]])
            for chain in FINGER_CHAINS
            for index in range(1, len(chain) - 1)
        ],
        dtype=np.float32,
    )
    tip_distances = np.asarray(
        [
            np.linalg.norm(points[first] - points[second]) / scale
            for offset, first in enumerate(FINGERTIPS)
            for second in FINGERTIPS[offset + 1 :]
        ],
        dtype=np.float32,
    )
    image_normal = _palm_normal(points)
    world_points = np.asarray(world_landmarks, dtype=np.float32) if world_landmarks is not None else points
    world_normal = _palm_normal(world_points) if world_points.shape == (21, 3) else image_normal
    center = points.mean(axis=0)
    global_features = np.asarray(
        [
            center[0], center[1], center[2], scale,
            float(np.clip(detection_score, 0.0, 1.0)),
            float(np.clip(handedness, -1.0, 1.0)),
        ],
        dtype=np.float32,
    )
    features = np.concatenate(
        [
            normalized.reshape(-1), bone_vectors, finger_vectors, joint_angles,
            tip_distances, image_normal, world_normal, global_features,
        ]
    ).astype(np.float32, copy=False)
    if features.shape != (GEOMETRY_FEATURE_DIM,):
        raise RuntimeError(f"geometry feature contract changed: {features.shape}")
    return features
