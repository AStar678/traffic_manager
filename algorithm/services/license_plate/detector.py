"""车牌检测模块 —— CLPRNet
论文: A Single-Stage Multi-Style License Plate Recognition Method Based on Attention
数据集: CCPD (Chinese City Parking Dataset)
"""
import torch
import cv2
import numpy as np

class CLPRNetDetector:
    """CLPRNet 单阶段多风格车牌检测器"""

    def __init__(self, model_path: str, device: str = "cpu"):
        self.device = device
        self.model = None
        self.model_path = model_path
        # TODO: 加载 CLPRNet 预训练权重
        # self.model = CLPRNet()
        # self.model.load_state_dict(torch.load(model_path, map_location=device))
        # self.model.to(device)
        # self.model.eval()

    def detect(self, image: np.ndarray) -> list:
        """检测车牌区域
        Args:
            image: BGR格式图像 (H, W, 3)
        Returns:
            [{object_id, bbox: {x1,y1,x2,y2}, position: {center_x,center_y,width,height}, confidence}]
        """
        # TODO: 实现CLPRNet推理
        # 1. 预处理：resize到模型输入尺寸，归一化
        # 2. 模型前向推理
        # 3. 后处理：NMS去重，坐标还原到原图尺寸
        # 4. 返回检测结果列表
        pass

    def preprocess(self, image: np.ndarray) -> torch.Tensor:
        """图像预处理"""
        # TODO: resize + normalize + to_tensor
        pass

    def postprocess(self, outputs, original_shape: tuple) -> list:
        """后处理：解析模型输出 → 检测框列表"""
        # TODO: decode预测 + NMS + 坐标还原
        pass
