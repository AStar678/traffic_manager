"""人体关键点检测模块 —— MMPose
基于 ctpgr-pytorch 数据集，使用 MMPose 提取骨骼关键点
再用 MMAction2 进行时序动作分类
"""
import numpy as np

class PoseDetector:
    """MMPose 人体关键点检测器

    关键点定义（参考 COCO 17点 + MediaPipe 33点）：
    本项目重点关注上肢关键点：双肩、双肘、双腕
    """

    KEYPOINT_NAMES = [
        "nose", "left_eye", "right_eye", "left_ear", "right_ear",
        "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
        "left_wrist", "right_wrist", "left_hip", "right_hip",
        "left_knee", "right_knee", "left_ankle", "right_ankle"
    ]

    def __init__(self, config_path: str, checkpoint_path: str, device: str = "cpu"):
        self.device = device
        # TODO: 初始化 MMPose 模型
        # from mmpose.apis import init_model
        # self.model = init_model(config_path, checkpoint_path, device=device)

    def detect(self, image: np.ndarray) -> list:
        """检测人体关键点
        Returns:
            [{name: str, x: float, y: float, score: float}, ...]
        """
        # TODO: MMPose推理
        pass
