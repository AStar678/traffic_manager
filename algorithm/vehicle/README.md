# PP-Vehicle 车辆类别识别微服务

该服务遵循 `algorithm/license` 和 `algorithm/police` 的 FastAPI 微服务结构，本地默认使用 `8003`，GPU 服务器使用 `8004`（`8003` 已由 WebRTC 占用）。推理链路直接复用 PaddleDetection 官方 PP-Vehicle：

1. PP-YOLOE 车辆检测；
2. OC-SORT 多目标跟踪，生成稳定 `trackId`；
3. PP-LCNet 识别车辆颜色及类别；
4. 按 `trackId` 对多帧类别结果投票平滑，降低标签抖动。

支持的官方车辆类别为 `sedan`、`suv`、`van`、`hatchback`、`mpv`、`pickup`、`bus`、`truck` 和 `estate`。实现依据可参考 [PP-Vehicle 快速开始](https://github.com/PaddlePaddle/PaddleDetection/blob/release/2.9/deploy/pipeline/docs/tutorials/PPVehicle_QUICK_STARTED.md)。

## API

- `GET /health`：服务及模型状态；
- `POST /api/v1/inference/image`：主服务传入摄像头共享帧；同一 `sourceId` 保持稳定 `trackId`；
- `POST /api/v1/inference/video`：后端通过 JSON 传入共享文件路径、HTTP 视频地址或 RTSP/RTMP 流；
- `POST /api/v1/inference/video/upload`：上传视频并接收流式结果；
- `GET /`：无构建步骤的极简测试前端。

两个推理接口均返回 `application/x-ndjson`，每行是一个 JSON 事件：

```json
{"event":"meta","video":{"width":1920,"height":1080,"fps":25}}
{"event":"frame","frameIndex":12,"timestampMs":480,"detections":[{"trackId":3,"vehicleType":"suv","vehicleTypeName":"SUV","confidence":0.91,"bbox":{"x1":101,"y1":220,"x2":488,"y2":610}}]}
{"event":"complete","summary":{"uniqueVehicleCount":7,"vehicleTypeCounts":{"suv":4,"sedan":3}}}
```

后端共享路径调用示例：

```bash
curl -N http://localhost:8003/api/v1/inference/video \
  -H 'Content-Type: application/json' \
  -d '{"task_type":"vehicle_type","video_path":"/app/uploads/videos/road.mp4"}'
```

Docker Compose 已将现有 `backend_uploads` 卷挂载到车辆算法容器的相同路径 `/app/uploads`，因此后端只需传递绝对路径，不需要再传输视频字节。

## 本地启动

PP-Vehicle 依赖应与服务依赖分开安装，便于根据 CPU/CUDA 环境选择 PaddlePaddle 轮子：

```bash
cd traffic_manager/algorithm
python3.10 -m venv vehicle/.venv
vehicle/.venv/bin/pip install -r vehicle/requirements.txt
vehicle/.venv/bin/pip install paddlepaddle==2.6.2
git clone --depth 1 --branch release/2.9 https://github.com/PaddlePaddle/PaddleDetection.git /opt/PaddleDetection
vehicle/.venv/bin/pip install -r /opt/PaddleDetection/requirements.txt
```

下载官方轻量 MOT 和车辆属性模型：

```bash
sh vehicle/scripts/download_models.sh ../models/ppvehicle
cp vehicle/.env.example vehicle/.env
# 将 .env 中两个模型路径改为上一步生成的 mot/ 和 attr/
vehicle/.venv/bin/python -m vehicle.main
```

已下载文件的 SHA-256 记录在 [`models.sha256`](models.sha256)，可在 `traffic_manager/models/ppvehicle` 下执行：

```bash
shasum -a 256 -c ../../algorithm/vehicle/models.sha256
```

打开 [http://localhost:8003](http://localhost:8003) 即可使用内置测试页。

### macOS Apple Silicon

当前工作区已下载并实测以下组合：

- PaddlePaddle `3.3.0` CPU（Python 3.13 / arm64）；
- PaddleDetection `release/2.9` commit `b25522a0f4bde8c80603f3ba5e3472059972e3b5`；
- `mot_ppyoloe_s_36e_ppvehicle` 轻量跟踪模型；
- `vehicle_attribute_model` 车辆属性模型。

重建本机环境：

```bash
cd traffic_manager/algorithm
python3 -m venv vehicle/.venv
vehicle/.venv/bin/pip install -r vehicle/requirements-macos-arm64.txt
vehicle/.venv/bin/pip install paddlepaddle==3.3.0 \
  -i https://www.paddlepaddle.org.cn/packages/stable/cpu/
```

当前已生成本地 `vehicle/.env`，可直接启动：

```bash
cd traffic_manager/algorithm
MPLCONFIGDIR=/tmp/visiondrive-matplotlib \
  vehicle/.venv/bin/python -m vehicle.main
```

另一个终端运行 HTTP 冒烟测试：

```bash
cd traffic_manager/algorithm
vehicle/.venv/bin/python vehicle/scripts/smoke_test.py \
  vehicle/testdata/traffic_test_short.mp4
```

测试素材来源、SHA-256 和实测结果见 [`testdata/README.md`](testdata/README.md)。Paddle 3.x 下服务会自动兼容官方下载包中的历史 `model.pdmodel` 格式。

## Docker

```bash
cd traffic_manager/docker
docker compose -f docker-compose.yml -f docker-compose.vehicle.yml up --build vehicle
```

Docker 与 `deployment/server` 均默认使用 PaddlePaddle 3.3.0 CUDA 11.8 GPU 推理，并设置 `PPVEHICLE_DEVICE=GPU`。正式服务只运行一个 Uvicorn worker，三路摄像头共享一份模型，避免重复占用显存。

## 测试

```bash
cd traffic_manager/algorithm
.venv/bin/python -m pytest -q vehicle/tests
```

单元测试使用假运行时验证 NDJSON 协议、上传清理、路径安全和多帧标签平滑，不需要下载大型模型。
