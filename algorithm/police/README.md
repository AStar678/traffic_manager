# 交警手势识别微服务

- 默认端口：`8001`
- 健康检查：`GET /health`
- 推理接口：`POST /api/v1/inference/image`
- 任务类型：`police_gesture`

在项目的 `algorithm/` 目录执行：

```bash
python3 -m venv police/.venv
police/.venv/bin/pip install -r police/requirements.txt
police/.venv/bin/python -m police.main
```

服务默认启动 2 个 Uvicorn 工作进程。可复制 `.env.example` 为 `.env`，通过 `POLICE_ALGORITHM_WORKERS` 调整并发模型进程数。

测试依赖和命令：

```bash
police/.venv/bin/pip install -r police/requirements-dev.txt
police/.venv/bin/python -m pytest -q police/tests
```
