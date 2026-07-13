"""通过 HTTP 上传视频，验证 PP-Vehicle 微服务的 NDJSON 结果流。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import httpx


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("video", type=Path)
    parser.add_argument("--base-url", default="http://127.0.0.1:8003")
    args = parser.parse_args()
    if not args.video.is_file():
        raise SystemExit(f"视频不存在: {args.video}")

    last_frame = None
    # 本机回环测试不应经过系统 HTTP/SOCKS 代理。
    with httpx.Client(trust_env=False, timeout=None) as client, \
            args.video.open("rb") as source, client.stream(
        "POST",
        f"{args.base_url.rstrip('/')}/api/v1/inference/video/upload",
        files={"file": (args.video.name, source, "video/mp4")},
    ) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line:
                continue
            event = json.loads(line)
            if event["event"] == "meta":
                print("视频信息:", json.dumps(event["video"], ensure_ascii=False))
            elif event["event"] == "frame":
                last_frame = event
                if event["frameIndex"] % 30 == 0:
                    print(
                        f"帧 {event['frameIndex']:03d}: "
                        f"{event['detectionCount']} 个目标, "
                        f"{event['processingFps']:.2f} FPS"
                    )
            elif event["event"] == "error":
                raise RuntimeError(event["message"])
            elif event["event"] == "complete":
                print("测试完成:", json.dumps(event["summary"], ensure_ascii=False))
                if not last_frame:
                    raise RuntimeError("未收到任何帧结果")


if __name__ == "__main__":
    main()
