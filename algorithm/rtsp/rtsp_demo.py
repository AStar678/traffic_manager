"""RTSP流 + 模型推理 Demo
基于《沙盘摄像头视频流获取.pdf》参考代码
演示：拉取沙盘摄像头 → 模型推理 → 显示标注结果
"""
import cv2
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from rtsp.camera_config import CAMERAS, get_cameras_for_task
from rtsp.rtsp_reader import RTSPStreamReader


def demo_basic(camera_id: str = "live1"):
    """基础演示：显示原始画面，按s截图，按q退出"""
    cam = CAMERAS.get(camera_id)
    if not cam:
        print(f"未知摄像头: {camera_id}")
        return

    reader = RTSPStreamReader(cam["rtsp_url"])
    reader.start()
    print(f"场景: {cam['name']} | 按 q 退出 | 按 s 截图")

    try:
        while True:
            frame = reader.get_frame()
            if frame is None:
                continue
            cv2.imshow(f"沙盘 - {cam['name']}", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                reader.save_snapshot(f"snapshot_{camera_id}.jpg")
    finally:
        reader.stop()


def demo_with_model(camera_id: str = "live1", model_path: str = None):
    """模型推理演示：显示识别后的标注画面"""
    cam = CAMERAS.get(camera_id)
    if not cam:
        print(f"未知摄像头: {camera_id}")
        return

    # TODO: 加载模型（替换为训练好的模型）
    # model = YOLO(model_path or "yolov8n.pt")

    reader = RTSPStreamReader(cam["rtsp_url"])
    reader.start()
    print(f"场景: {cam['name']} | 模型推理中... | 按 q 退出")

    try:
        while True:
            frame = reader.get_frame()
            if frame is None:
                continue
            # TODO: 模型推理
            # results = model(frame, verbose=False)
            # annotated = results[0].plot()
            # cv2.imshow(f"检测结果 - {cam['name']}", annotated)
            cv2.imshow(f"检测结果 - {cam['name']}", frame)  # 暂时显示原图
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        reader.stop()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="沙盘RTSP视频流测试")
    parser.add_argument("--camera", "-c", default="live1", help="摄像头ID (live1~live12)")
    parser.add_argument("--model", "-m", default=None, help="模型路径")
    parser.add_argument("--task", "-t", default=None, help="按任务筛选摄像头（license_plate/police_gesture）")
    args = parser.parse_args()

    if args.task:
        cameras = get_cameras_for_task(args.task)
        print(f"适用于 {args.task} 的摄像头: {[c['name'] for c in cameras]}")

    demo_basic(args.camera)
