"""Evaluate the police LSTM against per-frame CSV labels and generated skeletons."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from .pipeline import PoliceGesturePipeline


def load_labels(path: Path) -> np.ndarray:
    labels: list[int] = []
    with path.open(newline="", encoding="utf-8") as file:
        for row in csv.reader(file):
            labels.extend(int(value) for value in row if value.strip())
    return np.asarray(labels, dtype=np.int16)


def metrics(labels: np.ndarray, predictions: np.ndarray) -> dict[str, float | int]:
    usable = min(len(labels), len(predictions))
    labels = labels[:usable]
    predictions = predictions[:usable]
    gesture_mask = labels > 0
    return {
        "frames": usable,
        "accuracy": round(float(np.mean(labels == predictions)), 6) if usable else 0.0,
        "gestureAccuracy": round(float(np.mean(labels[gesture_mask] == predictions[gesture_mask])), 6)
        if gesture_mask.any() else 0.0,
        "falsePositiveRate": round(float(np.mean((labels == 0) & (predictions != 0))), 6) if usable else 0.0,
    }


def evaluate(source_dir: Path, test_dir: Path) -> dict:
    pipeline = PoliceGesturePipeline({"source_dir": source_dir})
    if not pipeline.status["ready"]:
        raise RuntimeError(pipeline.status["message"])

    samples = []
    all_labels = []
    all_predictions = []
    for label_path in sorted(test_dir.glob("*.csv")):
        coordinate_path = source_dir / "generated" / "coords" / "test" / f"{label_path.stem}.pkl"
        if not coordinate_path.is_file():
            continue
        labels = load_labels(label_path)
        predictions = pipeline._prepare_sample(label_path.stem)["stable_ids"]
        usable = min(len(labels), len(predictions))
        sample_metrics = metrics(labels, predictions)
        sample_metrics["sampleId"] = label_path.stem
        samples.append(sample_metrics)
        all_labels.append(labels[:usable])
        all_predictions.append(predictions[:usable])

    combined_labels = np.concatenate(all_labels) if all_labels else np.asarray([], dtype=np.int16)
    combined_predictions = np.concatenate(all_predictions) if all_predictions else np.asarray([], dtype=np.int16)
    return {
        "modelStatus": pipeline.status,
        "sampleCount": len(samples),
        "summary": metrics(combined_labels, combined_predictions),
        "samples": samples,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--test-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(evaluate(args.source_dir, args.test_dir), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
