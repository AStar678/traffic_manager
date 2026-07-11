# 手势识别参数配置

运行时参数保存在 `config/gesture-config.json`。服务启动时读取该文件，调用 `PATCH /api/config` 或 `PUT /api/config` 后会立即更新内存中的识别引擎，并持久化回该文件。

## 配置接口

```http
GET /api/config
```

返回当前配置：

```json
{
  "config": {
    "sampleTarget": 45
  }
}
```

```http
PATCH /api/config
Content-Type: application/json

{
  "staticRecognitionHoldMs": 300,
  "staticMatchThreshold": 0.7
}
```

局部更新配置。适合调参服务只修改某几个字段。

```http
PUT /api/config
Content-Type: application/json

{
  "...": "完整配置对象"
}
```

替换完整配置。适合配置中心下发整份参数。

## 字段说明

| 字段 | 作用 |
| --- | --- |
| `sampleTarget` | 录入和动态识别使用的滑动窗口帧数。 |
| `staticMatchThreshold` | 静态姿态余弦相似度通过阈值，越高越严格。 |
| `dynamicMatchThreshold` | 动态轨迹综合相似度通过阈值，越高越严格。 |
| `palmDirectionThreshold` | 手掌/手背朝向一致性通过阈值。 |
| `palmWorldDirectionThreshold` | 使用 3D 世界坐标判断掌心方向时的通过阈值。 |
| `palmWorldMismatchPenalty` | 3D 掌心方向不一致时的分数惩罚系数。 |
| `minDynamicMotion` | 动态动作的最低实时运动量，小于该值会被视作未完成动态动作。 |
| `staticStillMotionLimit` | 静态识别允许的小幅运动上限。 |
| `staticMotionHardLimit` | 静态姿态运动惩罚归一化上限。 |
| `staticMotionPenaltyMax` | 静态姿态因运动过大扣除的最高分值。 |
| `dynamicMotionRatio` | 动态动作实时运动量相对于录入运动量的最低比例。 |
| `staticRecognitionHoldMs` | 静态姿态需要连续稳定的时间，单位毫秒。 |
| `triggerCooldownMs` | 同一动作触发后的冷却时间，单位毫秒。 |
| `defaultHoldMs` | 录入动作未指定触发持续时间时使用的默认值，单位毫秒。 |
| `sequencePoseWeight` | 动态识别中逐帧姿态相似度权重。 |
| `sequencePathWeight` | 动态识别中轨迹路径相似度权重。 |
| `vehicleVolumeStep` | 音量增减动作每次调整的步长。 |
| `vehicleVolumeMin` | 音量下限。 |
| `vehicleVolumeMax` | 音量上限。 |
| `motionTrackedIndexes` | 用于计算运动量和轨迹的特征向量坐标索引对。 |
| `vehicleFeatureNames` | 模拟车机功能列表。 |
| `defaultVehicleState` | 服务启动时的模拟车辆初始状态。 |
