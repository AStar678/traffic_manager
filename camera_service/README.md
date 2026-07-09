# 虚拟摄像头微服务

这个服务用于模拟系统中的摄像头输入，对前端提供 MJPEG 实时预览和 JPEG 单帧截图。

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
- `GET /api/v1/cameras/stream.mjpg?sourceId=...`
- `GET /api/v1/cameras/snapshot.jpg?sourceId=...`

默认源包含浏览器摄像头推流、OpenCV 设备备用源，以及自动扫描到的车牌测试图片、交警指令测试视频。也可以通过 `POST /api/v1/cameras/source` 传入本机图片或视频路径动态添加源。图片源在实时流中会保持原始像素尺寸，非 16:9 时只补边不缩小；JPEG 图片源的 `/snapshot.jpg` 会直接返回原始文件字节，避免二次压缩影响识别。自定义源和当前活动源会保存到 `camera_service/data/camera_state.json`，服务重启后会恢复。

## 独立管理台

启动服务后打开：

```text
http://127.0.0.1:8010/ui
```

管理台由摄像头微服务自行托管，不接入主系统前端路由。可用于查看源列表、启用源、删除自定义源、实时预览和复制截图地址。

macOS 下 Python/OpenCV 进程可能拿不到摄像头权限，因此推荐在管理台点击“启动摄像头”，由浏览器申请摄像头权限并把帧推送给微服务。主系统仍然只读取微服务的 `/stream.mjpg` 和 `/snapshot.jpg`。

管理台会以较低负载推流：浏览器摄像头上传 640×360 JPEG 二进制帧，默认约 4fps；管理台自身 MJPEG 预览默认 5fps。主系统仍可按自己的流地址读取当前活动源。
