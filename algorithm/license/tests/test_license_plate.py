"""车牌识别单元测试"""
import base64
import io

from PIL import Image

from license.image_utils import draw_detections


def test_detector():
    pass

def test_ocr():
    pass

def test_pipeline():
    pass


def test_detection_visual_uses_compact_jpeg_data_url():
    image = Image.new("RGB", (320, 180), color=(24, 32, 48))
    data_url = draw_detections(image, [{
        "objectType": "license_plate",
        "plateNumber": "TEST123",
        "plateColor": "blue",
        "bbox": {"x1": 60, "y1": 70, "x2": 220, "y2": 112},
    }])

    prefix, encoded = data_url.split(",", 1)
    assert prefix == "data:image/jpeg;base64"
    rendered = Image.open(io.BytesIO(base64.b64decode(encoded)))
    assert rendered.size == image.size
