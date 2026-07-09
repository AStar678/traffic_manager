"""实时识别+推流管线

拉取沙盘RTSP视频流 → 模型推理标注 → FFmpeg推流到Mediamtx → 浏览器观看

依赖:
    - mediamtx (流媒体服务器): https://github.com/bluenviron/mediamtx
    - ffmpeg (推流工具): https://github.com/BtbN/FFmpeg-Builds/releases
"""
import subprocess
import sys
import time
from typing import Callable, Optional

import cv2
import numpy as np


class DetectionStreamer:
    """拉流→识别标注→推流 管线

    Usage:
        def my_detector(frame: np.ndarray) -> np.ndarray:
            '''识别并返回标注后的帧'''
            results = model(frame, verbose=False)
            return results[0].plot()

        streamer = DetectionStreamer(
            src_url="rtsp://10.126.59.120:8554/live/live1",
            dst_url="rtsp://127.0.0.1:8554/video30",
            detector=my_detector,
            ffmpeg_bin="ffmpeg"
        )
        streamer.run()
    """

    def __init__(
        self,
        src_url: str,
        dst_url: str,
        detector: Callable[[np.ndarray], np.ndarray],
        ffmpeg_bin: str = "ffmpeg",
        fps: int = 25,
        bitrate: str = "2M",
        show_preview: bool = True,
    ):
        """
        Args:
            src_url:    输入RTSP地址（沙盘摄像头）
            dst_url:    输出RTSP地址（推流到mediamtx）
            detector:   检测函数, 输入 frame (BGR), 返回标注后的 frame
            ffmpeg_bin: ffmpeg 可执行文件路径
            fps:        推流帧率
            bitrate:    推流码率
            show_preview: 是否显示本地预览窗口
        """
        self.src_url = src_url
        self.dst_url = dst_url
        self.detector = detector
        self.ffmpeg_bin = ffmpeg_bin
        self.fps = fps
        self.bitrate = bitrate
        self.show_preview = show_preview

        self._cap: Optional[cv2.VideoCapture] = None
        self._proc: Optional[subprocess.Popen] = None
        self._running = False

    def run(self):
        """启动识别推流管线（阻塞，按 q 退出）"""
        # 1. 打开输入流
        self._cap = cv2.VideoCapture(self.src_url, cv2.CAP_FFMPEG)
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if not self._cap.isOpened():
            raise RuntimeError(f"无法打开视频流: {self.src_url}")

        width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1280
        height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 720

        print(f"已连接视频流: {self.src_url}")
        print(f"分辨率: {width}x{height}, 推流到: {self.dst_url}")

        # 2. 启动 FFmpeg 推流子进程
        self._proc = self._start_ffmpeg(width, height)

        # 3. 主循环：读取 → 推理 → 推流
        self._running = True
        print("开始实时识别推流，按 q 退出")
        try:
            self._main_loop()
        finally:
            self.stop()

    def _main_loop(self):
        while self._running:
            ret, frame = self._cap.read()
            if not ret:
                print("读取帧失败，流可能已断开", file=sys.stderr)
                time.sleep(0.1)
                continue

            # 模型推理标注
            try:
                annotated = self.detector(frame)
            except Exception as e:
                print(f"推理异常: {e}", file=sys.stderr)
                annotated = frame  # 推理失败则推送原帧

            # 推流
            if self._proc.poll() is not None:
                print("ffmpeg 进程已退出，推流中断", file=sys.stderr)
                break

            try:
                self._proc.stdin.write(annotated.tobytes())
            except BrokenPipeError:
                print("ffmpeg 管道断开，推流中断", file=sys.stderr)
                break

            # 本地预览
            if self.show_preview:
                cv2.imshow("Detection Stream", annotated)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

    def _start_ffmpeg(self, width: int, height: int) -> subprocess.Popen:
        """启动 ffmpeg 子进程，从 stdin 读取帧并推送到 dst_url"""
        command = [
            self.ffmpeg_bin,
            "-y",
            "-loglevel", "error",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-pix_fmt", "bgr24",
            "-s", f"{width}x{height}",
            "-r", str(self.fps),
            "-i", "-",                        # 从 stdin 读取
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "ultrafast",
            "-tune", "zerolatency",
            "-b:v", self.bitrate,
            "-f", "rtsp",
            self.dst_url,
        ]
        return subprocess.Popen(command, stdin=subprocess.PIPE, stderr=sys.stderr)

    def stop(self):
        """停止推流"""
        self._running = False
        if self._cap:
            self._cap.release()
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.stdin.close()
                self._proc.wait(timeout=5)
            except Exception:
                self._proc.kill()
        cv2.destroyAllWindows()
        print("推流已停止")
