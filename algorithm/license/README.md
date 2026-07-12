# 车牌识别微服务

- 默认端口：`8000`
- 健康检查：`GET /health`
- 推理接口：`POST /api/v1/inference/image`
- 任务类型：`license_plate`

在项目的 `algorithm/` 目录执行：

```bash
python3 -m venv license/.venv
license/.venv/bin/pip install -r license/requirements.txt
license/.venv/bin/python -m license.main
```

服务默认启动 2 个 Uvicorn 工作进程。可复制 `.env.example` 为 `.env`，通过 `LICENSE_ALGORITHM_WORKERS` 调整并发模型进程数。

测试依赖和命令：

```bash
license/.venv/bin/pip install -r license/requirements-dev.txt
license/.venv/bin/python -m pytest -q license/tests
```
