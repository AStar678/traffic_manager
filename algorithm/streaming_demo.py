"""沙盘摄像头识别推流 —— 启动入口

用法:
    # 默认: Mock 随机标注（无需模型，测试管线用）
    python streaming_demo.py --camera live1

    # 使用 YOLO 真实检测
    python streaming_demo.py --camera live1 --detector yolo

    # 无头模式（不显示本地预览窗口）
    python streaming_demo.py --camera live1 --no-preview

    # 指定推流地址
    python streaming_demo.py --camera live2 --dst rtsp://127.0.0.1:8554/video31

前置条件:
    1. 沙盘摄像头 RTSP 可访问（内网 10.126.59.120:8554）
    2. mediamtx 流媒体服务器已启动（默认端口 8554）
    3. ffmpeg 已安装并在 PATH 中
"""
import argparse
import os
import sys
from pathlib import Path

# 确保 algorithm 包可导入
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rtsp.camera_config import CAMERAS, get_cameras_for_task
from services.streaming.detection_streamer import DetectionStreamer
from services.streaming.mock_detector import MockLicensePlateDetector


def build_yolo_detector(model_name: str = "yolov8n.pt"):
    """构建基于 YOLOv8 的通用检测器（作为车牌检测器的占位实现）"""
    try:
        from ultralytics import YOLO

        model_path = Path(__file__).resolve().parent / "models" / model_name
        if not model_path.exists():
            model_path = model_name  # 让 YOLO 自动下载

        yolo_model = YOLO(str(model_path))

        def detect(frame):
            results = yolo_model(frame, verbose=False)
            return results[0].plot()

        print(f"已加载 YOLO 模型: {model_name}")
        return detect

    except ImportError:
        # 如果没有 ultralytics，提供一个简单的占位检测器
        print("警告: ultralytics 未安装，使用空检测器（仅推流原帧）")

        def detect(frame):
            return frame

        return detect


def build_license_plate_detector():
    """构建车牌检测器（预留接口，模型训练完成后接入）"""
    # TODO: 接入训练好的车牌检测+OCR+颜色分类 Pipeline
    # from services.license_plate.pipeline import LicensePlatePipeline
    # pipeline = LicensePlatePipeline(config={...})
    # return lambda frame: pipeline.process_frame(frame)
    print("⚠ 车牌检测模型尚未就绪，回退到通用 YOLO 检测器")
    return build_yolo_detector()


def main():
    parser = argparse.ArgumentParser(description="沙盘摄像头识别推流")
    parser.add_argument(
        "--camera", "-c", default="live1",
        choices=list(CAMERAS.keys()),
        help="摄像头编号 (default: live1)"
    )
    parser.add_argument(
        "--task", "-t", default=None,
        choices=["license_plate", "vehicle_detection", "police_gesture", "incident_detection", "vehicle_counting"],
        help="按任务类型筛选摄像头"
    )
    parser.add_argument(
        "--dst", "-d", default=None,
        help="推流目标地址 (default: rtsp://127.0.0.1:8554/video{camera_suffix})"
    )
    parser.add_argument(
        "--model", "-m", default="yolov8n.pt",
        help="YOLO 模型名称或路径 (default: yolov8n.pt)"
    )
    parser.add_argument(
        "--detector", default="mock",
        choices=["mock", "yolo", "license_plate"],
        help="检测器类型: mock=模拟随机标注(默认), yolo=通用YOLO, license_plate=车牌检测器(未就绪)"
    )
    parser.add_argument(
        "--plate-count", type=int, default=2,
        help="Mock 模式下每帧模拟的车牌数量 (default: 2)"
    )
    parser.add_argument("--no-preview", action="store_true", help="不显示本地预览窗口")
    parser.add_argument("--ffmpeg", default="ffmpeg", help="ffmpeg 路径 (default: ffmpeg)")
    parser.add_argument("--fps", type=int, default=25, help="推流帧率 (default: 25)")
    parser.add_argument("--bitrate", default="2M", help="推流码率 (default: 2M)")

    args = parser.parse_args()

    # 选择摄像头
    if args.task:
        cameras = get_cameras_for_task(args.task)
        if not cameras:
            print(f"没有找到适用于任务 '{args.task}' 的摄像头")
            sys.exit(1)
        camera = cameras[0]
        print(f"任务 '{args.task}' 使用摄像头: {camera['name']} ({camera['rtsp_url']})")
    else:
        camera = CAMERAS.get(args.camera)
        if not camera:
            print(f"未知摄像头: {args.camera}")
            sys.exit(1)

    src_url = camera["rtsp_url"]

    # 确定推流地址
    if args.dst:
        dst_url = args.dst
    else:
        # live1 → video31, live2 → video32, ...
        num = int(args.camera.replace("live", ""))
        dst_url = f"rtsp://127.0.0.1:8554/video{30 + num}"

    # 构建检测器
    if args.detector == "mock":
        print(f"使用 Mock 检测器，每帧 {args.plate_count} 个模拟车牌")
        mock = MockLicensePlateDetector(plate_count=args.plate_count)
        detector_fn = mock  # MockLicensePlateDetector 实现了 __call__ 可直接用
    elif args.detector == "license_plate":
        detector_fn = build_license_plate_detector()
    else:
        detector_fn = build_yolo_detector(args.model)

    # 启动管线
    streamer = DetectionStreamer(
        src_url=src_url,
        dst_url=dst_url,
        detector=detector_fn,
        ffmpeg_bin=args.ffmpeg,
        fps=args.fps,
        bitrate=args.bitrate,
        show_preview=not args.no_preview,
    )

    print(f"\n摄像头: {camera['name']} | 场景: {camera['scene']}")
    print(f"拉流: {src_url}")
    print(f"推流: {dst_url}")
    if not args.no_preview:
        print(f"浏览器观看: http://127.0.0.1:8889/video{suffix}")
    print()

    try:
        streamer.run()
    except KeyboardInterrupt:
        print("\n用户中断")
    except RuntimeError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
