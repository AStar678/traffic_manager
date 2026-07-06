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
export const OWNER_GESTURE_MAP = {
  '001': { name: '手掌张开', action: '启动/唤醒' },
  '002': { name: '握拳', action: '确认/执行' },
  '003': { name: '单指画圈', action: '调节音量' },
  '004': { name: '左右滑动', action: '切换功能' },
  '005': { name: '拇指向上', action: '接听电话' },
  '006': { name: '拇指向下', action: '挂断电话' },
  '007': { name: '挥手', action: '返回主页' }
}

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
