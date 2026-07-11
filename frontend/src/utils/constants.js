// 任务类型
export const TASK_TYPES = {
  LICENSE_PLATE: 'license_plate',
  POLICE_GESTURE: 'police_gesture',
  OWNER_GESTURE: 'owner_gesture'
}

// 交警手势编码映射
export const POLICE_GESTURE_MAP = {
  STOP: '停止信号',
  GO_STRAIGHT: '直行信号',
  LEFT_TURN: '左转弯信号',
  LEFT_WAIT: '左转弯待转信号',
  RIGHT_TURN: '右转弯信号',
  LANE_CHANGE: '变道信号',
  SLOW_DOWN: '减速慢行信号',
  PULL_OVER: '靠边停车信号'
}

// 车主手势编码映射
export const OWNER_GESTURE_MAP = {}

export const OWNER_GESTURE_ACTIONS = [
  { actionType: 'NONE', actionLabel: '不触发控制' },
  { actionType: 'WAKE_SYSTEM', actionLabel: '启动/唤醒系统' },
  { actionType: 'CONFIRM', actionLabel: '确认当前操作' },
  { actionType: 'VOLUME_UP', actionLabel: '音量增加' },
  { actionType: 'VOLUME_DOWN', actionLabel: '音量降低' },
  { actionType: 'NEXT_MEDIA', actionLabel: '切换下一首' },
  { actionType: 'CLIMATE_UP', actionLabel: '空调升温' },
  { actionType: 'CLIMATE_DOWN', actionLabel: '空调降温' },
  { actionType: 'ANSWER_CALL', actionLabel: '接听电话' },
  { actionType: 'HANG_UP', actionLabel: '挂断电话' },
  { actionType: 'OPEN_NAVIGATION', actionLabel: '打开导航' },
  { actionType: 'RETURN_HOME', actionLabel: '返回驾驶主页' }
]

// 告警级别
export const ALERT_LEVELS = {
  INFO: { label: '提示', color: '#409eff' },
  WARNING: { label: '警告', color: '#e6a23c' },
  CRITICAL: { label: '严重', color: '#f56c6c' }
}

// 任务状态
export const JOB_STATUS = {
  QUEUED: 'queued',
  PROCESSING: 'processing',
  COMPLETED: 'completed',
  FAILED: 'failed',
  CANCELLED: 'cancelled'
}
