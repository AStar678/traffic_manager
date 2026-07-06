"""交警手势分类模块 —— MMAction2 时序动作识别
基于 ctpgr-pytorch 数据集训练，MMPose提取关键点后
用 MMAction2 的 ST-GCN / PoseC3D 进行时序分类
"""
import numpy as np

class PoliceGestureClassifier:
    """交警手势时序分类器

    8种中国标准交警手势:
    """

    GESTURE_MAP = {
        0: ("STOP", "停止信号"),
        1: ("GO_STRAIGHT", "直行信号"),
        2: ("LEFT_TURN", "左转弯信号"),
        3: ("LEFT_WAIT", "左转弯待转信号"),
        4: ("RIGHT_TURN", "右转弯信号"),
        5: ("LANE_CHANGE", "变道信号"),
        6: ("SLOW_DOWN", "减速慢行信号"),
        7: ("PULL_OVER", "靠边停车信号"),
    }

    def __init__(self, config_path: str, checkpoint_path: str, device: str = "cpu"):
        self.device = device
        self.sequence_length = 30  # 30帧窗口（1秒@30fps）
        self.keypoint_buffer = []  # 关键点序列缓冲区
        # TODO: 初始化 MMAction2 模型
        # from mmaction2.apis import init_model
        # self.model = init_model(config_path, checkpoint_path, device=device)

    def add_frame(self, keypoints: list):
        """添加一帧关键点，维护滑动窗口"""
        self.keypoint_buffer.append(keypoints)
        if len(self.keypoint_buffer) > self.sequence_length:
            self.keypoint_buffer.pop(0)

    def classify(self) -> dict:
        """对当前缓冲的关键点序列进行分类
        Returns:
            {gesture_code: str, gesture_name: str, confidence: float}
        """
        if len(self.keypoint_buffer) < self.sequence_length:
            return {"gesture_code": None, "gesture_name": "识别中...", "confidence": 0.0}
        # TODO: MMAction2 推理
        # 1. 关键点序列 → 骨架图/特征向量
        # 2. ST-GCN/PoseC3D 前向推理
        # 3. Softmax → 手势类别
        pass

    def reset(self):
        """清空关键点缓冲区"""
        self.keypoint_buffer.clear()
