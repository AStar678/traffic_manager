import { TASK_TYPES } from './constants'

function svgDataUrl(svg) {
  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`
}

/* ===== 模拟道路/摄像头画面(SVG) ===== */
export const sampleImages = {
  road: svgDataUrl(`
    <svg xmlns="http://www.w3.org/2000/svg" width="1200" height="720" viewBox="0 0 1200 720">
      <defs>
        <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#3a5a7c"/><stop offset="55%" stop-color="#2a3a4c"/>
          <stop offset="56%" stop-color="#1a2a3c"/><stop offset="100%" stop-color="#0f1a28"/>
        </linearGradient>
      </defs>
      <rect width="1200" height="720" fill="url(#sky)"/>
      <path d="M420 720 L550 380 H650 L820 720 Z" fill="#1a2535"/>
      <path d="M596 700 L600 610 M602 560 L604 500 M606 460 L608 420" stroke="#3a5070" stroke-width="10" stroke-dasharray="38 28"/>
      <rect x="185" y="220" width="300" height="120" rx="18" fill="#1e3048"/>
      <rect x="700" y="250" width="280" height="115" rx="18" fill="#253a50"/>
      <rect x="235" y="304" width="170" height="38" rx="6" fill="#dbeafe"/>
      <rect x="758" y="328" width="158" height="36" rx="6" fill="#dcfce7"/>
      <text x="32" y="48" font-family="Arial" font-size="24" font-weight="700" fill="#a0b8d0">RTSP live1 桥面道路 · 前置摄像头</text>
    </svg>
  `),
  police: svgDataUrl(`
    <svg xmlns="http://www.w3.org/2000/svg" width="1200" height="720" viewBox="0 0 1200 720">
      <rect width="1200" height="720" fill="#121a26"/>
      <rect y="470" width="1200" height="250" fill="#1c2838"/>
      <g stroke="#d0d8e0" stroke-width="18" opacity="0.85">
        <line x1="0" y1="565" x2="1200" y2="565"/>
        <line x1="0" y1="640" x2="1200" y2="640"/>
      </g>
      <circle cx="640" cy="130" r="48" fill="#facc15"/>
      <rect x="570" y="180" width="140" height="220" rx="60" fill="#1a5dc8"/>
      <rect x="536" y="250" width="38" height="210" rx="19" fill="#facc15"/>
      <rect x="706" y="230" width="38" height="210" rx="19" transform="rotate(-35 725 335)" fill="#facc15"/>
      <rect x="590" y="390" width="42" height="210" rx="20" fill="#0e1520"/>
      <rect x="652" y="390" width="42" height="210" rx="20" fill="#0e1520"/>
      <text x="32" y="48" font-family="Arial" font-size="24" font-weight="700" fill="#a0b8d0">路口摄像头 · 交警手势识别</text>
    </svg>
  `),
  cockpit: svgDataUrl(`
    <svg xmlns="http://www.w3.org/2000/svg" width="1200" height="720" viewBox="0 0 1200 720">
      <rect width="1200" height="720" fill="#0a0f18"/>
      <rect x="80" y="90" width="1040" height="520" rx="34" fill="#141d2a"/>
      <rect x="130" y="130" width="600" height="300" rx="20" fill="#0a1220"/>
      <rect x="780" y="150" width="270" height="80" rx="12" fill="#1e2a3a"/>
      <rect x="780" y="260" width="270" height="80" rx="12" fill="#1e2a3a"/>
      <rect x="780" y="370" width="270" height="80" rx="12" fill="#1e2a3a"/>
      <circle cx="430" cy="520" r="85" fill="none" stroke="#2a3a50" stroke-width="28"/>
      <text x="32" y="48" font-family="Arial" font-size="24" font-weight="700" fill="#a0b8d0">车内摄像头 · 手势控车测试平台</text>
    </svg>
  `)
}

/* ===== 车牌检测 ===== */
export const mockLicenseDetections = [
  {
    objectId: 'plate_001',
    objectType: 'license_plate',
    bbox: { x1: 210, y1: 250, x2: 438, y2: 318 },
    position: { centerX: 324, centerY: 284, width: 228, height: 68 },
    plateNumber: '京A12345',
    plateColor: 'blue',
    plateType: '蓝牌小型车',
    detectionConfidence: 0.97,
    ocrConfidence: 0.94,
    confidence: 0.96,
    frameNo: 182,
    timestamp: '00:00:07.28'
  },
  {
    objectId: 'plate_002',
    objectType: 'license_plate',
    bbox: { x1: 695, y1: 284, x2: 910, y2: 350 },
    position: { centerX: 802, centerY: 317, width: 215, height: 66 },
    plateNumber: '沪B8K218',
    plateColor: 'green',
    plateType: '新能源车牌',
    detectionConfidence: 0.93,
    ocrConfidence: 0.89,
    confidence: 0.91,
    frameNo: 182,
    timestamp: '00:00:07.28'
  }
]

/* ===== 交警关键点 ===== */
export const mockPoliceKeypoints = [
  { name: 'nose', x: 640, y: 128, score: 0.98 },
  { name: 'left_shoulder', x: 552, y: 234, score: 0.94 },
  { name: 'right_shoulder', x: 728, y: 236, score: 0.95 },
  { name: 'left_elbow', x: 500, y: 346, score: 0.93 },
  { name: 'right_elbow', x: 805, y: 332, score: 0.91 },
  { name: 'left_wrist', x: 460, y: 450, score: 0.90 },
  { name: 'right_wrist', x: 884, y: 260, score: 0.88 },
  { name: 'left_hip', x: 585, y: 500, score: 0.90 },
  { name: 'right_hip', x: 708, y: 502, score: 0.90 },
  { name: 'left_knee', x: 570, y: 675, score: 0.82 },
  { name: 'right_knee', x: 720, y: 678, score: 0.84 },
  { name: 'left_ankle', x: 548, y: 832, score: 0.78 },
  { name: 'right_ankle', x: 744, y: 830, score: 0.79 }
]

/* ===== 手部关键点 ===== */
export const mockHandKeypoints = [
  { name: 'wrist', x: 580, y: 690, score: 0.98 },
  { name: 'thumb_cmc', x: 520, y: 628, score: 0.95 },
  { name: 'thumb_mcp', x: 486, y: 570, score: 0.94 },
  { name: 'thumb_tip', x: 460, y: 500, score: 0.90 },
  { name: 'index_mcp', x: 585, y: 565, score: 0.96 },
  { name: 'index_pip', x: 592, y: 485, score: 0.96 },
  { name: 'index_tip', x: 600, y: 410, score: 0.95 },
  { name: 'middle_mcp', x: 636, y: 560, score: 0.95 },
  { name: 'middle_pip', x: 652, y: 470, score: 0.94 },
  { name: 'middle_tip', x: 666, y: 392, score: 0.92 },
  { name: 'ring_mcp', x: 690, y: 585, score: 0.93 },
  { name: 'ring_pip', x: 730, y: 512, score: 0.91 },
  { name: 'ring_tip', x: 760, y: 450, score: 0.90 },
  { name: 'pinky_mcp', x: 725, y: 630, score: 0.90 },
  { name: 'pinky_pip', x: 790, y: 590, score: 0.86 },
  { name: 'pinky_tip', x: 836, y: 548, score: 0.84 }
]

/* ===== 推理结果 ===== */
export const mockInference = {
  [TASK_TYPES.LICENSE_PLATE]: {
    taskType: TASK_TYPES.LICENSE_PLATE,
    latencyMs: 418,
    image: { width: 1200, height: 720 },
    detections: mockLicenseDetections,
    detectionCount: 2,
    annotatedImageUrl: sampleImages.road
  },
  [TASK_TYPES.POLICE_GESTURE]: {
    taskType: TASK_TYPES.POLICE_GESTURE,
    latencyMs: 612,
    image: { width: 1200, height: 720 },
    detections: [
      {
        objectId: 'person_001',
        objectType: 'traffic_police',
        bbox: { x1: 430, y1: 90, x2: 915, y2: 690 },
        confidence: 0.93,
        gestureCode: 'STOP',
        gestureName: '停止信号',
        keypoints: mockPoliceKeypoints
      }
    ],
    detectionCount: 1,
    annotatedImageUrl: sampleImages.police
  },
  [TASK_TYPES.OWNER_GESTURE]: {
    taskType: TASK_TYPES.OWNER_GESTURE,
    latencyMs: 238,
    image: { width: 1200, height: 720 },
    detections: [
      {
        objectId: 'hand_001',
        objectType: 'hand',
        confidence: 0.91,
        gestureCode: '003',
        gestureName: '单指画圈',
        keypoints: mockHandKeypoints
      }
    ],
    detectionCount: 1,
    annotatedImageUrl: sampleImages.cockpit
  }
}

/* ===== 置信度分布 ===== */
export const mockConfidence = {
  police: [
    { name: '停止信号', value: 93 },
    { name: '直行信号', value: 39 },
    { name: '左转弯信号', value: 24 },
    { name: '右转弯信号', value: 18 },
    { name: '变道信号', value: 15 },
    { name: '减速慢行', value: 12 },
    { name: '靠边停车', value: 10 },
    { name: '左转待转', value: 8 }
  ],
  owner: [
    { name: '单指画圈', value: 91 },
    { name: '手掌张开', value: 36 },
    { name: '左右滑动', value: 24 },
    { name: '握拳', value: 18 },
    { name: '拇指向上', value: 14 },
    { name: '挥手', value: 12 },
    { name: '拇指向下', value: 8 }
  ]
}

/* ===== 历史记录 ===== */
export const mockHistoryRecords = [
  { id: 1001, createdAt: '2026-07-08 09:18:32', taskType: 'license_plate', target: '京A12345 / 沪B8K218', status: 'completed', confidence: 0.96, duration: 418 },
  { id: 1002, createdAt: '2026-07-08 09:21:08', taskType: 'police_gesture', target: '停止信号', status: 'completed', confidence: 0.93, duration: 612 },
  { id: 1003, createdAt: '2026-07-08 09:24:41', taskType: 'owner_gesture', target: '单指画圈 → 调节音量', status: 'completed', confidence: 0.91, duration: 238 },
  { id: 1004, createdAt: '2026-07-08 09:29:13', taskType: 'license_plate', target: '浙C79D21', status: 'warning', confidence: 0.68, duration: 1240 },
  { id: 1005, createdAt: '2026-07-08 09:35:01', taskType: 'police_gesture', target: '直行信号', status: 'completed', confidence: 0.89, duration: 580 },
  { id: 1006, createdAt: '2026-07-08 09:40:22', taskType: 'owner_gesture', target: '握拳 → 确认执行', status: 'completed', confidence: 0.94, duration: 195 }
]

/* ===== 视频任务 ===== */
export const mockVideoJob = {
  jobId: 'job_video_20260708_001',
  taskType: 'license_plate',
  status: 'processing',
  progress: 63,
  processedFrames: 1820,
  totalFrames: 2880,
  sampleFps: 5,
  callbackUrl: 'http://backend:8080/internal/api/v1/algorithm/events',
  inputUrl: 'rtsp://10.126.59.120:8554/live/live1'
}

export const rtspChannels = [
  { label: 'live1 桥面', value: 'rtsp://10.126.59.120:8554/live/live1' },
  { label: 'live2 停车场出口', value: 'rtsp://10.126.59.120:8554/live/live2' },
  { label: 'live7 道路2', value: 'rtsp://10.126.59.120:8554/live/live7' },
  { label: 'live12 道路1', value: 'rtsp://10.126.59.120:8554/live/live12' }
]

/* ===== 业务流水线 ===== */
export const businessPipelines = {
  image: ['选择图片', '上传Java后端', '生成image_url', '调用算法推理', '写入历史记录', '前端渲染结果'],
  video: ['提交视频/RTSP', '创建异步Job', '算法抽帧推理', 'callback回传', 'WebSocket推送', '查询任务进度'],
  alert: ['写入JSON日志', 'Agent监听异常', 'LLM生成摘要', '保存告警事件', 'WebSocket/邮件通知']
}

/* ===== 告警数据 ===== */
export const mockAlerts = [
  {
    id: 'alert_001',
    severity: 'CRITICAL',
    title: '车牌识别连续失败率过高',
    summary: '最近1分钟车牌识别失败率达34%，疑似上传图片分辨率过低（平均320×240），建议检查输入图片质量与算法服务状态。',
    module: 'license_plate',
    status: 'open',
    occurredAt: '2026-07-08 09:30:12',
    suggestedActions: ['检查上传图片清晰度', '确认算法服务 /health 正常', '查看失败请求日志', '通知用户使用高分辨率图片']
  },
  {
    id: 'alert_002',
    severity: 'WARNING',
    title: '手势置信度持续偏低',
    summary: '车主手势模块近5分钟平均置信度为0.48，可能存在光照不足或手部遮挡，建议增强摄像头光照条件。',
    module: 'owner_gesture',
    status: 'processing',
    occurredAt: '2026-07-08 09:22:05',
    suggestedActions: ['增强摄像头光照', '降低背景干扰', '提高置信度采样窗口']
  },
  {
    id: 'alert_003',
    severity: 'INFO',
    title: 'WebSocket连接已恢复',
    summary: '告警推送通道重连成功，未读告警已同步到前端时间线。',
    module: 'websocket',
    status: 'resolved',
    occurredAt: '2026-07-08 09:16:46',
    suggestedActions: ['无需处理']
  },
  {
    id: 'alert_004',
    severity: 'CRITICAL',
    title: '算法模型服务响应超时',
    summary: 'Python FastAPI算法服务在过去2分钟内3次请求超时（>30s），可能是GPU资源不足或模型加载异常。',
    module: 'algorithm',
    status: 'open',
    occurredAt: '2026-07-08 09:38:55',
    suggestedActions: ['检查GPU/CPU使用率', '重启算法微服务', '降低并发请求数', '检查模型是否正常加载']
  }
]

export const mockAlertStats = {
  totalToday: 18,
  critical: 3,
  warning: 9,
  info: 6,
  trend: [3, 5, 4, 7, 6, 8, 18],
  severity: [
    { name: '提示', value: 6 },
    { name: '警告', value: 9 },
    { name: '严重', value: 3 }
  ],
  modules: [
    { name: '车牌识别', value: 7 },
    { name: '交警手势', value: 3 },
    { name: '车主手势', value: 5 },
    { name: '系统运行', value: 3 }
  ]
}

/* ===== 车辆状态（Dashboard用） ===== */
export const mockVehicleState = {
  speed: 42,
  gear: 'D',
  range: 286,
  tirePressure: [
    { name: '左前', value: 2.4, status: 'normal' },
    { name: '右前', value: 2.4, status: 'normal' },
    { name: '左后', value: 2.3, status: 'normal' },
    { name: '右后', value: 2.1, status: 'warning' }
  ],
  network: '5G',
  climate: { temperature: 24, mode: 'Auto', fan: 3 },
  audio: { volume: 42, track: 'City Drive' },
  phone: { status: '待机', caller: '无来电' },
  policeDetection: {
    detected: true,
    confidence: 0.87,
    action: '建议进入交警手势识别'
  }
}

/* ===== 系统健康状态 ===== */
export const mockSystemHealth = [
  { name: '模型服务', status: 'normal', value: '正常', detail: 'FastAPI /health OK · 延迟 42ms' },
  { name: '后端服务', status: 'normal', value: '在线', detail: 'Spring Boot :8080 · 运行中' },
  { name: 'WebSocket', status: 'normal', value: '已连接', detail: '告警推送通道正常' },
  { name: 'Agent监控', status: 'warning', value: '观察中', detail: '低置信度规则触发1次' }
]
