const DEFAULT_LANGUAGE = 'zh-CN'
const SPEECH_ANNOUNCEMENTS_STORAGE_KEY = 'visiondrive.speechAnnouncementsEnabled'

const OWNER_ACTION_ANNOUNCEMENTS = Object.freeze({
  '启动/唤醒系统': '已唤醒系统',
  '确认当前操作': '已确认',
  '音量增加': '已调高音量',
  '音量降低': '已调低音量',
  '切换下一首': '已切换下一首',
  '空调升温': '已调高空调温度',
  '空调降温': '已调低空调温度',
  '接听电话': '已接听电话',
  '挂断电话': '已挂断电话',
  '打开导航': '已打开导航',
  '返回驾驶主页': '已返回驾驶主页',
  '车辆状态已更新': '已更新车辆状态'
})

const POLICE_GESTURE_ANNOUNCEMENTS = Object.freeze({
  STOP: '交警指挥停车',
  '停止信号': '交警指挥停车',
  GO_STRAIGHT: '交警指挥直行',
  '直行信号': '交警指挥直行',
  LEFT_TURN: '交警指挥左转',
  '左转弯信号': '交警指挥左转',
  LEFT_WAIT: '交警指挥进入左转待转区',
  '左转弯待转信号': '交警指挥进入左转待转区',
  RIGHT_TURN: '交警指挥右转',
  '右转弯信号': '交警指挥右转',
  LANE_CHANGE: '交警指挥变道',
  '变道信号': '交警指挥变道',
  SLOW_DOWN: '交警指挥减速',
  '减速慢行信号': '交警指挥减速',
  PULL_OVER: '交警指挥靠边停车',
  '靠边停车信号': '交警指挥靠边停车'
})

let activeUtterance = null

export function areSpeechAnnouncementsEnabled() {
  if (typeof window === 'undefined') return true
  try {
    return window.localStorage.getItem(SPEECH_ANNOUNCEMENTS_STORAGE_KEY) !== 'false'
  } catch {
    return true
  }
}

export function setSpeechAnnouncementsEnabled(enabled) {
  const nextEnabled = Boolean(enabled)
  if (typeof window === 'undefined') return nextEnabled
  try {
    window.localStorage.setItem(SPEECH_ANNOUNCEMENTS_STORAGE_KEY, String(nextEnabled))
  } catch {
    // Storage may be unavailable in privacy-restricted browser contexts.
  }
  if (!nextEnabled) {
    window.speechSynthesis?.cancel()
    activeUtterance = null
  }
  return nextEnabled
}

function browserSpeech() {
  if (typeof window === 'undefined' || typeof window.SpeechSynthesisUtterance !== 'function') {
    return null
  }
  return window.speechSynthesis || null
}

function chineseVoice(speech) {
  const voices = speech.getVoices?.() || []
  return voices.find(voice => voice.lang?.toLowerCase() === 'zh-cn')
    || voices.find(voice => voice.lang?.toLowerCase().startsWith('zh'))
    || null
}

export function speakAnnouncement(message) {
  const text = String(message || '').trim()
  const speech = browserSpeech()
  if (!text || !speech || !areSpeechAnnouncementsEnabled()) return false

  speech.cancel()
  const utterance = new window.SpeechSynthesisUtterance(text)
  utterance.lang = DEFAULT_LANGUAGE
  utterance.rate = 0.95
  utterance.pitch = 1
  utterance.volume = 1
  utterance.voice = chineseVoice(speech)
  utterance.onend = utterance.onerror = () => {
    if (activeUtterance === utterance) activeUtterance = null
  }

  activeUtterance = utterance
  speech.speak(utterance)
  return true
}

export function announceOwnerGestureAction(actionLabel) {
  const action = String(actionLabel || '').trim()
  if (!action) return false
  return speakAnnouncement(OWNER_ACTION_ANNOUNCEMENTS[action] || `已${action.replaceAll('/', '或')}`)
}

export function announcePoliceGesture(gestureName) {
  const gesture = String(gestureName || '').trim()
  if (!gesture) return false
  const fallbackCommand = gesture
    .replace(/信号$/, '')
    .replace('左转弯', '左转')
    .replace('右转弯', '右转')
    .replace('减速慢行', '减速')
  return speakAnnouncement(POLICE_GESTURE_ANNOUNCEMENTS[gesture] || `交警指挥${fallbackCommand}`)
}
