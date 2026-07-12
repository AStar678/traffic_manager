import unittest
from unittest.mock import patch

import numpy as np

from config import SANDBOX_RTSP_BASE_URL
from services import sources


class FakeCapture:
    def __init__(self):
        self.opened = True
        self.settings = []
        self.released = False

    def isOpened(self):
        return self.opened

    def set(self, key, value):
        self.settings.append((key, value))
        return True

    def get(self, key):
        if key == sources.cv2.CAP_PROP_FPS:
            return 15
        return 0

    def read(self):
        return True, np.zeros((720, 1280, 3), dtype=np.uint8)

    def release(self):
        self.opened = False
        self.released = True


class SandboxSourceTest(unittest.TestCase):
    def test_all_twelve_sandbox_channels_are_built_in(self):
        sandbox = [item for item in sources.build_default_sources() if item.sourceType == "rtsp"]

        self.assertEqual(12, len(sandbox))
        self.assertEqual("sandbox-live1", sandbox[0].id)
        self.assertEqual(f"{SANDBOX_RTSP_BASE_URL}/live12", sandbox[-1].path)
        self.assertTrue(all(item.builtIn for item in sandbox))

    def test_custom_rtsp_source_validation(self):
        custom = sources.make_custom_source(
            "rtsp",
            path="rtsp://127.0.0.1:8554/demo",
            name="测试流",
        )
        self.assertEqual("rtsp", custom.sourceType)
        self.assertEqual("测试流", custom.name)

        with self.assertRaisesRegex(ValueError, "RTSP"):
            sources.make_custom_source("rtsp", path="http://example.com/video")

    def test_rtsp_reader_uses_ffmpeg_and_single_frame_buffer(self):
        capture = FakeCapture()
        source = sources.CameraSource(
            id="sandbox-live1",
            name="沙盘桥面",
            sourceType="rtsp",
            path="rtsp://127.0.0.1:8554/live/live1",
            fps=15,
        )

        with patch.object(sources.cv2, "VideoCapture", return_value=capture) as video_capture:
            reader = sources.FrameReader(source)
            try:
                frame, meta = reader.read_with_meta()
                self.assertEqual((720, 1280, 3), frame.shape)
                self.assertEqual("sandbox-live1", meta["sourceId"])
                video_capture.assert_called_with(source.path, sources.cv2.CAP_FFMPEG)
                self.assertIn((sources.cv2.CAP_PROP_BUFFERSIZE, 1), capture.settings)
            finally:
                reader.close()


if __name__ == "__main__":
    unittest.main()
