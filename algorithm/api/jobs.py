"""异步视频任务接口"""
from fastapi import APIRouter

router = APIRouter()

@router.post("/jobs")
async def create_job(request: dict):
    """创建异步视频任务"""
    pass

@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """查询任务状态"""
    pass

@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    """取消任务"""
    pass
