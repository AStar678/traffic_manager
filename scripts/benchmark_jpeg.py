#!/usr/bin/env python3
"""Measure independent JPEG frame delivery for all active camera slots."""
from __future__ import annotations

import argparse
import json
import threading
import time
import urllib.request
from dataclasses import asdict, dataclass


@dataclass
class SlotResult:
    slot_id: int
    requests: int
    unique_frames: int
    request_fps: float
    frame_fps: float
    average_bytes: int
    errors: list[str]


def benchmark_slot(
    base_url: str,
    path_template: str,
    slot_id: int,
    warmup_seconds: float,
    duration_seconds: float,
    timeout_seconds: float,
    start_barrier: threading.Barrier,
) -> SlotResult:
    url = f"{base_url.rstrip('/')}{path_template.format(slot=slot_id)}"
    start_barrier.wait()
    measurement_start = time.monotonic() + warmup_seconds
    measurement_end = measurement_start + duration_seconds
    request_count = 0
    total_bytes = 0
    frame_ids: set[str] = set()
    errors: list[str] = []

    while time.monotonic() < measurement_end:
        try:
            request = urllib.request.Request(url, headers={"Cache-Control": "no-cache"})
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                payload = response.read()
                frame_id = response.headers.get("X-VisionDrive-Frame-Id", "")
            if time.monotonic() >= measurement_start:
                request_count += 1
                total_bytes += len(payload)
                if frame_id:
                    frame_ids.add(frame_id)
        except Exception as exc:  # noqa: BLE001
            if len(errors) < 5:
                errors.append(str(exc))

    return SlotResult(
        slot_id=slot_id,
        requests=request_count,
        unique_frames=len(frame_ids),
        request_fps=round(request_count / duration_seconds, 2),
        frame_fps=round(len(frame_ids) / duration_seconds, 2),
        average_bytes=round(total_bytes / request_count) if request_count else 0,
        errors=errors,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:5173")
    parser.add_argument("--path-template", default="/jpeg/api/v1/jpeg/frame/{slot}.jpg")
    parser.add_argument("--slots", default="1,2,3")
    parser.add_argument("--duration", type=float, default=6.0)
    parser.add_argument("--warmup", type=float, default=1.0)
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument("--min-fps", type=float, default=20.0)
    args = parser.parse_args()

    slot_ids = [int(item.strip()) for item in args.slots.split(",") if item.strip()]
    start_barrier = threading.Barrier(len(slot_ids))
    results: list[SlotResult] = []
    result_lock = threading.Lock()

    def run(slot_id: int) -> None:
        result = benchmark_slot(
            args.base_url,
            args.path_template,
            slot_id,
            args.warmup,
            args.duration,
            args.timeout,
            start_barrier,
        )
        with result_lock:
            results.append(result)

    threads = [threading.Thread(target=run, args=(slot_id,), name=f"jpeg-slot-{slot_id}") for slot_id in slot_ids]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    results.sort(key=lambda item: item.slot_id)
    print(json.dumps({"results": [asdict(item) for item in results]}, ensure_ascii=False, indent=2))
    return 0 if results and all(item.frame_fps >= args.min_fps and not item.errors for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
