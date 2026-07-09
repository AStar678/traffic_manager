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
                "checkpointDir": str(config.POLICE_GESTURE_SOURCE_DIR / "checkpoints"),
                "checkpointExists": (config.POLICE_GESTURE_SOURCE_DIR / "checkpoints" / "lstm.pt").exists(),
            },
            "ownerGesture": {
                "sourceDir": str(config.OWNER_GESTURE_SOURCE_DIR),
                "mode": "MediaPipe Hands + geometry classifier",
            },
        },
    }
