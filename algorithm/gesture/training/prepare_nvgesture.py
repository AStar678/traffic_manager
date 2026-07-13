"""Precompute MediaPipe geometry and hand-centred RGB clips for NVGesture."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tqdm import tqdm

from .nvgesture import find_official_list, parse_official_list, prepare_sample


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--gesture-model", type=Path, required=True)
    parser.add_argument("--samples-per-video", type=int, default=24)
    parser.add_argument("--crop-size", type=int, default=256)
    parser.add_argument("--crop-expansion", type=float, default=1.70)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> None:
    import mediapipe as mp

    args = parse_args()
    base_options = mp.tasks.BaseOptions(model_asset_path=str(args.gesture_model))
    options = mp.tasks.vision.GestureRecognizerOptions(
        base_options=base_options,
        running_mode=mp.tasks.vision.RunningMode.IMAGE,
        num_hands=1,
        min_hand_detection_confidence=0.35,
        min_hand_presence_confidence=0.35,
        min_tracking_confidence=0.35,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary = {}
    with mp.tasks.vision.GestureRecognizer.create_from_options(options) as recognizer:
        for split in ("train", "test"):
            official_list = find_official_list(args.dataset_root, split)
            samples = parse_official_list(official_list, args.dataset_root)
            if args.limit:
                samples = samples[: args.limit]
            records = []
            failures = []
            for sample in tqdm(samples, desc=f"prepare {split}"):
                output_path = args.output_dir / split / f"{sample.sample_id}.npz"
                if output_path.exists() and not args.overwrite:
                    with __import__("numpy").load(output_path) as payload:
                        records.append({
                            "sample_id": sample.sample_id,
                            "path": str(output_path.resolve()),
                            "label": sample.label,
                            "detected_ratio": float(payload["detected"].mean()),
                            "source_video": str(sample.video_path),
                        })
                    continue
                try:
                    records.append(
                        prepare_sample(
                            sample,
                            recognizer,
                            output_path,
                            samples_per_video=args.samples_per_video,
                            crop_size=args.crop_size,
                            crop_expansion=args.crop_expansion,
                        )
                    )
                except Exception as exc:  # keep long preprocessing resumable
                    failures.append({"sample_id": sample.sample_id, "error": repr(exc)})
            manifest_path = args.output_dir / f"{split}_manifest.jsonl"
            manifest_path.write_text(
                "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
                encoding="utf-8",
            )
            summary[split] = {
                "official_list": str(official_list),
                "prepared": len(records),
                "failed": len(failures),
                "mean_detected_ratio": sum(record["detected_ratio"] for record in records) / max(len(records), 1),
                "failures": failures,
            }
    (args.output_dir / "preprocess_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
