"""Mock 车牌检测器 —— 模型就绪前用于测试推流管线

在画面中随机位置生成模拟的车牌识别标注，支持中文显示（使用 PIL）。
"""
import random
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# 模拟车牌号
PLATES = [
    "京A·12345", "沪B·67890", "粤C·11111",
    "苏D·22222", "浙E·33333", "鲁F·44444",
    "豫G·55555", "川H·66666", "鄂I·77777",
]

# 模拟车牌颜色及对应 BGR
COLOR_BGR = {
    "蓝牌": (255, 0, 0),
    "绿牌": (0, 255, 0),
    "黄牌": (0, 255, 255),
    "白牌": (255, 255, 255),
}

# 中文字体
_FONT_PATH = "C:/Windows/Fonts/simhei.ttf"


def _get_font(size: int = 18):
    try:
        return ImageFont.truetype(_FONT_PATH, size)
    except Exception:
        return ImageFont.load_default()


class MockLicensePlateDetector:
    """模拟车牌检测器 —— 在帧上随机生成标注"""

    def __init__(self, plate_count: int = 2, refresh_interval: int = 30):
        self.plate_count = plate_count
        self.refresh_interval = refresh_interval
        self._frame_idx = 0
        self._boxes = []
        self._img_w = 1280
        self._img_h = 720

    def __call__(self, frame: np.ndarray) -> np.ndarray:
        h, w = frame.shape[:2]
        if w != self._img_w or h != self._img_h:
            self._img_w, self._img_h = w, h
            self._boxes = []

        if self._frame_idx % self.refresh_interval == 0:
            self._boxes = self._generate_boxes(w, h)

        self._frame_idx += 1
        return self._draw_boxes(frame)

    def _generate_boxes(self, img_w: int, img_h: int):
        boxes = []
        for _ in range(self.plate_count):
            cx = random.randint(int(img_w * 0.15), int(img_w * 0.85))
            cy = random.randint(int(img_h * 0.3), int(img_h * 0.85))
            bw = random.randint(80, 160)
            bh = random.randint(25, 50)

            x1 = max(0, cx - bw // 2)
            y1 = max(0, cy - bh // 2)
            x2 = min(img_w, x1 + bw)
            y2 = min(img_h, y1 + bh)

            plate = random.choice(PLATES)
            color_name = random.choice(list(COLOR_BGR.keys()))
            confidence = round(random.uniform(0.82, 0.99), 2)

            boxes.append((x1, y1, x2, y2, plate, color_name, confidence))
        return boxes

    def _draw_boxes(self, frame: np.ndarray) -> np.ndarray:
        """用 PIL 绘制中文标注"""
        # 转 BGR → RGB → PIL
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img_rgb)
        draw = ImageDraw.Draw(pil_img)
        font = _get_font(16)

        for (x1, y1, x2, y2, plate, color_name, confidence) in self._boxes:
            bgr = COLOR_BGR[color_name]
            rgb = (bgr[2], bgr[1], bgr[0])  # BGR → RGB

            # 画框
            draw.rectangle([x1, y1, x2, y2], outline=rgb, width=2)

            # 标签文字
            label = f"{plate}  {color_name}  {confidence:.0%}"
            bbox = draw.textbbox((0, 0), label, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]

            label_y = y1 - th - 6
            if label_y < 0:
                label_y = y2 + 2

            # 标签背景
            draw.rectangle(
                [x1, label_y, x1 + tw + 8, label_y + th + 6],
                fill=rgb,
            )
            # 标签文字（白色字用黑色，其他用白色）
            text_color = (0, 0, 0) if color_name in ("白牌", "黄牌") else (255, 255, 255)
            draw.text((x1 + 4, label_y + 2), label, fill=text_color, font=font)

        # PIL → RGB → BGR → numpy
        return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
