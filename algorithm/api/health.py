"""健康检查接口"""
from fastapi import APIRouter
import config

router = APIRouter()

@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "VisionDrive Algorithm Service",
        "models": {
            "licensePlate": {
                "sourceDir": str(config.LICENSE_PLATE_SOURCE_DIR),
                "clprnetModel": str(config.CLPRNET_MODEL_PATH),
                "modelExists": config.CLPRNET_MODEL_PATH.exists(),
            },
            "gestureRecognition": {
                "appDir": str(config.GESTURE_RECOGNITION_APP_DIR),
                "configPath": str(config.GESTURE_CONFIG_PATH),
                "configExists": config.GESTURE_CONFIG_PATH.exists(),
                "mode": "MediaPipe keypoints + prototype matching engine",
            },
        },
    }
