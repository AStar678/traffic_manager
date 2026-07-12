<template>
  <div class="dashboard unified-cockpit">
    <header class="perception-bar">
      <div>
        <span class="section-kicker">DRIVE ASSIST</span>
        <strong>行车感知中心</strong>
        <small>三路道路感知与车内手势同步运行</small>
      </div>
      <div class="perception-state" :class="{ stopped: !perceptionEnabled }">
        <span class="state-pulse"></span>
        <div>
          <strong>{{ perceptionEnabled ? '全域识别运行中' : '识别已关闭' }}</strong>
          <small>{{ perceptionEnabled ? '车牌 · 交警 · 车主手势' : '道路视频仍保持预览' }}</small>
        </div>
        <button class="perception-toggle" type="button" @click="toggleUnifiedPerception">
          <el-icon><component :is="perceptionEnabled ? 'VideoPause' : 'VideoPlay'" /></el-icon>
          {{ perceptionEnabled ? '关闭识别' : '开启识别' }}
        </button>
      </div>
    </header>

    <section class="cockpit-grid">
      <aside class="drive-rail">
        <div class="speedo-section compact-speedo">
          <div class="speed-ring">
            <svg viewBox="0 0 200 200" class="speed-svg" aria-hidden="true">
              <circle cx="100" cy="100" r="88" fill="none" stroke="rgba(255,255,255,0.04)" stroke-width="10" />
              <circle
                cx="100" cy="100" r="88"
                fill="none"
                stroke="url(#speedGrad)"
                stroke-width="10"
                stroke-linecap="round"
                :stroke-dasharray="`${Math.min(vehicle.speed / 120, 1) * 553} 553`"
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
            <div class="speed-value"><strong>{{ vehicle.speed }}</strong><span>km/h</span></div>
          </div>
          <div class="gear-badge"><span>当前档位</span><strong>{{ vehicle.gear }}</strong></div>
        </div>

        <div class="drive-health card">
          <div v-for="item in health.slice(0, 3)" :key="item.name" class="health-line">
            <span><i class="status-dot" :class="item.status === 'normal' ? 'online' : 'warning'"></i>{{ item.name }}</span>
            <strong>{{ item.value }}</strong>
          </div>
        </div>
      </aside>

      <section class="vision-stage" aria-label="道路与车内摄像头实时画面">
        <div class="camera-duo compact-camera-duo">
          <article class="camera-feed card">
            <div class="camera-inner">
              <video
                v-show="cameraVideoReady"
                :ref="setDashboardCameraVideoRef"
                class="camera-stream"
                autoplay muted playsinline
                @loadeddata="markCameraVideoReady"
                @playing="markCameraVideoReady"
              ></video>
              <img v-if="!cameraVideoReady && cameraDisplayUrl" class="camera-stream" :src="cameraDisplayUrl" alt="前向道路摄像头预览">
              <div v-if="!cameraVideoReady && !cameraDisplayUrl" class="camera-placeholder">
                <el-icon :size="36"><Camera /></el-icon>
                <span>{{ cameraError || '等待主服务摄像头模块' }}</span>
              </div>
              <div class="camera-overlay-info">
                <span class="camera-label">{{ selectedCameraSource?.name || '前向道路摄像头' }}</span>
                <span class="camera-live">● {{ cameraStatusText }}</span>
              </div>
              <div class="camera-slot-switcher" aria-label="主画面摄像头选择">
                <button
                  v-for="slot in cameraSlots"
                  :key="slot.slotId"
                  type="button"
                  :disabled="slot.sourceType === 'OFF'"
                  :class="{ active: slot.slotId === Number(selectedCameraSourceId) }"
                  @click="selectCameraSlot(slot.slotId)"
                >CAM {{ slot.slotId }}</button>
              </div>
              <div v-if="perceptionEnabled" class="scan-line-animated"></div>
              <div class="vision-caption">
                <span>道路感知</span>
                <strong>{{ roadPerceptionCaption }}</strong>
              </div>
            </div>
          </article>

          <article class="camera-feed card gesture-camera-feed" :class="{ active: gestureControlActive }">
            <div class="camera-inner gesture-camera-inner">
              <video
                v-show="gestureCameraReady"
                ref="gestureVideoRef"
                class="camera-stream gesture-local-video"
                autoplay muted playsinline
                @loadeddata="markGestureCameraReady"
                @playing="markGestureCameraReady"
              ></video>
              <div v-if="!gestureCameraReady" class="camera-placeholder gesture-placeholder">
                <el-icon :size="36"><Pointer /></el-icon>
                <span>{{ gestureCameraError || (perceptionEnabled ? '正在启动车内摄像头' : '识别已关闭') }}</span>
              </div>
              <div class="camera-overlay-info">
                <span class="camera-label">车内手势摄像头</span>
                <span class="camera-live" :class="{ online: gestureControlActive }">● {{ gestureCameraStatusText }}</span>
              </div>
              <div class="vision-caption">
                <span>手势匹配</span>
                <strong>{{ gestureMatchLabel }}</strong>
                <small>{{ gestureTriggerLabel }}</small>
              </div>
            </div>
          </article>
        </div>

        <div class="vehicle-strip">
          <div class="vehicle-metric">
            <el-icon><Sunny /></el-icon><span>空调</span><strong>{{ vehicle.climate.temperature }}°C</strong><small>{{ vehicle.climate.mode }}</small>
          </div>
          <div class="vehicle-metric">
            <el-icon><Headset /></el-icon><span>多媒体</span><strong>{{ vehicle.audio.track }}</strong><small>音量 {{ vehicle.audio.volume }}%</small>
          </div>
          <div class="vehicle-metric">
            <el-icon><Phone /></el-icon><span>电话</span><strong>{{ vehicle.phone.status }}</strong><small>{{ vehicle.phone.caller }}</small>
          </div>
          <button class="vehicle-metric alert-shortcut" type="button" @click="$router.push('/alert-dashboard')">
            <el-icon><Bell /></el-icon><span>系统告警</span><strong>{{ recentAlerts.length }} 条</strong><small>查看全部</small>
          </button>
        </div>
      </section>

      <aside class="recognition-rail">
        <article class="recognition-card plate-result" :class="{ live: perceptionEnabled }">
          <div class="recognition-head">
            <span class="recognition-icon"><el-icon><Postcard /></el-icon></span>
            <div><small>车牌识别</small><strong>{{ plateStatusText }}</strong></div>
            <span class="live-mark">{{ perceptionEnabled ? 'LIVE' : 'OFF' }}</span>
          </div>
          <div class="recognition-value plate-number">{{ latestPlate?.plateNumber || '暂未检测' }}</div>
          <div class="recognition-meta">
            <span class="plate-summary-facts"><i v-if="latestPlate" :class="`plate-color-${plateColorKey(latestPlate)}`"></i>{{ latestPlate ? plateTypeText : '等待车牌进入画面' }}</span>
            <span>{{ plateResult.latencyMs || 0 }} ms</span>
          </div>
          <div v-if="plateExpanded" class="all-plates-list">
            <div v-for="plate in allPlateDetections" :key="`${plate.cameraSlotId}-${plate.objectId}-${plate.plateNumber}`" :title="plate.cameraName">
              <span>CAM {{ plate.cameraSlotId }}</span>
              <strong>{{ plate.plateNumber || '未知车牌' }}</strong>
              <small :class="`plate-color-${plateColorKey(plate)}`">{{ plateColorName(plate) }}</small>
              <em>{{ plateConfidenceText(plate) }}</em>
            </div>
            <p v-if="!allPlateDetections.length">当前三路画面暂无车牌</p>
          </div>
          <div class="plate-actions">
            <button class="detail-button secondary" type="button" @click="plateExpanded = !plateExpanded">
              {{ plateExpanded ? '收起' : `展开全部 (${allPlateDetections.length})` }}
            </button>
            <button class="detail-button" type="button" @click="plateDialogOpen = true">
              查看细节 <el-icon><ArrowRight /></el-icon>
            </button>
          </div>
        </article>

        <article class="recognition-card police-result" :class="{ live: perceptionEnabled }">
          <div class="recognition-head">
            <span class="recognition-icon"><el-icon><Aim /></el-icon></span>
            <div><small>交警手势</small><strong>{{ policeStatusText }}</strong></div>
            <span class="live-mark">{{ perceptionEnabled ? 'LIVE' : 'OFF' }}</span>
          </div>
          <div class="recognition-value">{{ latestPoliceGesture }}</div>
          <div class="recognition-meta">
            <span>{{ latestPoliceAction }}</span>
            <span>{{ policeConfidenceText }}</span>
          </div>
          <button class="detail-button" type="button" @click="policeDialogOpen = true">
            查看细节 <el-icon><ArrowRight /></el-icon>
          </button>
        </article>

        <article class="recognition-card owner-result" :class="{ live: gestureControlActive }">
          <div class="recognition-head">
            <span class="recognition-icon"><el-icon><Pointer /></el-icon></span>
            <div><small>车主手势</small><strong>{{ gestureControlStatus }}</strong></div>
            <span class="live-mark">{{ gestureControlActive ? 'LIVE' : 'OFF' }}</span>
          </div>
          <div class="recognition-value">{{ lastGestureControl?.gestureName || gestureMatchLabel }}</div>
          <div class="recognition-meta">
            <span>{{ lastGestureControl?.actionLabel || '等待操作手势' }}</span>
            <span>{{ lastGestureControl ? lastControlTime : gestureScoreLabel }}</span>
          </div>
          <div class="owner-actions">
            <button class="detail-button" type="button" @click="openOwnerDetail">查看细节</button>
            <button class="detail-button secondary" type="button" @click="openOwnerSettings">手势设置</button>
          </div>
        </article>
      </aside>
    </section>

    <el-dialog v-model="plateDialogOpen" title="车牌识别详情" width="94vw" top="4vh" destroy-on-close class="recognition-dialog" @closed="restoreDashboardCamera">
      <LicensePlatePage embedded :external-result="plateResult" :external-recognizing="perceptionEnabled" @toggle-recognition="toggleUnifiedPerception" />
    </el-dialog>
    <el-dialog v-model="policeDialogOpen" title="交警手势识别详情" width="94vw" top="4vh" destroy-on-close class="recognition-dialog" @closed="restoreDashboardCamera">
      <PoliceGesturePage embedded :external-result="policeResult" :external-recognizing="perceptionEnabled" @toggle-recognition="toggleUnifiedPerception" />
    </el-dialog>
    <el-dialog v-model="ownerDialogOpen" title="车主手势识别详情" width="94vw" top="3vh" destroy-on-close class="recognition-dialog owner-dialog" @closed="ownerSettingsRequested = false">
      <OwnerGesturePage ref="ownerDetailRef" embedded :open-management-on-mount="ownerSettingsRequested" />
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { DrawingUtils, FilesetResolver, GestureRecognizer } from '@/vendor/tasks-vision/vision_bundle.mjs'
import { executeOwnerGestureControl, getOwnerGestureControlSettings, getOwnerGestureData } from '@/api/ownerGestures'
import { getInferenceData, inferenceCameras } from '@/api/inference'
import { mockSystemHealth, mockAlerts } from '@/utils/mockData'
import { useAlertStore } from '@/stores/alert'
import { useCameraSource } from '@/composables/useCameraSource'
import { useVehicleStore } from '@/stores/vehicle'
import { POLICE_GESTURE_MAP, TASK_TYPES } from '@/utils/constants'
import LicensePlatePage from '@/views/LicensePlatePage.vue'
import PoliceGesturePage from '@/views/PoliceGesturePage.vue'
import OwnerGesturePage from '@/views/OwnerGesturePage.vue'
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
  selectedCameraSourceId,
  cameraSlots,
  activeCameraSlots,
  selectedCameraSource,
  cameraStatus,
  cameraError,
  cameraDisplayUrl,
  cameraVideoRef,
  cameraVideoReady,
  markCameraVideoReady,
  refreshCameraPreview,
  selectCameraSlot
} = useCameraSource()

const perceptionEnabled = ref(true)
const plateResult = ref(emptyPerceptionResult(TASK_TYPES.LICENSE_PLATE))
const policeResult = ref(emptyPerceptionResult(TASK_TYPES.POLICE_GESTURE))
const plateRecognitionLoading = ref(false)
const policeRecognitionLoading = ref(false)
const plateRecognitionError = ref('')
const policeRecognitionError = ref('')
const plateDialogOpen = ref(false)
const plateExpanded = ref(false)
const policeDialogOpen = ref(false)
const ownerDialogOpen = ref(false)
const ownerSettingsRequested = ref(false)
const ownerDetailRef = ref(null)
const dashboardCameraElement = ref(null)

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
let plateRecognitionTimer
let policeRecognitionTimer

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

const latestPlate = computed(() => plateResult.value.detections?.[0] || null)
const allPlateDetections = computed(() => plateResult.value.detections || [])
const plateTypeText = computed(() => {
  const item = latestPlate.value
  if (!item) return '暂无类型'
  return `颜色：${plateColorName(item)} · 置信度：${plateConfidenceText(item)}`
})

function plateColorKey(item) {
  const value = String(item?.plateColor || item?.plateType || '').toLowerCase()
  if (value.includes('blue') || value.includes('蓝')) return 'blue'
  if (value.includes('green') || value.includes('绿') || value.includes('新能源')) return 'green'
  if (value.includes('yellow') || value.includes('黄')) return 'yellow'
  if (value.includes('white') || value.includes('白')) return 'white'
  if (value.includes('black') || value.includes('黑')) return 'black'
  return 'unknown'
}

function plateColorName(item) {
  return { blue: '蓝色', green: '绿色', yellow: '黄色', white: '白色', black: '黑色', unknown: '未知' }[plateColorKey(item)]
}

function plateConfidenceText(item) {
  const confidence = Number(item?.ocrConfidence ?? item?.confidence ?? item?.detectionConfidence)
  return Number.isFinite(confidence) ? `${Math.round(confidence * 100)}%` : '--'
}
const latestPoliceDetection = computed(() => policeResult.value.detections?.[0] || null)
const latestPoliceGesture = computed(() => {
  const detection = latestPoliceDetection.value
  return detection?.gestureName || POLICE_GESTURE_MAP[detection?.gestureCode] || '暂未检测'
})
const latestPoliceAction = computed(() => {
  const detection = latestPoliceDetection.value
  if (detection?.action) return detection.action
  const actions = {
    STOP: '停车等待', GO_STRAIGHT: '允许通行', LEFT_TURN: '左转通行',
    LEFT_WAIT: '进入待转区', RIGHT_TURN: '右转通行', LANE_CHANGE: '变更车道',
    SLOW_DOWN: '减速慢行', PULL_OVER: '靠边停车'
  }
  return actions[detection?.gestureCode] || '等待交通指令'
})
const policeConfidenceText = computed(() => {
  const confidence = Number(latestPoliceDetection.value?.confidence)
  return Number.isFinite(confidence) ? `${Math.round(confidence * 100)}%` : '--'
})
const plateStatusText = computed(() => {
  if (!perceptionEnabled.value) return '已停止'
  if (plateRecognitionError.value) return '服务异常'
  if (plateRecognitionLoading.value) return '识别中'
  return latestPlate.value ? '已同步结果' : '持续扫描中'
})
const policeStatusText = computed(() => {
  if (!perceptionEnabled.value) return '已停止'
  if (policeRecognitionError.value) return '服务异常'
  if (policeRecognitionLoading.value) return '识别中'
  return latestPoliceDetection.value ? '已同步结果' : '持续扫描中'
})
const roadPerceptionCaption = computed(() => {
  if (!perceptionEnabled.value) return '仅视频预览'
  const plateCount = plateResult.value.detections?.length || 0
  if (latestPoliceDetection.value) return `交警指令：${latestPoliceGesture.value}`
  if (plateCount) return `已检测 ${plateCount} 个车牌`
  return '车牌与交警手势同步检测'
})

onMounted(() => {
  alertStore.fetchAlerts()
  refreshCameraPreview()
  startRoadRecognition()
  void startGestureControl()
})

onBeforeUnmount(() => {
  stopRoadRecognition()
  stopGestureControl()
})

const recentAlerts = computed(() => mockAlerts.slice(0, 2))

function emptyPerceptionResult(taskType) {
  return {
    taskType,
    latencyMs: 0,
    image: { width: 1280, height: 720 },
    detections: [],
    detectionCount: 0,
    annotatedImageUrl: ''
  }
}

function setDashboardCameraVideoRef(element) {
  if (!element) return
  dashboardCameraElement.value = element
  cameraVideoRef.value = element
}

function restoreDashboardCamera() {
  void nextTick(() => {
    if (dashboardCameraElement.value) {
      cameraVideoRef.value = dashboardCameraElement.value
    }
    refreshCameraPreview()
  })
}

function startRoadRecognition() {
  clearInterval(plateRecognitionTimer)
  clearInterval(policeRecognitionTimer)
  void recognizeRoadTask(TASK_TYPES.LICENSE_PLATE)
  void recognizeRoadTask(TASK_TYPES.POLICE_GESTURE)
  plateRecognitionTimer = window.setInterval(() => {
    void recognizeRoadTask(TASK_TYPES.LICENSE_PLATE)
  }, 800)
  policeRecognitionTimer = window.setInterval(() => {
    void recognizeRoadTask(TASK_TYPES.POLICE_GESTURE)
  }, 1000)
}

function stopRoadRecognition() {
  clearInterval(plateRecognitionTimer)
  clearInterval(policeRecognitionTimer)
  plateRecognitionTimer = undefined
  policeRecognitionTimer = undefined
}

async function recognizeRoadTask(taskType) {
  if (!perceptionEnabled.value || !activeCameraSlots.value.length) return
  const loading = taskType === TASK_TYPES.LICENSE_PLATE ? plateRecognitionLoading : policeRecognitionLoading
  const errorState = taskType === TASK_TYPES.LICENSE_PLATE ? plateRecognitionError : policeRecognitionError
  if (loading.value) return
  loading.value = true
  try {
    const response = await inferenceCameras(taskType)
    if (!perceptionEnabled.value) return
    const data = getInferenceData(response) || {}
    const nextResult = {
      ...emptyPerceptionResult(taskType),
      ...data,
      detections: data.detections || []
    }
    if (taskType === TASK_TYPES.LICENSE_PLATE) plateResult.value = nextResult
    else policeResult.value = nextResult
    errorState.value = ''
  } catch (error) {
    console.error(`${taskType} recognition failed`, error)
    errorState.value = '识别服务连接失败'
  } finally {
    loading.value = false
  }
}

async function toggleUnifiedPerception() {
  if (perceptionEnabled.value) {
    perceptionEnabled.value = false
    stopRoadRecognition()
    stopGestureControl()
    gestureControlStatus.value = '识别已关闭'
    gestureTriggerLabel.value = '识别已关闭'
    return
  }

  perceptionEnabled.value = true
  plateRecognitionError.value = ''
  policeRecognitionError.value = ''
  startRoadRecognition()
  await startGestureControl()
}

function openOwnerDetail() {
  ownerSettingsRequested.value = false
  ownerDialogOpen.value = true
}

function openOwnerSettings() {
  ownerSettingsRequested.value = true
  ownerDialogOpen.value = true
}

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

/* ===== 一体化驾驶主界面 ===== */
.unified-cockpit {
  gap: 12px;
  min-height: 100%;
}

.perception-bar {
  min-height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 10px 14px 10px 18px;
  border: 1px solid var(--border-card);
  border-radius: var(--radius-md);
  background: linear-gradient(90deg, rgba(0, 180, 216, 0.09), rgba(22, 29, 43, 0.78) 38%, rgba(22, 29, 43, 0.96));
}

.perception-bar > div:first-child {
  min-width: 0;
  display: grid;
  grid-template-columns: auto auto;
  align-items: baseline;
  column-gap: 10px;
}

.section-kicker {
  color: var(--primary-color);
  font: 800 10px/1 "SF Mono", "Cascadia Code", monospace;
  letter-spacing: 1.5px;
}

.perception-bar > div:first-child strong {
  color: var(--text-primary);
  font-size: 18px;
  letter-spacing: 0.3px;
}

.perception-bar > div:first-child small {
  grid-column: 1 / -1;
  margin-top: 3px;
  color: var(--text-muted);
  font-size: 11px;
}

.perception-state {
  display: flex;
  align-items: center;
  gap: 10px;
}

.state-pulse {
  width: 10px;
  height: 10px;
  flex: 0 0 10px;
  border-radius: 50%;
  background: var(--success-color);
  box-shadow: 0 0 0 5px rgba(0, 230, 118, 0.12), 0 0 18px rgba(0, 230, 118, 0.38);
  animation: pulseNumber 1.6s ease-in-out infinite;
}

.perception-state.stopped .state-pulse {
  background: var(--text-muted);
  box-shadow: 0 0 0 5px rgba(88, 102, 128, 0.13);
  animation: none;
}

.perception-state > div {
  min-width: 152px;
}

.perception-state strong,
.perception-state small {
  display: block;
}

.perception-state strong {
  color: var(--text-primary);
  font-size: 13px;
}

.perception-state small {
  margin-top: 2px;
  color: var(--text-muted);
  font-size: 10px;
}

.perception-toggle {
  min-width: 112px;
  min-height: 40px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  padding: 0 14px;
  border: 1px solid rgba(0, 180, 216, 0.34);
  border-radius: 10px;
  background: rgba(0, 180, 216, 0.1);
  color: var(--primary-color);
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
}

.perception-state:not(.stopped) .perception-toggle:hover {
  border-color: rgba(255, 61, 0, 0.42);
  background: rgba(255, 61, 0, 0.1);
  color: #ff7043;
}

.cockpit-grid {
  display: grid;
  grid-template-columns: 174px minmax(0, 1fr) 304px;
  gap: 12px;
  align-items: stretch;
  min-height: 0;
}

.drive-rail,
.recognition-rail,
.vision-stage {
  min-width: 0;
}

.drive-rail {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  border: 1px solid var(--border-card);
  border-radius: var(--radius-md);
  background: linear-gradient(180deg, rgba(22, 29, 43, 0.95), rgba(15, 21, 34, 0.94));
}

.compact-speedo {
  gap: 4px;
}

.compact-speedo .speed-ring {
  width: 144px;
  height: 144px;
}

.compact-speedo .speed-value strong {
  font-size: 46px;
}

.compact-speedo .speed-value span {
  font-size: 11px;
}

.compact-speedo .gear-badge {
  width: 100%;
  flex-direction: row;
  justify-content: space-between;
  padding: 8px 14px;
  border-radius: 10px;
}

.compact-speedo .gear-badge strong {
  font-size: 28px;
}

.drive-health {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 9px;
}

.health-line {
  min-height: 44px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 0 4px;
  border-bottom: 1px solid var(--border-subtle);
}

.health-line:last-child { border-bottom: 0; }

.health-line span {
  min-width: 0;
  overflow: hidden;
  color: var(--text-secondary);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.health-line .status-dot {
  margin-right: 5px;
}

.health-line strong {
  flex: 0 0 auto;
  color: var(--text-primary);
  font-size: 12px;
}

.vision-stage {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.compact-camera-duo {
  flex: 1;
  grid-template-columns: minmax(0, 1.08fr) minmax(240px, 0.92fr);
  min-height: 346px;
}

.compact-camera-duo .camera-inner {
  min-height: 346px;
}

.vision-caption {
  position: absolute;
  z-index: 4;
  left: 0;
  right: 0;
  bottom: 0;
  min-height: 64px;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: center;
  gap: 4px 12px;
  padding: 11px 16px;
  background: linear-gradient(180deg, rgba(8, 12, 20, 0.12), rgba(8, 12, 20, 0.92));
  border-top: 1px solid rgba(255, 255, 255, 0.07);
}

.camera-slot-switcher {
  position: absolute;
  z-index: 5;
  top: 47px;
  left: 16px;
  display: flex;
  gap: 6px;
}

.camera-slot-switcher button {
  min-width: 52px;
  min-height: 26px;
  border: 1px solid rgba(255,255,255,.14);
  border-radius: 7px;
  background: rgba(8,12,20,.7);
  color: var(--text-muted);
  font: 800 9px/1 "SF Mono", monospace;
  cursor: pointer;
}

.camera-slot-switcher button.active {
  border-color: rgba(0,180,216,.52);
  background: rgba(0,180,216,.18);
  color: var(--primary-color);
}

.camera-slot-switcher button:disabled { cursor: not-allowed; opacity: .35; }

.vision-caption span {
  color: var(--text-muted);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.7px;
}

.vision-caption strong {
  min-width: 0;
  overflow: hidden;
  color: var(--text-primary);
  font-size: 13px;
  text-align: right;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.vision-caption small {
  grid-column: 1 / -1;
  overflow: hidden;
  color: var(--text-secondary);
  font-size: 10px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.vehicle-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.vehicle-metric {
  min-width: 0;
  min-height: 70px;
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr);
  align-content: center;
  column-gap: 8px;
  padding: 9px 11px;
  border: 1px solid var(--border-card);
  border-radius: 10px;
  background: var(--bg-card);
  color: var(--text-primary);
  text-align: left;
}

.vehicle-metric .el-icon {
  grid-row: 1 / 4;
  align-self: center;
  color: var(--primary-color);
}

.vehicle-metric span,
.vehicle-metric strong,
.vehicle-metric small {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.vehicle-metric span { color: var(--text-muted); font-size: 9px; }
.vehicle-metric strong { color: var(--text-primary); font-size: 12px; }
.vehicle-metric small { color: var(--text-secondary); font-size: 9px; }

.alert-shortcut {
  font: inherit;
  cursor: pointer;
}

.alert-shortcut:hover { border-color: rgba(255, 171, 0, 0.32); }
.alert-shortcut .el-icon { color: var(--warning-color); }

.recognition-rail {
  display: grid;
  grid-template-rows: repeat(3, auto);
  gap: 10px;
}

.recognition-card {
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 13px;
  overflow: hidden;
  border: 1px solid var(--border-card);
  border-radius: var(--radius-md);
  background: linear-gradient(155deg, rgba(28, 36, 52, 0.96), rgba(15, 21, 34, 0.98));
  transition: border-color var(--duration-fast), box-shadow var(--duration-fast);
}

.recognition-card.live { border-color: rgba(0, 180, 216, 0.2); }
.police-result.live { border-color: rgba(255, 171, 0, 0.2); }
.owner-result.live { border-color: rgba(0, 230, 118, 0.2); }

.recognition-head {
  display: grid;
  grid-template-columns: 36px minmax(0, 1fr) auto;
  align-items: center;
  gap: 9px;
}

.recognition-icon {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  border-radius: 10px;
  background: rgba(0, 180, 216, 0.1);
  color: var(--primary-color);
}

.police-result .recognition-icon { background: rgba(255, 171, 0, 0.1); color: var(--warning-color); }
.owner-result .recognition-icon { background: rgba(0, 230, 118, 0.1); color: var(--success-color); }

.recognition-head small,
.recognition-head strong {
  display: block;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.recognition-head small { color: var(--text-muted); font-size: 10px; }
.recognition-head strong { margin-top: 2px; color: var(--text-secondary); font-size: 11px; }

.live-mark {
  padding: 3px 6px;
  border-radius: 5px;
  background: rgba(0, 230, 118, 0.08);
  color: var(--success-color);
  font: 800 9px/1 "SF Mono", monospace;
  letter-spacing: 0.7px;
}

.recognition-card:not(.live) .live-mark {
  background: rgba(88, 102, 128, 0.12);
  color: var(--text-muted);
}

.recognition-value {
  margin-top: 11px;
  overflow: hidden;
  color: var(--text-primary);
  font-size: 21px;
  font-weight: 800;
  line-height: 1.12;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.plate-number {
  font-family: "SF Mono", "Cascadia Code", monospace;
  letter-spacing: 1px;
}

.recognition-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin: 5px 0 10px;
  color: var(--text-muted);
  font-size: 10px;
}

.recognition-meta span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.recognition-meta span:last-child { flex: 0 0 auto; }
.plate-summary-facts { display: inline-flex; align-items: center; gap: 5px; }
.plate-summary-facts i { flex: 0 0 auto; width: 7px; height: 7px; border-radius: 50%; box-shadow: 0 0 7px currentColor; }
.plate-color-blue { color: #4da3ff !important; }
.plate-color-blue:is(i) { background: #4da3ff; }
.plate-color-green { color: #00e676 !important; }
.plate-color-green:is(i) { background: #00e676; }
.plate-color-yellow { color: #ffd43b !important; }
.plate-color-yellow:is(i) { background: #ffd43b; }
.plate-color-white { color: #f8fafc !important; }
.plate-color-white:is(i) { background: #f8fafc; }
.plate-color-black { color: #cbd5e1 !important; }
.plate-color-black:is(i) { background: #111827; border: 1px solid #cbd5e1; }
.plate-color-unknown { color: var(--text-muted) !important; }
.plate-color-unknown:is(i) { background: var(--text-muted); }

.detail-button {
  min-height: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  margin-top: auto;
  border: 1px solid rgba(0, 180, 216, 0.28);
  border-radius: 9px;
  background: rgba(0, 180, 216, 0.08);
  color: var(--primary-color);
  font-size: 11px;
  font-weight: 800;
  cursor: pointer;
}

.detail-button:hover {
  border-color: rgba(0, 180, 216, 0.5);
  background: rgba(0, 180, 216, 0.14);
}

.owner-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 7px;
  margin-top: auto;
}

.plate-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 7px;
  margin-top: auto;
}

.plate-actions .detail-button { margin-top: 0; }

.all-plates-list {
  max-height: 132px;
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin: 0 0 10px;
  overflow-y: auto;
}

.all-plates-list div {
  display: grid;
  grid-template-columns: 40px minmax(0, 1fr) 42px 38px;
  align-items: center;
  gap: 7px;
  padding: 6px 7px;
  border: 1px solid var(--border-subtle);
  border-radius: 7px;
  background: rgba(255,255,255,.025);
}

.all-plates-list span { color: var(--primary-color); font: 800 8px/1 "SF Mono", monospace; }
.all-plates-list strong, .all-plates-list small, .all-plates-list em { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.all-plates-list strong { color: var(--text-primary); font-size: 10px; }
.all-plates-list small, .all-plates-list em { font-size: 8px; font-style: normal; }
.all-plates-list em { color: var(--warning-color); text-align: right; }
.all-plates-list p { padding: 10px; color: var(--text-muted); font-size: 10px; text-align: center; }

.owner-actions .detail-button { margin-top: 0; }
.detail-button.secondary { border-color: var(--border-card); background: rgba(255, 255, 255, 0.03); color: var(--text-secondary); }

:deep(.recognition-dialog) {
  margin-bottom: 0;
}

:deep(.recognition-dialog .el-dialog__header) {
  margin-right: 0;
  padding: 16px 20px 12px;
  border-bottom: 1px solid var(--border-subtle);
}

:deep(.recognition-dialog .el-dialog__body) {
  height: calc(92vh - 66px);
  padding: 14px 18px 18px;
  overflow: auto;
}

:deep(.owner-dialog .el-dialog__body) {
  height: calc(94vh - 66px);
}

@media (max-width: 1180px) {
  .cockpit-grid { grid-template-columns: 150px minmax(0, 1fr); }
  .recognition-rail {
    grid-column: 1 / -1;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    grid-template-rows: none;
  }
  .compact-speedo .speed-ring { width: 124px; height: 124px; }
  .compact-speedo .speed-value strong { font-size: 40px; }
  .compact-speedo { flex-direction: column; }
}

@media (max-width: 820px) {
  .perception-bar,
  .perception-state { align-items: flex-start; }
  .perception-bar { flex-direction: column; }
  .perception-state { width: 100%; }
  .perception-state > div { flex: 1; }
  .cockpit-grid { grid-template-columns: 1fr; }
  .drive-rail { flex-direction: row; align-items: center; }
  .compact-speedo { flex: 0 0 150px; }
  .drive-health { flex: 1; }
  .compact-camera-duo { grid-template-columns: 1fr; min-height: 0; }
  .compact-camera-duo .camera-inner { min-height: 260px; }
  .recognition-rail { grid-column: auto; grid-template-columns: 1fr; }
  .vehicle-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 520px) {
  .perception-state { flex-wrap: wrap; }
  .perception-toggle { width: 100%; }
  .drive-rail { flex-direction: column; }
  .compact-speedo { width: 100%; flex-basis: auto; flex-direction: row; }
  .drive-health { width: 100%; }
  .vehicle-strip { grid-template-columns: 1fr; }
  .owner-actions { grid-template-columns: 1fr; }
  .plate-actions { grid-template-columns: 1fr; }
  :deep(.recognition-dialog .el-dialog__body) { padding: 10px; }
}
</style>
