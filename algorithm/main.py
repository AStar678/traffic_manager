"""VisionDrive 算法微服务入口"""
import uvicorn
from fastapi import FastAPI
from api.inference import router as inference_router
from api.jobs import router as jobs_router
from api.health import router as health_router
import config

app = FastAPI(
    title="VisionDrive Algorithm Service",
    description="车载视觉感知算法微服务 — 车牌识别·交警手势·车主手势",
    version="1.0.0"
)

# 注册路由
app.include_router(health_router, tags=["Health"])
app.include_router(inference_router, prefix="/api/v1", tags=["Inference"])
app.include_router(jobs_router, prefix="/api/v1", tags=["Jobs"])

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=True
    )
