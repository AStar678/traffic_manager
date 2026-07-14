#!/usr/bin/env python3
"""Measure the actual publication rate of a selected camera frame output."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frame-dir", type=Path, required=True)
    parser.add_argument("--slots", default="1,2,3")
    parser.add_argument("--pattern", default="camera-{slot}.display.jpg")
    parser.add_argument("--duration", type=float, default=6.0)
    parser.add_argument("--min-fps", type=float, default=20.0)
    args = parser.parse_args()

    slot_ids = [int(item.strip()) for item in args.slots.split(",") if item.strip()]
    mtimes = {slot_id: set() for slot_id in slot_ids}
    deadline = time.monotonic() + args.duration
    while time.monotonic() < deadline:
        for slot_id in slot_ids:
            path = args.frame_dir / args.pattern.format(slot=slot_id)
            try:
                mtimes[slot_id].add(path.stat().st_mtime_ns)
            except FileNotFoundError:
                pass
        time.sleep(0.002)

    results = [
        {
            "slot_id": slot_id,
            "unique_snapshots": len(mtimes[slot_id]),
            "publish_fps": round(len(mtimes[slot_id]) / args.duration, 2),
        }
        for slot_id in slot_ids
    ]
    print(json.dumps({"results": results}, ensure_ascii=False, indent=2))
    return 0 if all(item["publish_fps"] >= args.min_fps for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
