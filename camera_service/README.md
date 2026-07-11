# 虚拟摄像头微服务

这个服务用于模拟系统中的摄像头输入，对前端提供 WebRTC 实时视频预览和 PNG/JPEG 单帧截图。

## 启动

```bash
cd traffic_manager/camera_service
../algorithm/.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8010 --no-access-log
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

## 独立管理台

启动服务后打开：

```text
http://127.0.0.1:8010/ui
```

管理台由摄像头微服务自行托管，不接入主系统前端路由。可用于查看源列表、启用源、删除自定义源、实时预览和复制截图地址。

macOS 下 Python/OpenCV 进程可能拿不到摄像头权限，因此推荐在管理台点击“启动摄像头”，由浏览器申请摄像头权限并通过 WebRTC 将视频轨道发布给微服务。主系统预览通过 `/api/v1/cameras/webrtc/offer` 订阅视频流，识别读取 `/snapshot.png`。

管理台会以 WebRTC 推流：浏览器摄像头默认请求 1280×720 视频轨道，微服务保留最新原始帧用于截图接口，避免逐帧 HTTP JPEG 上传导致的卡顿、掉帧和音画/帧时间不同步问题。
