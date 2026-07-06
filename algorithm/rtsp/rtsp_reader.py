"""RTSP视频流读取工具
基于《沙盘摄像头视频流获取.pdf》参考代码
使用 OpenCV + FFMPEG 后端，TCP传输减少花屏/延迟
"""
import cv2
import threading
import time
from typing import Callable, Optional


class RTSPStreamReader:
    """RTSP视频流读取器

    用法:
        reader = RTSPStreamReader("rtsp://10.126.59.120:8554/live/live1")
        reader.on_frame = lambda frame: print(f"收到帧: {frame.shape}")
        reader.start()
        # ... 处理中 ...
        reader.stop()
    """

    def __init__(self, rtsp_url: str, buffer_size: int = 1):
        self.rtsp_url = rtsp_url
        self.buffer_size = buffer_size
        self.cap: Optional[cv2.VideoCapture] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self.on_frame: Optional[Callable] = None

    def start(self):
        """启动视频流读取"""
        self.cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, self.buffer_size)

        if not self.cap.isOpened():
            raise RuntimeError(f"无法打开视频流: {self.rtsp_url}")

        self._running = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()
        print(f"已连接到视频流: {self.rtsp_url}")

    def _read_loop(self):
        """读取循环（后台线程）"""
        while self._running:
            ret, frame = self.cap.read()
            if not ret:
                print(f"读取帧失败: {self.rtsp_url}")
                time.sleep(0.1)
                continue
            if self.on_frame:
                self.on_frame(frame)

    def get_frame(self) -> Optional[any]:
        """同步获取一帧（用于单帧推理）"""
        if self.cap is None or not self.cap.isOpened():
            return None
        ret, frame = self.cap.read()
        return frame if ret else None

    def save_snapshot(self, filepath: str = "snapshot.jpg"):
        """保存当前帧截图"""
        frame = self.get_frame()
        if frame is not None:
            cv2.imwrite(filepath, frame)
            print(f"已保存截图: {filepath}")
        return frame

    def stop(self):
        """停止视频流"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()
        print(f"已断开视频流: {self.rtsp_url}")

    def is_connected(self) -> bool:
        return self.cap is not None and self.cap.isOpened()
