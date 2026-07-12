<template>
  <div class="dashboard">
    <!-- 核心驾驶信息：速度 + 档位 -->
    <div class="hero-row">
      <!-- 速度表区域 -->
      <div class="speedo-section">
        <div class="speed-ring">
          <svg viewBox="0 0 200 200" class="speed-svg">
            <circle cx="100" cy="100" r="88" fill="none" stroke="rgba(255,255,255,0.04)" stroke-width="10" />
            <circle
              cx="100" cy="100" r="88"
              fill="none"
              stroke="url(#speedGrad)"
              stroke-width="10"
              stroke-linecap="round"
              :stroke-dasharray="`${(vehicle.speed / 120) * 553} 553`"
              stroke-dashoffset="0"
              transform="rotate(-90 100 100)"
              class="speed-arc"
            />
            <defs>
              <linearGradient id="speedGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="#00b4d8" />
                <stop offset="100%" stop-color="#00e5ff" />
              </linearGradient>
            </defs>
          </svg>
          <div class="speed-value">
            <strong>{{ vehicle.speed }}</strong>
            <span>km/h</span>
          </div>
        </div>
        <!-- 档位 -->
        <div class="gear-badge">
          <span>档位</span>
          <strong>{{ vehicle.gear }}</strong>
        </div>
      </div>

      <!-- 中央：驾驶输入 + 本机手势摄像头 -->
      <div class="camera-duo">
        <div class="camera-feed card">
          <div class="camera-inner">
            <video
              v-show="cameraVideoReady"
              ref="cameraVideoRef"
              class="camera-stream"
              autoplay
              muted
              playsinline
              @loadeddata="markCameraVideoReady"
              @playing="markCameraVideoReady"
            ></video>
            <img
              v-if="!cameraVideoReady && cameraDisplayUrl"
              class="camera-stream"
              :src="cameraDisplayUrl"
              alt="前置摄像头降级预览"
            >
            <div v-if="!cameraVideoReady && !cameraDisplayUrl" class="camera-placeholder">
              <el-icon :size="42"><Camera /></el-icon>
              <span>{{ cameraError || '等待摄像头服务' }}</span>
            </div>
            <div class="camera-overlay-info">
              <span class="camera-label">{{ selectedCameraSource?.name || '前置摄像头' }}</span>
              <span class="camera-live">● {{ cameraStatusText }}</span>
            </div>
            <div class="scan-line-animated"></div>
            <!-- 检测到车牌时显示浮层 -->
            <div class="detection-hint" v-if="vehicle.policeDetection.detected">
              <span class="status-dot warning"></span>
              检测到交警 · 置信度 {{ Math.round(vehicle.policeDetection.confidence * 100) }}%
              <button class="action-pill" @click="$router.push('/police-gesture')">查看</button>
            </div>
          </div>
        </div>

        <div class="camera-feed card gesture-camera-feed" :class="{ active: gestureControlActive }">
          <div class="camera-inner gesture-camera-inner">
            <video
              v-show="gestureCameraReady"
              ref="gestureVideoRef"
              class="camera-stream gesture-local-video"
              autoplay
              muted
              playsinline
              @loadeddata="markGestureCameraReady"
              @playing="markGestureCameraReady"
            ></video>
            <canvas
              v-show="gestureCameraReady"
              ref="gestureOverlayRef"
              class="gesture-keypoint-overlay"
            ></canvas>
            <div v-if="!gestureCameraReady" class="camera-placeholder gesture-placeholder">
              <el-icon :size="42"><Pointer /></el-icon>
              <span>{{ gestureCameraError || '打开手势控车后启用本机摄像头' }}</span>
            </div>
            <div class="camera-overlay-info">
              <span class="camera-label">本机手势摄像头</span>
              <span class="camera-live" :class="{ online: gestureControlActive }">● {{ gestureCameraStatusText }}</span>
            </div>
            <div v-if="gestureCameraReady" class="gesture-camera-readout">
              <div>
                <span>匹配</span>
                <strong>{{ gestureMatchLabel }}</strong>
              </div>
              <div>
                <span>相似度</span>
                <strong>{{ gestureScoreLabel }}</strong>
              </div>
              <div>
                <span>状态</span>
                <strong>{{ gestureTriggerLabel }}</strong>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧：车辆健康状态卡片 -->
      <div class="health-stack">
        <div class="card health-item" v-for="item in health.slice(0, 3)" :key="item.name">
          <div class="health-head">
            <span>{{ item.name }}</span>
            <span class="status-dot" :class="item.status === 'normal' ? 'online' : 'warning'"></span>
          </div>
          <strong>{{ item.value }}</strong>
          <p>{{ item.detail }}</p>
        </div>
      </div>
    </div>

    <!-- 第二行：车辆状态 + 快捷操作 -->
    <div class="secondary-row">
      <!-- 胎压 + 空调 -->
      <div class="card status-grid" :class="{ active: lastGestureControl?.actionType?.startsWith('CLIMATE') }">
        <h3 class="card-title">车辆状态</h3>
        <div class="status-items">
          <div
            v-for="tire in vehicle.tirePressure"
            :key="tire.name"
            class="status-item"
            :class="{ alert: tire.status === 'warning' }"
          >
            <el-icon><Location /></el-icon>
            <div>
              <strong>{{ tire.value }} <small>bar</small></strong>
              <span>{{ tire.name }}胎压</span>
            </div>
          </div>
        </div>
        <div class="gradient-divider"></div>
        <div class="climate-row">
          <div class="climate-icon">
            <el-icon :size="28"><Sunny /></el-icon>
          </div>
          <div class="climate-info">
            <strong>{{ vehicle.climate.temperature }}°C</strong>
            <span>空调 · {{ vehicle.climate.mode }}</span>
          </div>
        </div>
      </div>

      <!-- 多媒体卡片 -->
      <div class="card media-card" :class="{ active: ['VOLUME_UP', 'VOLUME_DOWN', 'NEXT_MEDIA'].includes(lastGestureControl?.actionType) }">
        <h3 class="card-title">正在播放</h3>
        <div class="media-art">
          <el-icon :size="40"><Headset /></el-icon>
        </div>
        <strong class="media-track">{{ vehicle.audio.track }}</strong>
        <span class="media-meta">音量 {{ vehicle.audio.volume }}%</span>
        <div class="media-controls">
          <el-button circle><el-icon><VideoPlay /></el-icon></el-button>
          <el-button circle><el-icon><ArrowRight /></el-icon></el-button>
        </div>
      </div>

      <!-- 电话状态 -->
      <div class="card phone-card" :class="{ active: ['ANSWER_CALL', 'HANG_UP'].includes(lastGestureControl?.actionType) }">
        <h3 class="card-title">电话</h3>
        <div class="phone-status">
          <el-icon :size="36"><Phone /></el-icon>
          <strong>{{ vehicle.phone.status }}</strong>
          <span>{{ vehicle.phone.caller }}</span>
        </div>
      </div>

      <div class="card gesture-control-card" :class="{ active: gestureControlActive || lastGestureControl }">
        <h3 class="card-title">手势控制</h3>
        <div v-if="lastGestureControl" class="gesture-control-state">
          <span class="gesture-badge">{{ lastGestureControl.gestureName }}</span>
          <strong>{{ lastGestureControl.actionLabel }}</strong>
          <small>{{ lastControlTime }} · 置信度 {{ Math.round(lastGestureControl.confidence * 100) }}%</small>
        </div>
        <div v-else class="gesture-control-empty">
          <el-icon :size="32"><Pointer /></el-icon>
          <span>{{ gestureControlStatus }}</span>
        </div>
        <button
          class="gesture-open-button"
          type="button"
          :class="{ running: gestureControlActive }"
          :disabled="gestureControlLoading"
          @click="toggleGestureControl"
        >
          {{ gestureControlButtonText }}
        </button>
      </div>

      <!-- 告警快捷入口 -->
      <div class="card alert-card">
        <h3 class="card-title">系统告警</h3>
        <div class="alert-mini" v-for="alert in recentAlerts" :key="alert.id" @click="$router.push('/alert-dashboard')">
          <span class="status-dot" :class="alert.severity === 'CRITICAL' ? 'offline' : 'warning'"></span>
          <div>
            <strong>{{ alert.title }}</strong>
            <span>{{ alert.occurredAt }}</span>
          </div>
        </div>
        <button class="action-link" @click="$router.push('/alert-dashboard')">查看全部 →</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { DrawingUtils, FilesetResolver, GestureRecognizer } from '@/vendor/tasks-vision/vision_bundle.mjs'
import { executeOwnerGestureControl, getOwnerGestureControlSettings, getOwnerGestureData } from '@/api/ownerGestures'
import { mockSystemHealth, mockAlerts } from '@/utils/mockData'
import { useAlertStore } from '@/stores/alert'
import { useCameraSource } from '@/composables/useCameraSource'
import { useVehicleStore } from '@/stores/vehicle'
import {
  OWNER_GESTURE_RECOGNITION_CONFIG,
  extractFeatureVector,
  sequenceMotion
} from '@/utils/ownerGesturePrototype'

const MODEL_PATH = '/models/gesture_recognizer.task'
const GESTURE_FRAME_INTERVAL_MS = 33
const BUILT_IN_GESTURE_THRESHOLD = 0.7
const BUILT_IN_GESTURE_FALLBACK_HOLD_MS = 1200
const BUILT_IN_GESTURE_COOLDOWN_MS = 1500
const BUILT_IN_DISPLAY_GRACE_MS = 500
const BUILT_IN_GESTURE_LABELS = {
  Closed_Fist: '握拳',
  Open_Palm: '手掌张开',
  Pointing_Up: '单指向上',
  Thumb_Down: '拇指向下',
  Thumb_Up: '拇指向上',
  Victory: '胜利手势',
  ILoveYou: 'I Love You'
}

const alertStore = useAlertStore()
const vehicleStore = useVehicleStore()
const vehicle = vehicleStore.vehicle
const health = mockSystemHealth
const {
  selectedCameraSource,
  cameraStatus,
  cameraError,
  cameraDisplayUrl,
  cameraVideoRef,
  cameraVideoReady,
  markCameraVideoReady,
  refreshCameraPreview
} = useCameraSource()

const gestureControlActive = ref(false)
const gestureControlLoading = ref(false)
const gestureControlStatus = ref('等待手势控制')
const gestureVideoRef = ref(null)
const gestureOverlayRef = ref(null)
const gestureCameraReady = ref(false)
const gestureCameraError = ref('')
const gestureMatchLabel = ref('未录入')
const gestureScoreLabel = ref('--')
const gestureTriggerLabel = ref('等待')

let gestureRecognizer
let gestureDrawingUtils
let gestureOverlayContext
let gestureMediaStream
let gestureSocket
let gestureFrameId
let lastGestureVideoTime = -1
let lastGestureFrameAt = 0
let gestureRunId = 0
let lastBuiltInGestureCode = ''
let lastBuiltInGestureAt = 0
let lastBuiltInMatchAt = 0
let builtInGestureStableCode = ''
let builtInGestureStableSince = 0
let builtInGestureVectors = []
let lastGestureRecognitionDisplay
let gestureControlBindings = new Map()
let gestureControlConfig = {}
let gestureSocketReconnectTimer

const cameraStatusText = computed(() => {
  const labels = { idle: '待机', loading: '连接中', ready: 'LIVE', empty: '无源', offline: '离线' }
  return labels[cameraStatus.value] || cameraStatus.value
})
const lastGestureControl = computed(() => vehicleStore.lastGestureControl)
const gestureControlButtonText = computed(() => {
  if (gestureControlLoading.value) return '启动中'
  return gestureControlActive.value ? '关闭手势控车' : '打开手势控车'
})
const gestureCameraStatusText = computed(() => {
  if (gestureControlLoading.value) return '启动中'
  if (gestureControlActive.value && gestureSocket?.readyState === WebSocket.OPEN) return '识别中'
  if (gestureControlActive.value) return '本机摄像头'
  if (gestureCameraError.value) return '离线'
  return '待机'
})
const lastControlTime = computed(() => {
  const timestamp = lastGestureControl.value?.triggeredAt
  if (!timestamp) return '--'
  return new Date(timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
})

onMounted(() => {
  alertStore.fetchAlerts()
  refreshCameraPreview()
})

onBeforeUnmount(() => {
  stopGestureControl()
})

const recentAlerts = computed(() => mockAlerts.slice(0, 2))

async function toggleGestureControl() {
  if (gestureControlActive.value || gestureControlLoading.value) {
    stopGestureControl()
    return
  }
  await startGestureControl()
}

async function startGestureControl() {
  const runId = ++gestureRunId
  gestureControlLoading.value = true
  gestureControlStatus.value = '正在启动识别'
  gestureTriggerLabel.value = '启动中'
  gestureCameraError.value = ''

  try {
    await refreshGestureControlBindings()
    await ensureGestureRecognizer()
    await startGestureCamera()
    await waitForGestureVideo()
    if (runId !== gestureRunId) return
    gestureControlActive.value = true
    gestureControlLoading.value = false
    gestureControlStatus.value = '识别服务连接中'
    gestureTriggerLabel.value = '识别服务连接中'
    connectGestureSocket()
    recognizeGestureLoop()
  } catch (error) {
    console.error(error)
    gestureControlStatus.value = '手势控车启动失败'
    gestureTriggerLabel.value = '启动失败'
    gestureControlLoading.value = false
    stopGestureControl({ keepStatus: true })
  }
}

function stopGestureControl(options = {}) {
  gestureRunId += 1
  gestureControlActive.value = false
  gestureControlLoading.value = false
  if (gestureFrameId) {
    cancelAnimationFrame(gestureFrameId)
  }
  gestureFrameId = undefined
  lastGestureVideoTime = -1
  lastGestureFrameAt = 0
  lastBuiltInGestureCode = ''
  lastBuiltInGestureAt = 0
  lastBuiltInMatchAt = 0
  builtInGestureStableCode = ''
  builtInGestureStableSince = 0
  builtInGestureVectors = []
  if (gestureSocket) {
    gestureSocket.onopen = null
    gestureSocket.onmessage = null
    gestureSocket.onclose = null
    gestureSocket.onerror = null
    gestureSocket.close()
  }
  gestureSocket = undefined
  window.clearTimeout(gestureSocketReconnectTimer)
  gestureSocketReconnectTimer = undefined
  stopGestureCamera()
  if (!options.keepStatus) {
    gestureControlStatus.value = '等待手势控制'
    gestureTriggerLabel.value = '等待'
  }
}

async function refreshGestureControlBindings() {
  try {
    const data = getOwnerGestureData(await getOwnerGestureControlSettings())
    gestureControlConfig = data?.config || {}
    gestureControlBindings = new Map(
      (data?.settings || []).map(item => [String(item.gestureCode), item])
    )
  } catch (error) {
    console.error(error)
    gestureControlConfig = {}
    gestureControlBindings = new Map()
  }
}

async function ensureGestureRecognizer() {
  if (gestureRecognizer) return gestureRecognizer
  const vision = await FilesetResolver.forVisionTasks('/wasm')
  try {
    gestureRecognizer = await GestureRecognizer.createFromOptions(vision, {
      baseOptions: {
        modelAssetPath: MODEL_PATH,
        delegate: 'GPU'
      },
      runningMode: 'VIDEO',
      numHands: 1
    })
  } catch (error) {
    console.warn('GPU delegate unavailable, falling back to CPU.', error)
    gestureRecognizer = await GestureRecognizer.createFromOptions(vision, {
      baseOptions: {
        modelAssetPath: MODEL_PATH,
        delegate: 'CPU'
      },
      runningMode: 'VIDEO',
      numHands: 1
    })
  }
  return gestureRecognizer
}

async function startGestureCamera() {
  await nextTick()
  if (gestureMediaStream) {
    await attachGestureCameraStream()
    return true
  }

  if (!navigator.mediaDevices?.getUserMedia) {
    throw new Error('gesture_camera_unsupported')
  }

  try {
    gestureMediaStream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'user' },
      audio: false
    })
    await attachGestureCameraStream()
    gestureCameraError.value = ''
    return true
  } catch (error) {
    gestureCameraError.value = '本机摄像头启动失败，请允许浏览器摄像头权限'
    throw error
  }
}

async function attachGestureCameraStream() {
  const video = gestureVideoRef.value
  if (!video || !gestureMediaStream) return
  if (video.srcObject !== gestureMediaStream) {
    video.srcObject = gestureMediaStream
  }
  video.muted = true
  video.playsInline = true
  video.autoplay = true
  await video.play()
  markGestureCameraReady()
}

function stopGestureCamera() {
  gestureMediaStream?.getTracks().forEach(track => track.stop())
  gestureMediaStream = undefined
  if (gestureVideoRef.value) {
    gestureVideoRef.value.srcObject = null
  }
  clearGestureOverlay()
  gestureCameraReady.value = false
}

function markGestureCameraReady() {
  gestureCameraReady.value = true
  gestureCameraError.value = ''
  resizeGestureOverlay()
}

function waitForGestureVideo() {
  return new Promise((resolve, reject) => {
    const startedAt = performance.now()
    function check() {
      const video = gestureVideoRef.value
      if (video && video.readyState >= 2 && video.videoWidth && video.videoHeight) {
        resizeGestureOverlay()
        resolve(video)
        return
      }
      if (performance.now() - startedAt > 5000) {
        reject(new Error('camera_video_not_ready'))
        return
      }
      requestAnimationFrame(check)
    }
    check()
  })
}

function connectGestureSocket() {
  if (!gestureControlActive.value) return
  if (gestureSocket && [WebSocket.CONNECTING, WebSocket.OPEN].includes(gestureSocket.readyState)) return
  window.clearTimeout(gestureSocketReconnectTimer)
  gestureSocketReconnectTimer = undefined

  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
  const socket = new WebSocket(`${protocol}//${location.host}/api/recognition/stream`)
  gestureSocket = socket

  socket.onopen = () => {
    if (socket !== gestureSocket) return
    gestureControlLoading.value = false
    gestureControlStatus.value = '识别中'
    gestureTriggerLabel.value = '识别中'
  }

  socket.onmessage = event => {
    if (socket !== gestureSocket) return
    try {
      applyGestureRecognitionState(JSON.parse(event.data))
    } catch (error) {
      console.error(error)
    }
  }

  socket.onerror = () => {
    if (socket !== gestureSocket) return
    gestureControlStatus.value = '识别服务连接失败'
    gestureTriggerLabel.value = '识别服务连接失败'
    gestureControlLoading.value = false
    try {
      socket.close()
    } catch (error) {
      console.error(error)
    }
  }

  socket.onclose = () => {
    if (socket !== gestureSocket) return
    gestureSocket = undefined
    if (!gestureControlActive.value) return
    gestureControlLoading.value = false
    gestureControlStatus.value = '识别服务重连中'
    gestureTriggerLabel.value = '识别服务重连中'
    scheduleGestureSocketReconnect()
  }
}

function scheduleGestureSocketReconnect() {
  if (!gestureControlActive.value || gestureSocketReconnectTimer) return
  gestureSocketReconnectTimer = window.setTimeout(() => {
    gestureSocketReconnectTimer = undefined
    connectGestureSocket()
  }, 1000)
}

function recognizeGestureLoop() {
  if (!gestureControlActive.value || !gestureRecognizer) {
    return
  }

  try {
    const now = performance.now()
    if (now - lastGestureFrameAt < GESTURE_FRAME_INTERVAL_MS) {
      return
    }
    lastGestureFrameAt = now

    const video = gestureVideoRef.value
    if (video?.readyState >= 2 && video.currentTime !== lastGestureVideoTime) {
      lastGestureVideoTime = video.currentTime
      resizeGestureOverlay()
      const result = gestureRecognizer.recognizeForVideo(video, now)
      drawGestureResult(result)
      const landmarks = result.landmarks?.[0]
      if (landmarks) {
        const vector = extractFeatureVector(landmarks, result.worldLandmarks?.[0])
        applyBuiltInGestureRecognition(result.gestures?.[0]?.[0], vector)
        if (gestureSocket?.readyState === WebSocket.OPEN) {
          gestureSocket.send(JSON.stringify({ type: 'frame', vector }))
        } else if (!lastGestureControl.value) {
          gestureControlStatus.value = '识别服务连接中'
          gestureTriggerLabel.value = '识别服务连接中'
        }
      } else {
        resetBuiltInGestureState()
        restoreLastGestureRecognitionDisplay()
        gestureTriggerLabel.value = '未检测到手'
        if (!lastGestureControl.value) {
          gestureControlStatus.value = '未检测到手'
        }
      }
    }
  } catch (error) {
    console.error('Dashboard gesture recognition frame failed.', error)
    gestureControlStatus.value = '识别帧异常，正在恢复'
    gestureTriggerLabel.value = '识别帧异常，正在恢复'
  } finally {
    if (gestureControlActive.value && gestureRecognizer) {
      gestureFrameId = requestAnimationFrame(recognizeGestureLoop)
    }
  }
}

function applyBuiltInGestureRecognition(category, vector) {
  const gestureCode = category?.categoryName
  const score = Number(category?.score || 0)
  const now = performance.now()
  if (!gestureCode || gestureCode === 'None' || score < BUILT_IN_GESTURE_THRESHOLD) {
    resetBuiltInGestureState()
    return
  }

  const config = builtInGestureConfig()
  const gestureName = BUILT_IN_GESTURE_LABELS[gestureCode] || gestureCode
  const recognitionHoldMs = builtInStaticRecognitionHoldMs(config)
  const triggerHoldMs = builtInGestureHoldMs(gestureCode)
  const motion = trackBuiltInGestureMotion(gestureCode, vector, config)
  lastBuiltInMatchAt = now

  if (motion > builtInStaticMotionLimit(config)) {
    builtInGestureStableSince = 0
    gestureMatchLabel.value = '静态确认中'
    gestureScoreLabel.value = '--'
    gestureTriggerLabel.value = '请保持静止'
    gestureControlStatus.value = '请保持静止'
    return
  }

  if (!builtInGestureStableSince) {
    builtInGestureStableSince = now
  }
  const stableElapsed = now - builtInGestureStableSince
  if (stableElapsed < recognitionHoldMs) {
    const holdLabel = builtInGestureHoldLabel(recognitionHoldMs - stableElapsed)
    gestureMatchLabel.value = '静态确认中'
    gestureScoreLabel.value = '--'
    gestureTriggerLabel.value = holdLabel
    gestureControlStatus.value = holdLabel
    return
  }

  lastBuiltInMatchAt = now
  rememberGestureRecognitionDisplay(gestureName, formatGestureScore(score))

  if (gestureCode === lastBuiltInGestureCode && now - lastBuiltInGestureAt < BUILT_IN_GESTURE_COOLDOWN_MS) {
    return
  }

  const binding = gestureControlBindings.get(String(gestureCode))
  if (!binding?.enabled || binding.actionType === 'NONE') {
    gestureTriggerLabel.value = '已识别，未关联功能'
    gestureControlStatus.value = '已识别，未关联功能'
    return
  }

  if (stableElapsed < triggerHoldMs) {
    const stableLabel = `稳定中 ${formatHoldSeconds(triggerHoldMs - stableElapsed)}s`
    gestureTriggerLabel.value = stableLabel
    gestureControlStatus.value = stableLabel
    return
  }

  lastBuiltInGestureCode = gestureCode
  lastBuiltInGestureAt = now
  void executeDashboardGestureControl({
    gestureCode,
    name: gestureName,
    score
  })
}

function trackBuiltInGestureMotion(gestureCode, vector, config) {
  if (gestureCode !== builtInGestureStableCode) {
    builtInGestureStableCode = gestureCode
    builtInGestureStableSince = 0
    builtInGestureVectors = []
  }
  builtInGestureVectors.push(vector)
  const sampleTarget = positiveMs(config.sampleTarget, OWNER_GESTURE_RECOGNITION_CONFIG.sampleTarget)
  if (builtInGestureVectors.length > sampleTarget) {
    builtInGestureVectors = builtInGestureVectors.slice(-sampleTarget)
  }
  return sequenceMotion(builtInGestureVectors, config)
}

function resetBuiltInGestureState() {
  lastBuiltInMatchAt = 0
  builtInGestureStableCode = ''
  builtInGestureStableSince = 0
  builtInGestureVectors = []
}

function builtInGestureHoldMs(gestureCode) {
  const setting = gestureControlBindings.get(String(gestureCode))
  return positiveMs(
    setting?.holdMs,
    positiveMs(gestureControlConfig?.defaultHoldMs, BUILT_IN_GESTURE_FALLBACK_HOLD_MS)
  )
}

function builtInStaticRecognitionHoldMs(config) {
  return positiveMs(config.staticRecognitionHoldMs, OWNER_GESTURE_RECOGNITION_CONFIG.staticRecognitionHoldMs)
}

function builtInStaticMotionLimit(config) {
  return positiveMs(config.staticMotionHardLimit, positiveMs(config.staticStillMotionLimit, OWNER_GESTURE_RECOGNITION_CONFIG.staticStillMotionLimit))
}

function builtInGestureConfig() {
  return { ...OWNER_GESTURE_RECOGNITION_CONFIG, ...(gestureControlConfig || {}) }
}

function builtInGestureHoldLabel(remainingMs) {
  return `静态保持 ${formatHoldSeconds(remainingMs)}s`
}

function formatHoldSeconds(ms) {
  return (Math.ceil(Math.max(ms, 0) / 100) / 10).toFixed(1).replace(/\.0$/, '')
}

function positiveMs(value, fallback) {
  const numeric = Number(value)
  return Number.isFinite(numeric) && numeric > 0 ? numeric : fallback
}

function drawGestureResult(result) {
  const canvas = gestureOverlayRef.value
  if (!canvas) return
  if (!gestureOverlayContext) {
    gestureOverlayContext = canvas.getContext('2d')
    gestureDrawingUtils = new DrawingUtils(gestureOverlayContext)
  }
  clearGestureOverlay()
  const landmarks = result.landmarks?.[0]
  if (!landmarks) return

  gestureDrawingUtils.drawConnectors(landmarks, GestureRecognizer.HAND_CONNECTIONS, {
    color: '#00b4d8',
    lineWidth: 3
  })
  gestureDrawingUtils.drawLandmarks(landmarks, {
    color: '#ffab00',
    fillColor: '#eef2f7',
    lineWidth: 1,
    radius: 4
  })
}

function resizeGestureOverlay() {
  const video = gestureVideoRef.value
  const canvas = gestureOverlayRef.value
  if (!video || !canvas || !video.videoWidth || !video.videoHeight) return
  if (canvas.width !== video.videoWidth || canvas.height !== video.videoHeight) {
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    gestureOverlayContext = canvas.getContext('2d')
    gestureDrawingUtils = new DrawingUtils(gestureOverlayContext)
  }
}

function clearGestureOverlay() {
  const canvas = gestureOverlayRef.value
  if (!canvas) return
  const context = gestureOverlayContext || canvas.getContext('2d')
  context?.clearRect(0, 0, canvas.width, canvas.height)
}

function applyGestureRecognitionState(state) {
  const recognition = state?.recognition
  if (!recognition) return
  const shouldKeepBuiltInDisplay =
    !recognition.accepted &&
    lastBuiltInMatchAt &&
    performance.now() - lastBuiltInMatchAt < BUILT_IN_DISPLAY_GRACE_MS

  const scoreText =
    recognition.score === null || recognition.score === undefined
      ? recognition.motionLabel || '--'
      : formatGestureScore(recognition.score)
  const recognized = recognition.accepted && rememberGestureRecognitionDisplay(recognition.name, scoreText)

  if (!shouldKeepBuiltInDisplay) {
    if (!recognized) {
      restoreLastGestureRecognitionDisplay()
    }
    gestureTriggerLabel.value = recognition.triggerState || '识别中'
  }

  if (!recognition.accepted) {
    if (!lastGestureControl.value && !shouldKeepBuiltInDisplay) {
      gestureControlStatus.value = recognition.triggerState || '识别中'
    }
    return
  }

  gestureControlStatus.value = recognition.triggerState || recognition.name || '识别中'
  if (recognition.triggered) {
    void executeDashboardGestureControl(recognition)
  }
}

async function executeDashboardGestureControl(recognition) {
  try {
    const control = getOwnerGestureData(await executeOwnerGestureControl({
      gestureCode: recognition.gestureCode || recognition.id || recognition.name,
      gestureName: recognition.name,
      confidence: recognition.score
    }))

    if (!control?.enabled) {
      gestureControlStatus.value = '已识别，未关联功能'
      gestureTriggerLabel.value = '已识别，未关联功能'
      return
    }

    vehicleStore.applyGestureControl(control)
    gestureControlStatus.value = control.actionLabel || '车辆状态已更新'
    gestureTriggerLabel.value = `已触发：${control.actionLabel || '车辆状态已更新'}`
  } catch (error) {
    console.error(error)
    gestureControlStatus.value = '控制执行失败'
    gestureTriggerLabel.value = '控制执行失败'
  }
}

function formatGestureScore(score) {
  const numericScore = Number(score)
  return Number.isFinite(numericScore) ? numericScore.toFixed(3) : '--'
}

function rememberGestureRecognitionDisplay(name, scoreText) {
  const gestureName = String(name || '').trim()
  const normalizedName = gestureName.toLowerCase()
  if (!gestureName || ['unknown', 'none', '未识别', '未录入'].includes(normalizedName)) {
    return false
  }

  lastGestureRecognitionDisplay = {
    name: gestureName,
    scoreText: scoreText || '--'
  }
  gestureMatchLabel.value = lastGestureRecognitionDisplay.name
  gestureScoreLabel.value = lastGestureRecognitionDisplay.scoreText
  return true
}

function restoreLastGestureRecognitionDisplay() {
  if (lastGestureRecognitionDisplay) {
    gestureMatchLabel.value = lastGestureRecognitionDisplay.name
    gestureScoreLabel.value = lastGestureRecognitionDisplay.scoreText
    return
  }

  gestureMatchLabel.value = '等待识别'
  gestureScoreLabel.value = '--'
}
</script>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ===== 第一行：速度 + 摄像头 + 健康状态 ===== */
.hero-row {
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr) 280px;
  gap: 16px;
  min-height: 280px;
}

/* 速度表 */
.speedo-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.speed-ring {
  position: relative;
  width: 200px;
  height: 200px;
}

.speed-svg {
  width: 100%;
  height: 100%;
}

.speed-arc {
  transition: stroke-dasharray 600ms var(--ease-out);
}

.speed-value {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.speed-value strong {
  font-size: 64px;
  font-weight: 700;
  line-height: 1;
  letter-spacing: -2px;
  color: var(--text-primary);
}

.speed-value span {
  margin-top: 4px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
  letter-spacing: 1px;
}

.gear-badge {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px 28px;
  background: linear-gradient(135deg, var(--primary-color), #0096c7);
  border-radius: var(--radius-lg);
}

.gear-badge span {
  font-size: 11px;
  font-weight: 600;
  color: rgba(8, 12, 20, 0.7);
  letter-spacing: 1px;
  text-transform: uppercase;
}

.gear-badge strong {
  font-size: 36px;
  font-weight: 800;
  color: #080c14;
  line-height: 1;
}

/* 摄像头画面 */
.camera-duo {
  display: grid;
  grid-template-columns: minmax(0, 1.08fr) minmax(260px, 0.92fr);
  gap: 12px;
  min-width: 0;
  min-height: 280px;
}

.camera-feed {
  padding: 0;
  overflow: hidden;
  border-radius: var(--radius-lg);
  min-width: 0;
}

.camera-inner {
  position: relative;
  height: 100%;
  min-height: 280px;
  background:
    linear-gradient(180deg, rgba(8,12,20,0.15) 0%, rgba(8,12,20,0.55) 100%),
    radial-gradient(ellipse at 50% 70%, #1a2940 0%, #0a1220 70%);
  display: flex;
  align-items: flex-end;
}

.camera-stream {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
  opacity: 0.9;
  background: #070b12;
}

.camera-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: var(--text-muted);
  font-size: 13px;
  font-weight: 700;
  background:
    linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px),
    linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px);
  background-size: 40px 40px;
}

.camera-overlay-info {
  position: absolute;
  z-index: 4;
  top: 14px;
  left: 18px;
  right: 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.camera-label {
  min-width: 0;
  overflow: hidden;
  font-size: 13px;
  font-weight: 700;
  color: rgba(255,255,255,0.85);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.camera-live {
  flex: 0 1 auto;
  min-width: 0;
  overflow: hidden;
  padding: 2px 7px;
  border-radius: 999px;
  background: rgba(8, 12, 20, 0.58);
  font-size: 12px;
  font-weight: 700;
  color: var(--danger-color);
  text-align: right;
  text-overflow: ellipsis;
  white-space: nowrap;
  animation: pulseNumber 1.5s ease-in-out infinite;
}

.camera-live.online {
  color: var(--success-color);
}

.gesture-camera-feed {
  border-color: rgba(0, 180, 216, 0.18);
}

.gesture-camera-feed.active {
  border-color: rgba(0, 180, 216, 0.42);
  box-shadow: 0 0 24px var(--primary-glow);
}

.gesture-camera-inner {
  background:
    linear-gradient(180deg, rgba(8,12,20,0.12) 0%, rgba(8,12,20,0.54) 100%),
    radial-gradient(ellipse at 50% 64%, #15323a 0%, #0a1220 72%);
}

.gesture-local-video,
.gesture-keypoint-overlay {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  transform: scaleX(-1);
}

.gesture-keypoint-overlay {
  z-index: 2;
  pointer-events: none;
}

.gesture-placeholder {
  padding: 24px;
  text-align: center;
}

.gesture-camera-readout {
  position: absolute;
  z-index: 4;
  left: 0;
  right: 0;
  bottom: 0;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  border-top: 1px solid rgba(0, 180, 216, 0.18);
  background: linear-gradient(180deg, rgba(8, 12, 20, 0.2), rgba(8, 12, 20, 0.86));
  backdrop-filter: blur(8px);
}

.gesture-camera-readout div {
  min-width: 0;
  padding: 9px 10px;
  border-right: 1px solid rgba(255, 255, 255, 0.06);
}

.gesture-camera-readout div:last-child {
  border-right: 0;
}

.gesture-camera-readout span {
  display: block;
  color: var(--text-secondary);
  font-size: 10px;
  font-weight: 800;
}

.gesture-camera-readout strong {
  display: block;
  margin-top: 3px;
  overflow: hidden;
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.detection-hint {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 12px 18px;
  background: rgba(255, 171, 0, 0.12);
  border-top: 1px solid rgba(255, 171, 0, 0.2);
  color: var(--warning-color);
  font-size: 14px;
  font-weight: 600;
}

.action-pill {
  margin-left: auto;
  padding: 6px 16px;
  border: 1px solid var(--warning-color);
  border-radius: 999px;
  background: transparent;
  color: var(--warning-color);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: all var(--duration-fast);
}

.action-pill:hover {
  background: var(--warning-color);
  color: #080c14;
}

/* 健康状态 */
.health-stack {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.health-item {
  padding: 14px 16px;
}

.health-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.health-head span {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-secondary);
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.health-item strong {
  display: block;
  margin-top: 6px;
  font-size: 18px;
  color: var(--text-primary);
}

.health-item p {
  margin-top: 4px;
  font-size: 12px;
  color: var(--text-muted);
}

/* ===== 第二行 ===== */
.secondary-row {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 16px;
}

.secondary-row .card.active {
  border-color: rgba(0,180,216,0.35);
  box-shadow: 0 0 22px var(--primary-glow);
}

.card-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 14px;
}

/* 车辆状态 */
.status-grid { }

.status-items {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  background: rgba(255,255,255,0.03);
  border-radius: var(--radius-sm);
  transition: background var(--duration-fast);
}

.status-item.alert {
  background: rgba(255, 171, 0, 0.08);
  border: 1px solid rgba(255, 171, 0, 0.15);
}

.status-item .el-icon {
  color: var(--text-muted);
  font-size: 20px;
}

.status-item strong {
  display: block;
  font-size: 16px;
  color: var(--text-primary);
}

.status-item strong small {
  font-size: 11px;
  color: var(--text-muted);
}

.status-item span {
  font-size: 11px;
  color: var(--text-muted);
}

.climate-row {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-top: 8px;
}

.climate-icon {
  width: 48px;
  height: 48px;
  display: grid;
  place-items: center;
  background: rgba(255,255,255,0.04);
  border-radius: var(--radius-sm);
  color: var(--warning-color);
}

.climate-info strong {
  display: block;
  font-size: 22px;
  color: var(--text-primary);
}

.climate-info span {
  font-size: 12px;
  color: var(--text-muted);
}

/* 多媒体 */
.media-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.media-art {
  width: 64px;
  height: 64px;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, #1a2940, #253a56);
  border-radius: var(--radius-md);
  margin-bottom: 12px;
  color: var(--primary-color);
}

.media-track {
  font-size: 15px;
  color: var(--text-primary);
}

.media-meta {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
}

.media-controls {
  display: flex;
  gap: 10px;
  margin-top: 14px;
}

/* 电话 */
.phone-card { }

.phone-status {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 16px 0;
}

.phone-status .el-icon {
  color: var(--success-color);
}

.phone-status strong {
  font-size: 18px;
  color: var(--text-primary);
}

.phone-status span {
  font-size: 12px;
  color: var(--text-muted);
}

/* 手势控制 */
.gesture-control-card {
  min-height: 180px;
}

.gesture-control-state,
.gesture-control-empty {
  min-height: 96px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  text-align: center;
}

.gesture-badge {
  max-width: 100%;
  padding: 5px 10px;
  border-radius: 999px;
  border: 1px solid rgba(0,180,216,0.3);
  background: var(--primary-soft);
  color: var(--primary-color);
  font-size: 12px;
  font-weight: 800;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.gesture-control-state strong {
  font-size: 17px;
  color: var(--text-primary);
}

.gesture-control-state small,
.gesture-control-empty span {
  font-size: 12px;
  color: var(--text-muted);
}

.gesture-control-empty .el-icon {
  color: var(--text-muted);
}

.gesture-open-button {
  width: 100%;
  min-height: 34px;
  border: 1px solid rgba(0, 180, 216, 0.34);
  border-radius: 8px;
  color: var(--primary-color);
  background: rgba(0, 180, 216, 0.1);
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
}

.gesture-open-button:hover {
  border-color: rgba(0, 180, 216, 0.56);
  background: rgba(0, 180, 216, 0.16);
}

.gesture-open-button.running {
  border-color: rgba(0, 255, 136, 0.34);
  color: var(--success-color);
  background: rgba(0, 255, 136, 0.1);
}

.gesture-open-button:disabled {
  cursor: wait;
  opacity: 0.72;
}

/* 告警快捷卡片 */
.alert-card { }

.alert-mini {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 0;
  cursor: pointer;
  transition: opacity var(--duration-fast);
}

.alert-mini:hover {
  opacity: 0.8;
}

.alert-mini + .alert-mini {
  border-top: 1px solid var(--border-subtle);
}

.alert-mini strong {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.3;
}

.alert-mini span {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 2px;
}

.action-link {
  display: inline-block;
  margin-top: 10px;
  padding: 0;
  border: none;
  background: none;
  color: var(--primary-color);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: color var(--duration-fast);
}

.action-link:hover {
  color: #00e5ff;
}

@media (max-width: 1200px) {
  .hero-row {
    grid-template-columns: 1fr;
  }
  .camera-duo {
    grid-template-columns: 1fr 1fr;
  }
  .secondary-row {
    grid-template-columns: repeat(2, 1fr);
  }
  .speedo-section {
    flex-direction: row;
    justify-content: center;
  }
}

@media (max-width: 760px) {
  .camera-duo {
    grid-template-columns: 1fr;
  }
}
</style>
