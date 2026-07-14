#!/usr/bin/env python3
"""Update only VisionDrive performance keys while preserving secrets and comments."""
from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path


UPDATES = {
    "GESTURE_ALGORITHM_THREADS": "4",
    "JPEG_DISPLAY_QUALITY": "60",
    "JPEG_TARGET_FPS": "25",
    "JPEG_ENCODER_WORKERS": "12",
    "WEBRTC_OUTPUT_FPS": "25",
    "WEBRTC_FRAME_PUBLISH_FPS": "25",
    "WEBRTC_INFERENCE_SNAPSHOT_FPS": "10",
    "PPVEHICLE_CPU_THREADS": "4",
}


def update_file(path: Path) -> list[str]:
    original = path.read_text(encoding="utf-8")
    found: set[str] = set()
    lines: list[str] = []
    for line in original.splitlines(keepends=True):
        key = line.split("=", 1)[0].strip() if "=" in line and not line.lstrip().startswith("#") else ""
        if key in UPDATES:
            ending = "\n" if line.endswith("\n") else ""
            lines.append(f"{key}={UPDATES[key]}{ending}")
            found.add(key)
        else:
            lines.append(line)

    missing = [key for key in UPDATES if key not in found]
    if missing:
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        lines.append("\n# JPEG 并发与算法 CPU/GPU 性能配置\n")
        lines.extend(f"{key}={UPDATES[key]}\n" for key in missing)

    mode = path.stat().st_mode
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.writelines(lines)
        temporary = Path(handle.name)
    os.chmod(temporary, mode)
    os.replace(temporary, path)
    return missing


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    missing = update_file(args.path)
    print(f"updated={len(UPDATES)} appended={len(missing)} path={args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
