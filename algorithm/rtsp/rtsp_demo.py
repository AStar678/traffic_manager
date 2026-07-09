"""沙盘摄像头交互式预览工具

用法:
    python rtsp_demo.py              # 交互选择摄像头
    python rtsp_demo.py --camera live1  # 直接打开 live1
    python rtsp_demo.py --camera live1 --mock  # 预览 + Mock 车牌标注
    python rtsp_demo.py --list       # 列出所有摄像头
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2
from rtsp.camera_config import CAMERAS
from rtsp.rtsp_reader import RTSPStreamReader
from services.streaming.mock_detector import MockLicensePlateDetector


def list_cameras():
    """列出所有摄像头"""
    print("\n沙盘摄像头列表:\n")
    print(f"{'编号':<8} {'名称':<14} {'场景':<18} {'用途'}")
    print("-" * 70)
    for cam_id, cam in CAMERAS.items():
        uses = ", ".join(cam["use_for"])
        print(f"{cam_id:<8} {cam['name']:<14} {cam['scene']:<18} {uses}")
    print()


def preview_camera(camera_id: str, use_mock: bool = False):
    """预览指定摄像头"""
    cam = CAMERAS.get(camera_id)
    if not cam:
        print(f"未知摄像头: {camera_id}")
        return

    mock = MockLicensePlateDetector() if use_mock else None

    print(f"\n正在连接: {cam['name']} ({camera_id})")
    print(f"地址: {cam['rtsp_url']}")
    if use_mock:
        print("Mock 模式: 画面中随机标注模拟车牌")
    print("按 q 退出，按 s 截图保存为 snapshot.jpg\n")

    reader = RTSPStreamReader(cam["rtsp_url"])
    reader.start()

    try:
        while True:
            frame = reader.get_frame()
            if frame is None:
                continue

            if mock:
                frame = mock(frame)

            cv2.imshow(f"{cam['name']} - {camera_id}", frame)
            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):
                break
            elif key == ord("s"):
                filename = f"snapshot_{camera_id}.jpg"
                cv2.imwrite(filename, frame)
                print(f"已保存截图: {filename}")
    finally:
        reader.stop()


def main():
    parser = argparse.ArgumentParser(description="沙盘摄像头预览工具")
    parser.add_argument("--camera", "-c", help="摄像头编号 (如 live1)")
    parser.add_argument("--list", "-l", action="store_true", help="列出所有摄像头")
    parser.add_argument("--mock", "-m", action="store_true", help="显示 Mock 车牌标注")
    args = parser.parse_args()

    if args.list:
        list_cameras()
        return

    if args.camera:
        preview_camera(args.camera, use_mock=args.mock)
    else:
        list_cameras()
        cam_id = input("输入摄像头编号 (如 live1): ").strip()
        if cam_id:
            preview_camera(cam_id, use_mock=args.mock)


if __name__ == "__main__":
    main()
