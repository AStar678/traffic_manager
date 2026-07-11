# 车主手势控车原型网络 Demo

本地 Web Demo 使用电脑摄像头采集车主手势，基于 MediaPipe Gesture Recognizer 提取手部 21 点关键点。前端只负责摄像头、关键点提取和骨架展示；后端微服务持续运行原型匹配引擎，负责录入、识别、原型库持久化和车辆控制状态。

## 启动

```bash
npm install
npm run local
```

打开 `http://127.0.0.1:5173/`，点击“启动摄像头”，浏览器弹出权限时选择允许。

如果 5173 端口被占用，服务会自动尝试后续端口，并在终端输出实际访问地址。

## 微服务接口

- `GET /api/health`：服务健康检查。
- `GET /api/state`：系统状态，包含原型列表、录入状态、车辆控制状态和当前参数配置。
- `GET /api/config`：查询当前识别参数配置。
- `PATCH /api/config`：局部更新识别参数，服务会合并到现有配置并写回配置文件。
- `PUT /api/config`：替换完整识别参数配置，适合由配置管理服务一次性下发。
- `GET /api/prototypes`：查询已录入原型。
- `DELETE /api/prototypes`：清空原型库。
- `DELETE /api/prototypes/:id`：删除单个原型。
- `POST /api/recordings/start`：开始录入动作。
- `POST /api/recordings/cancel`：取消当前录入。
- `POST /api/recognize`：单次识别接口，输入关键点特征向量。
- `WS /api/recognition/stream`：高频流式识别接口，前端每帧发送特征向量，服务端返回识别结果、录入进度和车辆状态。

原型库持久化在 `data/prototypes.json`。WebSocket 用于高频帧数据，避免每帧 HTTP 请求带来的连接和头部开销。

识别阈值、静态维持时间、动态运动量、手掌正反面检查、触发冷却、采样帧数和车辆控制步进等运行参数保存在 `config/gesture-config.json`，不写死在识别代码中。参数字段说明见 `docs/gesture-parameters.md`。

## 操作流程

1. 输入动作名称。
2. 选择要绑定的车辆操作。
3. 选择识别类型：静态姿态或动态轨迹。
4. 选择触发持续时间。
5. 点击“开始录入”，对摄像头完成动作，系统会按配置采集指定帧数的手部关键点。
4. 录入完成后，继续做同一个动作，页面会显示原型匹配结果、相似度和触发状态。

## 本地模型文件

- `public/models/gesture_recognizer.task`：MediaPipe 官方预训练手势识别权重。
- `public/wasm/`：MediaPipe Tasks Vision 的本地 WASM 运行文件。

## 识别逻辑

- 静态手势：使用当前帧关键点向量与原型平均向量做余弦相似度匹配，并优先使用 3D 手部关键点检查手掌/手背朝向一致性；允许自然抖动和小幅变化，姿态维持时间由配置控制。
- 动态动作：使用最近滑动窗口与录入时保存的序列做轨迹相似度匹配，并要求实时运动量达到配置门槛；自然抖动和小动作不视为动态。
- 误触发抑制：相似度低于阈值时拒识，同一动作连续命中达到设定持续时间后才触发，触发冷却时间由配置控制。
