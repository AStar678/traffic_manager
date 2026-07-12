# 旧虚拟摄像头微服务（已废弃）

> 当前主系统已把三路摄像头管理融合进 Java 主服务。正常开发、部署和验收均不要启动本目录，也不要占用 8010 端口。主前端的“摄像头”模块调用 `/api/v1/cameras/**`，帧通过共享文件目录交给车牌与交警算法。

以下内容仅用于查阅旧实现，不再属于当前运行架构。

这个服务用于模拟系统中的摄像头输入，对前端提供 WebRTC 实时视频预览和 PNG/JPEG 单帧截图。

## 启动

```bash
cd traffic_manager/camera_service
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8010 --no-access-log
```

## 常用接口

- `GET /health`
- `GET /ui`
- `GET /api/v1/cameras/sources`
- `POST /api/v1/cameras/source`
- `DELETE /api/v1/cameras/source/{source_id}`
- `GET /api/v1/cameras/webrtc/status`
- `POST /api/v1/cameras/webrtc/offer`，主系统/管理台订阅当前摄像头源的视频轨道。
- `POST /api/v1/cameras/webrtc/publish`，管理台浏览器摄像头向微服务发布视频轨道。
- `GET /api/v1/cameras/stream.mjpg?sourceId=...`，兼容旧版 MJPEG 预览。
- `GET /api/v1/cameras/snapshot.jpg?sourceId=...`
- `GET /api/v1/cameras/snapshot.png?sourceId=...`，用于主服务识别输入，避免视频帧二次 JPEG 压缩。

默认源包含浏览器摄像头推流、OpenCV 设备备用源，以及自动扫描到的车牌测试图片、交警指令测试视频。也可以通过 `POST /api/v1/cameras/source` 传入本机图片或视频路径动态添加源。实时预览统一走 WebRTC：图片源会作为稳定视频帧持续发送，视频源由摄像头端读取、循环和打时间戳后发送，主系统不需要按功能页重新拉取图片帧。截图接口仍会保持原始像素尺寸，非 16:9 时只补边不缩小；JPEG 图片源的 `/snapshot.jpg` 会直接返回原始文件字节，识别链路推荐使用 `/snapshot.png` 获取无损截图。自定义源和当前活动源会保存到 `camera_service/data/camera_state.json`，服务重启后会恢复。

## 沙盘 RTSP 摄像头

服务内置 PDF 中给出的 12 路沙盘摄像头，启动后会以 `sandbox-live1` 至 `sandbox-live12` 出现在源列表中：

- `live1` 桥面、`live2` 停车场出口、`live3` 行人检测、`live4` 消防车识别
- `live5` 桥出口、`live6` 桥入口、`live7` 道路2、`live8` 隧道事故识别
- `live9` 隧道车辆数量、`live10` 道路3、`live11` 停车场入口、`live12` 道路1

默认地址前缀为 `rtsp://10.126.59.120:8554/live`，可通过环境变量 `SANDBOX_RTSP_BASE_URL` 覆盖。OpenCV 使用 FFmpeg 后端、TCP 传输和单帧缓冲读取，断流后每 2 秒尝试重连。沙盘源进入摄像头服务后，与本机源一样提供 WebRTC、MJPEG 和 PNG/JPEG 快照，因此现有识别页面可以直接使用。

也可以在管理台选择“RTSP 网络流”添加其他流，或调用：

```http
POST /api/v1/cameras/source
Content-Type: application/json

{
  "sourceType": "rtsp",
  "path": "rtsp://10.126.59.120:8554/live/live1",
  "name": "沙盘桥面",
  "fps": 15
}
```

## 独立管理台

启动服务后打开：

```text
http://127.0.0.1:8010/ui
```

管理台由摄像头微服务自行托管，不接入主系统前端路由。可用于查看源列表、启用源、删除自定义源、实时预览和复制截图地址。

macOS 下 Python/OpenCV 进程可能拿不到摄像头权限，因此推荐在管理台点击“启动摄像头”，由浏览器申请摄像头权限并通过 WebRTC 将视频轨道发布给微服务。主系统预览通过 `/api/v1/cameras/webrtc/offer` 订阅视频流，识别读取 `/snapshot.png`。

管理台会以 WebRTC 推流：浏览器摄像头默认请求 1280×720 视频轨道，微服务保留最新原始帧用于截图接口，避免逐帧 HTTP JPEG 上传导致的卡顿、掉帧和音画/帧时间不同步问题。
