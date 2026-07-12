# 车主手势识别微服务

- 默认端口：`8002`
- 健康检查：`GET /health`
- REST 接口：`/api/v1/owner-gestures/**`、`/api/**`
- WebSocket：`/api/v1/owner-gestures/recognition/stream`、`/api/recognition/stream`

在项目的 `algorithm/` 目录执行：

```bash
python3 -m venv gesture/.venv
gesture/.venv/bin/pip install -r gesture/requirements.txt
gesture/.venv/bin/python -m gesture.main
```

该服务固定单进程以保证录入状态一致，只读识别通过线程池并发执行。可复制 `.env.example` 为 `.env`，通过 `GESTURE_ALGORITHM_THREADS` 调整线程并发数。

测试依赖和命令：

```bash
gesture/.venv/bin/pip install -r gesture/requirements-dev.txt
gesture/.venv/bin/python -m pytest -q gesture/tests
```
