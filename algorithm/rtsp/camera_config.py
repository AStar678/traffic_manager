"""沙盘摄像头配置
来源: 《沙盘摄像头视频流获取.pdf》
智慧交通管理系统场景化沙盘 —— 12路RTSP摄像头
"""

CAMERAS = {
    "live1": {
        "name": "桥面",
        "rtsp_url": "rtsp://10.126.59.120:8554/live/live1",
        "scene": "bridge",
        "use_for": ["license_plate", "vehicle_detection"]
    },
    "live2": {
        "name": "停车场出口",
        "rtsp_url": "rtsp://10.126.59.120:8554/live/live2",
        "scene": "parking_exit",
        "use_for": ["license_plate"]
    },
    "live3": {
        "name": "行人检测",
        "rtsp_url": "rtsp://10.126.59.120:8554/live/live3",
        "scene": "pedestrian",
        "use_for": ["owner_gesture"]
    },
    "live4": {
        "name": "消防车识别",
        "rtsp_url": "rtsp://10.126.59.120:8554/live/live4",
        "scene": "fire_truck",
        "use_for": ["license_plate"]
    },
    "live5": {
        "name": "桥出口",
        "rtsp_url": "rtsp://10.126.59.120:8554/live/live5",
        "scene": "bridge_exit",
        "use_for": ["license_plate"]
    },
    "live6": {
        "name": "桥入口",
        "rtsp_url": "rtsp://10.126.59.120:8554/live/live6",
        "scene": "bridge_entrance",
        "use_for": ["license_plate"]
    },
    "live7": {
        "name": "道路2",
        "rtsp_url": "rtsp://10.126.59.120:8554/live/live7",
        "scene": "road_2",
        "use_for": ["license_plate", "vehicle_detection"]
    },
    "live8": {
        "name": "隧道（事故识别）",
        "rtsp_url": "rtsp://10.126.59.120:8554/live/live8",
        "scene": "tunnel_accident",
        "use_for": ["incident_detection"]
    },
    "live9": {
        "name": "隧道（车辆数量）",
        "rtsp_url": "rtsp://10.126.59.120:8554/live/live9",
        "scene": "tunnel_count",
        "use_for": ["vehicle_counting"]
    },
    "live10": {
        "name": "道路3",
        "rtsp_url": "rtsp://10.126.59.120:8554/live/live10",
        "scene": "road_3",
        "use_for": ["license_plate", "vehicle_detection"]
    },
    "live11": {
        "name": "停车场入口",
        "rtsp_url": "rtsp://10.126.59.120:8554/live/live11",
        "scene": "parking_entrance",
        "use_for": ["license_plate"]
    },
    "live12": {
        "name": "道路1",
        "rtsp_url": "rtsp://10.126.59.120:8554/live/live12",
        "scene": "road_1",
        "use_for": ["license_plate", "vehicle_detection"]
    },
}


def get_camera(scene: str) -> dict:
    """根据场景名获取摄像头配置"""
    for cam_id, cam in CAMERAS.items():
        if cam["scene"] == scene:
            return cam
    return None


def get_cameras_for_task(task: str) -> list:
    """获取适用于某任务的摄像头列表"""
    result = []
    for cam_id, cam in CAMERAS.items():
        if task in cam["use_for"]:
            result.append(cam)
    return result


def get_all_rtsp_urls() -> list:
    """获取所有RTSP地址"""
    return [cam["rtsp_url"] for cam in CAMERAS.values()]
