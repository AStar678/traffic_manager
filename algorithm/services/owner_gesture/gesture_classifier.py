"""车主手势分类模块 —— 原型网络 (Prototypical Network)
基于 HaGRIDv2 数据集训练
使用几何规则做初筛 + 原型网络做少样本分类

手势定义（按《算法技术路线》文档）：
  - 静态手势：手掌张开、握拳、拇指向上/向下 → 几何规则判定
  - 动态手势：单指画圈、左右滑动、挥手 → 时序运动特征 + 原型网络
"""
import numpy as np

class OwnerGestureClassifier:
    """车主手势分类器 —— 原型网络"""

    GESTURE_MAP = {
        1: ("001", "手掌张开", "启动/唤醒系统", "static"),
        2: ("002", "握拳", "确认/执行", "static"),
        3: ("003", "单指画圈", "调节音量", "dynamic"),
        4: ("004", "左右滑动", "切换功能", "dynamic"),
        5: ("005", "拇指向上", "接听电话", "static"),
        6: ("006", "拇指向下", "挂断电话", "static"),
        7: ("007", "挥手", "返回主页", "dynamic"),
    }

    def __init__(self, model_path: str = None):
        self.model_path = model_path
        self.keypoint_history = []  # 动态手势需维护关键点历史
        # TODO: 加载原型网络模型
        # self.prototype_net = PrototypicalNetwork()

    def classify_static(self, keypoints: list) -> dict:
        """静态手势分类（几何规则）
        通过手指角度、指间距离等几何特征判定
        """
        # TODO: 实现几何规则判定
        # - 五指伸展角度 > 阈值 → 手掌张开
        # - 五指蜷曲，指尖贴近掌心 → 握拳
        # - 拇指与垂直方向角度 > 60° → 拇指向上
        # - 拇指与垂直方向角度 < -60° → 拇指向下
        pass

    def classify_dynamic(self, keypoint_sequence: list) -> dict:
        """动态手势分类（原型网络）
        通过原型网络对关键点运动轨迹进行分类
        """
        # TODO: 原型网络推理
        # 1. 计算关键点运动轨迹特征
        # 2. 与各类原型计算距离
        # 3. 最近原型 → 手势类别
        pass

    def classify(self, keypoints: list) -> dict:
        """统一分类入口
        Returns:
            {gesture_code: str, gesture_name: str, action: str, confidence: float}
        """
        # TODO: 先判断静态/动态，再分发
        pass

    def reset_history(self):
        """清空关键点历史"""
        self.keypoint_history.clear()
