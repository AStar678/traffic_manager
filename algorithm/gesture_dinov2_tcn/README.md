# DINOv2-TCN 视频原型手势识别运行说明

本目录实现当前系统唯一使用的用户手势识别算法。旧的 MediaPipe 原型算法代码和数据仍保留在 `algorithm/gesture`，但前端、后端业务只应使用 `dinov2_tcn_prototype`。

## 1. 算法与输入

- RGB 编码器：DINOv2-S/14。
- 手部编码器：MediaPipe 21 点图像坐标、世界坐标、检测置信度、左右手信息，以及手指方向、关节角度、掌心方向等自定义几何特征，共 175 维。
- 时序网络：因果 TCN，融合几何特征的一阶速度和二阶加速度。
- 输出：128 维 L2 归一化视频嵌入，与用户录入的原型做余弦相似度匹配。
- 单次窗口：连续 12 帧，每帧包含一个 `224 x 224` RGB 手部裁剪和一组手部关键点。
- 当前相似度阈值：`0.95`。

该算法只识别视频手势，没有系统预设手势。前端不提供动态/静态选择；为了兼容现有接口，录入请求固定传递 `"kind": "dynamic"`。

## 2. 目录与数据

```text
algorithm/
├── gesture/                         # FastAPI 服务入口及旧算法（保留，不删除）
│   ├── main.py
│   ├── requirements.txt
│   └── config/gesture-config.json
└── gesture_dinov2_tcn/
    ├── model.py                     # DINOv2 + 几何特征融合 + TCN
    ├── geometry.py                  # 175 维手部几何特征
    ├── runtime.py                   # 视频采样、原型录入与匹配
    ├── checkpoints/best_model.pt    # 默认部署权重
    └── data/gesture_prototypes.json # DINOv2 用户原型库
```

可以通过环境变量覆盖权重、配置和原型库路径：

| 环境变量 | 默认值 | 用途 |
| --- | --- | --- |
| `GESTURE_ALGORITHM_HOST` | `0.0.0.0` | 监听地址 |
| `GESTURE_ALGORITHM_PORT` | `8002` | 服务端口 |
| `GESTURE_ALGORITHM_THREADS` | `40` | FastAPI 线程池大小 |
| `GESTURE_CONFIG_PATH` | `gesture/config/gesture-config.json` | 运行参数配置 |
| `GESTURE_DINOV2_CHECKPOINT` | `gesture_dinov2_tcn/checkpoints/best_model.pt` | 训练权重 |
| `GESTURE_DINOV2_PROTOTYPE_STORE` | `gesture_dinov2_tcn/data/gesture_prototypes.json` | 用户视频原型库 |
| `CUDA_VISIBLE_DEVICES` | 未限制 | 推理使用的 GPU |

原型库是运行数据，重启服务不会清空。旧算法原型与 DINOv2 原型分开存储。

## 3. 本地启动

建议使用 Python 3.11，并在项目的 `algorithm` 目录中启动，因为 `gesture` 和 `gesture_dinov2_tcn` 是并列 Python 包。

```bash
cd /path/to/traffic_manager/algorithm
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r gesture/requirements.txt
```

放置训练权重：

```bash
mkdir -p gesture_dinov2_tcn/checkpoints
cp /path/to/trained/best_model.pt gesture_dinov2_tcn/checkpoints/best_model.pt
```

也可以不复制权重，直接指定绝对路径：

```bash
export GESTURE_DINOV2_CHECKPOINT=/absolute/path/to/best_model.pt
```

启动服务：

```bash
export GESTURE_ALGORITHM_HOST=0.0.0.0
export GESTURE_ALGORITHM_PORT=8002
export CUDA_VISIBLE_DEVICES=0
python -m gesture.main
```

另开终端激活并预加载 DINOv2-TCN：

```bash
curl --fail -X PUT \
  -H 'Content-Type: application/json' \
  -d '{"algorithm":"dinov2_tcn_prototype"}' \
  http://127.0.0.1:8002/api/v1/owner-gestures/algorithm
```

第一次激活会读取权重并将模型放到 CUDA；没有可用 CUDA 时自动使用 CPU。运行时不需要联网下载 Hugging Face 权重，训练后的 `best_model.pt` 已包含完整模型参数。

## 4. 服务器运行

当前服务器使用用户级 systemd 服务：

- 服务器：`100.73.64.55`
- 部署根目录：`/home/aoxiang/visiondrive`
- 工作目录：`/home/aoxiang/visiondrive/app/algorithm`
- 服务名：`visiondrive-gesture.service`
- Python：`/home/aoxiang/miniconda3/envs/visiondrive/bin/python`
- 端口：`8002`
- 当前训练权重：`/home/aoxiang/visiondrive/output/gesture_dinov2_tcn_proto/full/best_model.pt`

部署目录中的默认权重路径可以链接到训练输出：

```bash
mkdir -p /home/aoxiang/visiondrive/app/algorithm/gesture_dinov2_tcn/checkpoints
ln -sfn \
  /home/aoxiang/visiondrive/output/gesture_dinov2_tcn_proto/full/best_model.pt \
  /home/aoxiang/visiondrive/app/algorithm/gesture_dinov2_tcn/checkpoints/best_model.pt
```

重启、查看状态和日志：

```bash
systemctl --user restart visiondrive-gesture.service
systemctl --user --no-pager --full status visiondrive-gesture.service
journalctl --user -u visiondrive-gesture.service -n 100 --no-pager
```

重启后执行一次激活请求可以立即预热模型，避免第一次摄像头帧请求等待加载：

```bash
curl --fail -X PUT \
  -H 'Content-Type: application/json' \
  -d '{"algorithm":"dinov2_tcn_prototype"}' \
  http://127.0.0.1:8002/api/v1/owner-gestures/algorithm
```

## 5. 健康检查

```bash
curl --fail http://127.0.0.1:8002/health
curl --fail http://127.0.0.1:8002/api/v1/owner-gestures/state
```

正常状态应同时满足：

- `activeAlgorithm` 为 `dinov2_tcn_prototype`；
- DINOv2 选项的 `ready` 为 `true`；
- `checkpointExists` 为 `true`；
- 有 NVIDIA GPU 时 `device` 为 `cuda`；
- `loadError` 为 `null`；
- `sequenceLength` 为 `12`。

`prototypeCount: 0` 只表示尚未录入用户手势，不表示模型启动失败。

可用以下命令确认模型是否占用 GPU：

```bash
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader
```

## 6. 录入与识别接口

直接访问算法服务时，接口前缀是：

```text
http://<algorithm-host>:8002/api/v1/owner-gestures
```

前端通常先访问 Java 后端的 `/api/owner-gestures/*`，再由后端根据 `GESTURE_ALGORITHM_BASE_URL` 转发到该算法服务。

常用接口：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/health` | 服务及模型健康状态 |
| `PUT` | `/api/v1/owner-gestures/algorithm` | 激活并预加载 DINOv2-TCN |
| `GET` | `/api/v1/owner-gestures/state` | 算法、录入和原型库状态 |
| `GET` | `/api/v1/owner-gestures/config` | 当前运行参数 |
| `PATCH` | `/api/v1/owner-gestures/config` | 局部更新阈值等参数 |
| `GET` | `/api/v1/owner-gestures/prototypes` | 查询用户原型 |
| `DELETE` | `/api/v1/owner-gestures/prototypes/{id}` | 删除一个用户原型 |
| `POST` | `/api/v1/owner-gestures/recordings/start` | 开始采集 12 帧视频原型 |
| `POST` | `/api/v1/owner-gestures/recordings/cancel` | 取消录入 |
| `POST` | `/api/v1/owner-gestures/recognize` | 提交一帧视频和关键点 |

开始录入示例：

```bash
curl --fail -X POST \
  -H 'Content-Type: application/json' \
  -d '{"name":"向左滑动","kind":"dynamic","holdMs":1200}' \
  http://127.0.0.1:8002/api/v1/owner-gestures/recordings/start
```

随后连续向 `/recognize` 提交至少 12 帧。每帧 JSON 的关键字段如下：

```json
{
  "type": "frame",
  "frame": "data:image/jpeg;base64,...",
  "landmarks": [[0.1, 0.2, -0.01]],
  "worldLandmarks": [[0.01, 0.02, -0.03]],
  "detectionScore": 0.99,
  "handedness": "Right"
}
```

`landmarks` 必须有 21 个三维点；`worldLandmarks` 可以省略，但提供后通常更稳定。`frame` 必须是 Base64 编码的 RGB 图片或 Data URL。前端默认每 `150 ms` 提交一帧。

修改相似度阈值示例：

```bash
curl --fail -X PATCH \
  -H 'Content-Type: application/json' \
  -d '{"dinov2MatchThreshold":0.95}' \
  http://127.0.0.1:8002/api/v1/owner-gestures/config
```

## 7. 常见故障

### `checkpointExists: false`

权重不在默认位置。检查软链接或设置 `GESTURE_DINOV2_CHECKPOINT`，然后重启服务。

### `activeAlgorithm: mediapipe_prototype`

服务仍处于旧算法配置。调用 `PUT /api/v1/owner-gestures/algorithm` 并传入 `dinov2_tcn_prototype`。该选择会持久化到 `gesture-config.json`。

### `ready: false` 但没有 `loadError`

模型采用延迟加载，服务刚启动且尚未执行激活或识别请求。执行一次算法激活请求进行预热。

### `ready: false` 且存在 `loadError`

优先查看 systemd 日志。常见原因是权重与模型结构不匹配、缺少 `torch`/`transformers`、CUDA 不可用或显存不足。

### 接口返回正常但始终“未录入”

DINOv2 原型库为空，需要在前端“管理手势”中打开摄像头并录入动作。旧 MediaPipe 原型不会被 DINOv2 算法读取。

### 本地后端无法访问服务器算法

确认后端环境中配置了：

```bash
export GESTURE_ALGORITHM_BASE_URL=http://100.73.64.55:8002
```

然后从后端所在机器执行 `curl http://100.73.64.55:8002/health`，确认内网连接和端口可达。
