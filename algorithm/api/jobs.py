"""异步视频任务接口"""
from fastapi import APIRouter
from datetime import datetime, timezone
import uuid

router = APIRouter()
_jobs = {}

@router.post("/jobs")
async def create_job(request: dict):
    """创建异步视频任务"""
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    job = {
        "jobId": job_id,
        "taskType": request.get("task_type") or request.get("taskType"),
        "status": "queued",
        "progress": 0,
        "message": "视频/RTSP 异步任务接口已预留，当前核心算法图片推理已接通",
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    _jobs[job_id] = job
    return job

@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """查询任务状态"""
    return _jobs.get(job_id, {
        "jobId": job_id,
        "status": "not_found",
        "progress": 0,
        "message": "未找到任务",
    })

@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    """取消任务"""
    job = _jobs.get(job_id)
    if job:
        job["status"] = "cancelled"
        job["message"] = "任务已取消"
        return job
    return {
        "jobId": job_id,
        "status": "not_found",
        "message": "未找到任务",
    }
