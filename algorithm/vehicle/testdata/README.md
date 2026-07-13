# 车辆识别测试素材

- 原始视频：`traffic_pexels_854897.mp4`
- 测试短片：`traffic_test_short.mp4`，前 4 秒，960×540，29.97 FPS，120 帧
- 来源：[Pexels / Pixabay — Video Footage Of Traffic](https://www.pexels.com/video/video-footage-of-traffic-854897/)
- 许可：素材页标记为 Free to use (CC0)

SHA-256：

```text
0d437d64690876a13f6cc9dd0dd2d66de9a5937c5070ef9e13c7433712c77036  traffic_pexels_854897.mp4
aa526d9d2f95a4c70bc9386ccb39550db11330c8affcc9c6bc84f1b007d33a26  traffic_test_short.mp4
```

2026-07-13 本机 CPU 直接运行时测试结果：

```json
{
  "processedFrames": 120,
  "emittedFrames": 120,
  "uniqueVehicleCount": 14,
  "vehicleTypeCounts": {
    "sedan": 10,
    "mpv": 1,
    "hatchback": 2,
    "van": 1
  },
  "latencyMs": 20792,
  "averageFps": 5.77
}
```

通过 `POST /api/v1/inference/video/upload` 的完整 HTTP 链路复测：

```json
{
  "processedFrames": 120,
  "emittedFrames": 120,
  "uniqueVehicleCount": 14,
  "vehicleTypeCounts": {
    "sedan": 10,
    "mpv": 1,
    "hatchback": 2,
    "van": 1
  },
  "latencyMs": 23258,
  "averageFps": 5.16,
  "httpStatus": 200
}
```
