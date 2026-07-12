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
            "policeGesture": {
                "sourceDir": str(config.POLICE_GESTURE_SOURCE_DIR),
                "poseModel": str(config.POLICE_GESTURE_SOURCE_DIR / "checkpoints" / "pose_model.pt"),
                "lstmModel": str(config.POLICE_GESTURE_SOURCE_DIR / "checkpoints" / "lstm.pt"),
                "modelExists": all((config.POLICE_GESTURE_SOURCE_DIR / "checkpoints" / name).exists()
                                   for name in ("pose_model.pt", "lstm.pt")),
                "mode": "ctpgr-pytorch pose + LSTM",
            },
            "gestureRecognition": {
                "appDir": str(config.GESTURE_RECOGNITION_APP_DIR),
                "configPath": str(config.GESTURE_CONFIG_PATH),
                "configExists": config.GESTURE_CONFIG_PATH.exists(),
                "mode": "MediaPipe keypoints + prototype matching engine",
            },
        },
    }
