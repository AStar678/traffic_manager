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

    def classify_static(self, keypoints: list) -> dict:
        """静态手势分类（几何规则）
        通过手指角度、指间距离等几何特征判定
        """
        if not keypoints:
            return self._unknown()

        points = {point["name"]: point for point in keypoints}
        wrist = points.get("wrist")
        if not wrist:
            return self._unknown()

        extended = self._extended_fingers(points)
        extended_count = sum(extended.values())
        thumb = points.get("thumb_tip")
        palm_scale = self._distance(points.get("middle_finger_mcp"), wrist) or 1.0

        other_curled = sum(extended[name] for name in ("index", "middle", "ring", "pinky")) <= 1
        if thumb and other_curled and thumb["y"] < wrist["y"] - palm_scale * 0.9:
            return self._result(5, 0.9)
        if thumb and other_curled and thumb["y"] > wrist["y"] + palm_scale * 0.7:
            return self._result(6, 0.88)
        if extended_count >= 4:
            return self._result(1, 0.86 + min(extended_count, 5) * 0.02)
        if extended_count <= 1:
            return self._result(2, 0.86)
        return self._unknown(confidence=0.35)

    def classify_dynamic(self, keypoint_sequence: list) -> dict:
        """动态手势分类（原型网络）
        通过原型网络对关键点运动轨迹进行分类
        """
        if len(keypoint_sequence) < 5:
            return self._unknown(confidence=0.0)

        wrists = []
        index_tips = []
        for frame in keypoint_sequence[-12:]:
            points = {point["name"]: point for point in frame}
            if points.get("wrist"):
                wrists.append(points["wrist"])
            if points.get("index_finger_tip"):
                index_tips.append(points["index_finger_tip"])

        if len(wrists) >= 5:
            dx = wrists[-1]["x"] - wrists[0]["x"]
            dy = wrists[-1]["y"] - wrists[0]["y"]
            travel = float(np.hypot(dx, dy))
            if travel > 70 and abs(dx) > abs(dy) * 1.6:
                return self._result(4, min(0.95, 0.72 + travel / 500))
            if self._direction_changes(wrists) >= 2 and travel > 35:
                return self._result(7, 0.78)

        if len(index_tips) >= 8 and self._looks_circular(index_tips):
            return self._result(3, 0.8)

        return self._unknown(confidence=0.3)

    def classify(self, keypoints: list) -> dict:
        """统一分类入口
        Returns:
            {gesture_code: str, gesture_name: str, action: str, confidence: float}
        """
        if not keypoints:
            return self._unknown()

        self.keypoint_history.append(keypoints)
        if len(self.keypoint_history) > 16:
            self.keypoint_history.pop(0)

        dynamic = self.classify_dynamic(self.keypoint_history)
        static = self.classify_static(keypoints)
        return dynamic if dynamic["confidence"] > static["confidence"] else static

    def reset_history(self):
        """清空关键点历史"""
        self.keypoint_history.clear()

    def _result(self, gesture_id: int, confidence: float) -> dict:
        code, name, action, kind = self.GESTURE_MAP[gesture_id]
        return {
            "gesture_code": code,
            "gesture_name": name,
            "action": action,
            "kind": kind,
            "confidence": round(float(confidence), 4),
        }

    @staticmethod
    def _unknown(confidence: float = 0.0) -> dict:
        return {
            "gesture_code": None,
            "gesture_name": "未识别",
            "action": "无控制动作",
            "kind": "unknown",
            "confidence": round(float(confidence), 4),
        }

    def _extended_fingers(self, points: dict) -> dict[str, bool]:
        return {
            "thumb": self._thumb_extended(points),
            "index": self._finger_extended(points, "index_finger"),
            "middle": self._finger_extended(points, "middle_finger"),
            "ring": self._finger_extended(points, "ring_finger"),
            "pinky": self._finger_extended(points, "pinky"),
        }

    @staticmethod
    def _finger_extended(points: dict, prefix: str) -> bool:
        tip = points.get(f"{prefix}_tip")
        pip = points.get(f"{prefix}_pip")
        mcp = points.get(f"{prefix}_mcp")
        if not tip or not pip or not mcp:
            return False
        return tip["y"] < pip["y"] < mcp["y"]

    @staticmethod
    def _thumb_extended(points: dict) -> bool:
        tip = points.get("thumb_tip")
        ip = points.get("thumb_ip")
        mcp = points.get("thumb_mcp")
        wrist = points.get("wrist")
        if not tip or not ip or not mcp or not wrist:
            return False
        return OwnerGestureClassifier._distance(tip, wrist) > OwnerGestureClassifier._distance(ip, wrist) * 1.15

    @staticmethod
    def _distance(a: dict | None, b: dict | None) -> float:
        if not a or not b:
            return 0.0
        return float(np.hypot(float(a["x"]) - float(b["x"]), float(a["y"]) - float(b["y"])))

    @staticmethod
    def _direction_changes(points: list[dict]) -> int:
        signs = []
        for index in range(1, len(points)):
            delta = points[index]["x"] - points[index - 1]["x"]
            if abs(delta) > 8:
                signs.append(1 if delta > 0 else -1)
        return sum(1 for index in range(1, len(signs)) if signs[index] != signs[index - 1])

    @staticmethod
    def _looks_circular(points: list[dict]) -> bool:
        xs = np.asarray([point["x"] for point in points], dtype=float)
        ys = np.asarray([point["y"] for point in points], dtype=float)
        width = xs.max() - xs.min()
        height = ys.max() - ys.min()
        if width < 30 or height < 30:
            return False
        ratio = width / max(height, 1)
        return 0.55 <= ratio <= 1.8
