"""统一图片推理接口"""
from fastapi import APIRouter

router = APIRouter()

@router.post("/inference/image")
async def inference_image(request: dict):
    """统一图片推理：通过task_type区分任务类型"""
    # TODO: 根据task_type分发到对应service
    pass
