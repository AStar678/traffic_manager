<template>
  <div ref="pageRef" class="owner-gesture-page">
    <header class="topbar">
      <div>
        <p class="eyebrow">Owner Gesture Control</p>
        <h1>车主手势控车原型网络</h1>
      </div>
      <div class="top-actions">
        <button class="primary" type="button" @click="openManagementDialog">管理手势</button>
        <div class="status-pill" id="modelStatus">模型加载中</div>
      </div>
    </header>

    <main class="layout">
      <section class="camera-panel">
        <div class="video-shell">
          <video id="webcam" autoplay playsinline muted></video>
          <canvas id="overlay"></canvas>
          <div class="camera-empty" id="cameraEmpty">
            <strong>摄像头未启动</strong>
            <span>点击“启动摄像头”后开始录入或识别动作</span>
          </div>
          <div class="viewport-top">
            <span class="chip live">● LIVE</span>
            <span class="chip">车内摄像头</span>
          </div>
        </div>

        <div class="toolbar">
          <button class="primary" id="startCameraBtn" type="button" @click="startCamera">启动摄像头</button>
          <button id="stopCameraBtn" type="button" disabled @click="stopCamera">停止</button>
          <button id="manageGesturesBtn" type="button" @click="openManagementDialog">手势管理</button>
        </div>

        <div class="readout-grid">
          <div class="readout">
            <span>原型匹配</span>
            <strong id="prototypeMatch">未录入</strong>
          </div>
          <div class="readout">
            <span>相似度</span>
            <strong id="similarityScore">--</strong>
          </div>
          <div class="readout">
            <span>误触发状态</span>
            <strong id="triggerState">等待</strong>
          </div>
        </div>
      </section>

      <aside class="side-panel">
        <section class="panel">
          <div class="panel-head">
            <h2>手势库</h2>
            <span id="prototypeCount">0 个</span>
          </div>
          <div class="prototype-list" id="prototypeList"></div>
        </section>

        <section class="panel vehicle-panel">
          <h2>模拟车辆控制</h2>
          <div class="vehicle-state">
            <span>系统</span>
            <strong id="vehiclePower">待唤醒</strong>
          </div>
          <label>
            音量
            <input id="volumeSlider" type="range" min="0" max="100" value="35" />
          </label>
          <label>
            空调温度
            <input id="tempSlider" type="range" min="16" max="30" value="24" />
          </label>
          <div class="vehicle-state">
            <span>电话</span>
            <strong id="phoneState">空闲</strong>
          </div>
          <div class="vehicle-state">
            <span>当前功能</span>
            <strong id="featureState">主页</strong>
          </div>
        </section>
      </aside>
    </main>

    <div class="modal-backdrop" v-show="isManagementOpen" role="dialog" aria-modal="true" aria-labelledby="gestureManagerTitle">
      <section class="gesture-manager">
        <header class="manager-header">
          <div>
            <p class="eyebrow">Gesture Manager</p>
            <h2 id="gestureManagerTitle">自定义手势管理</h2>
          </div>
          <button type="button" @click="closeManagementDialog">关闭</button>
        </header>

        <div class="manager-body">
          <section class="manager-section record-section">
            <div class="panel-head">
              <h3>录入手势</h3>
              <span id="sampleCount">0 / 45 帧</span>
            </div>
            <label>
              动作名称
              <input id="gestureNameInput" type="text" placeholder="例如：挥手返回主页" />
            </label>
            <div class="field-grid">
              <label>
                手势类型
                <select id="gestureKindSelect">
                  <option value="static" selected>静态姿态</option>
                  <option value="dynamic">动态轨迹</option>
                </select>
              </label>
              <label>
                触发持续时间
                <select id="holdMsSelect">
                  <option value="900">0.9 秒</option>
                  <option value="1200" selected>1.2 秒</option>
                  <option value="1800">1.8 秒</option>
                </select>
              </label>
            </div>
            <div class="button-row">
              <button class="primary" id="recordBtn" type="button" disabled @click="startCountdownRecording">录入新手势</button>
              <button id="cancelRecordBtn" type="button" disabled @click="stopRecording">取消录入</button>
            </div>
            <p class="hint" id="recordHint">先选择静态姿态或动态轨迹，点击录入后倒数 3 秒并采集 45 帧保存手势。</p>
          </section>

          <section class="manager-section gesture-management-panel">
            <div class="panel-head management-head">
              <h3>功能关联</h3>
              <button class="primary compact-button" id="saveControlBindingsBtn" type="button" @click="saveControlBindings">保存关联</button>
            </div>
            <div class="gesture-mapping-list" id="gestureMappingList"></div>
          </section>
        </div>
      </section>
    </div>

    <div class="countdown-screen" v-show="isCountdownOpen" role="status" aria-live="assertive">
      <div class="countdown-panel">
        <div class="countdown-preview">
          <video id="countdownWebcam" autoplay playsinline muted></video>
          <div class="countdown-badge">摄像头已打开</div>
        </div>
        <div class="countdown-info">
          <span>准备录入</span>
          <strong>{{ recordingCountdown }}</strong>
          <p>保持手势在画面中央</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { DrawingUtils, FilesetResolver, GestureRecognizer } from '@/vendor/tasks-vision/vision_bundle.mjs'
import {
  executeOwnerGestureControl,
  getOwnerGestureControlSettings,
  getOwnerGestureData,
  saveOwnerGestureControlSettings
} from '@/api/ownerGestures'
import { OWNER_GESTURE_ACTIONS } from '@/utils/constants'
import {
  OWNER_GESTURE_RECOGNITION_CONFIG,
  extractFeatureVector,
  sequenceMotion
} from '@/utils/ownerGesturePrototype'
import { useVehicleStore } from '@/stores/vehicle'

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
  ILoveYou: 'I Love You',
  None: '未识别'
}

const pageRef = ref(null)
const vehicleStore = useVehicleStore()
const isManagementOpen = ref(false)
const isCountdownOpen = ref(false)
const recordingCountdown = ref(3)

let els = {}
let ctx
let drawingUtils
let recognizer
let mediaStream
let animationFrame
let lastVideoTime = -1
let lastPredictFrameAt = 0
let prototypes = []
let isRecording = false
let recognitionSocket
let serviceConfig
let shouldReconnectSocket = true
let controlSettings = []
let actionOptions = OWNER_GESTURE_ACTIONS
let countdownTimer
let lastBuiltInGestureCode = ''
let lastBuiltInGestureAt = 0
let lastBuiltInMatchAt = 0
let builtInGestureStableCode = ''
let builtInGestureStableSince = 0
let builtInGestureVectors = []
let lastRecognizedGestureDisplay

onMounted(async () => {
  await nextTick()
  bindElements()
  await init()
})

onBeforeUnmount(() => {
  shouldReconnectSocket = false
  window.clearInterval(countdownTimer)
  stopCamera()
  recognitionSocket?.close()
  recognitionSocket = undefined
})

function bindElements() {
  const root = pageRef.value
  const find = selector => root.querySelector(selector)
  els = {
    modelStatus: find('#modelStatus'),
    webcam: find('#webcam'),
    countdownWebcam: find('#countdownWebcam'),
    overlay: find('#overlay'),
    cameraEmpty: find('#cameraEmpty'),
    startCameraBtn: find('#startCameraBtn'),
    stopCameraBtn: find('#stopCameraBtn'),
    manageGesturesBtn: find('#manageGesturesBtn'),
    prototypeMatch: find('#prototypeMatch'),
    similarityScore: find('#similarityScore'),
    triggerState: find('#triggerState'),
    gestureNameInput: find('#gestureNameInput'),
    gestureKindSelect: find('#gestureKindSelect'),
    holdMsSelect: find('#holdMsSelect'),
    recordBtn: find('#recordBtn'),
    cancelRecordBtn: find('#cancelRecordBtn'),
    recordHint: find('#recordHint'),
    sampleCount: find('#sampleCount'),
    prototypeCount: find('#prototypeCount'),
    prototypeList: find('#prototypeList'),
    gestureMappingList: find('#gestureMappingList'),
    saveControlBindingsBtn: find('#saveControlBindingsBtn'),
    vehiclePower: find('#vehiclePower'),
    volumeSlider: find('#volumeSlider'),
    tempSlider: find('#tempSlider'),
    phoneState: find('#phoneState'),
    featureState: find('#featureState')
  }
  ctx = els.overlay.getContext('2d')
  drawingUtils = new DrawingUtils(ctx)
}

async function init() {
  await loadServiceState()
  await loadControlSettings()
  syncVehiclePanel()
  connectRecognitionStream()

  try {
    const vision = await FilesetResolver.forVisionTasks('/wasm')
    recognizer = await createRecognizer(vision)
    els.modelStatus.textContent = '模型已就绪'
    els.modelStatus.classList.add('ready')
    updateRecordButton()
  } catch (error) {
    console.error(error)
    els.modelStatus.textContent = '模型加载失败'
    els.modelStatus.classList.add('error')
    els.recordHint.textContent = '请确认已安装依赖并通过本地服务器访问页面。'
  }
}

async function loadServiceState() {
  try {
    applyServiceState(await apiRequest('/api/state'))
  } catch (error) {
    console.error(error)
    renderPrototypes()
    els.triggerState.textContent = '识别服务未连接'
    els.recordHint.textContent = recordingHint()
  }
}

async function loadControlSettings() {
  try {
    applyControlSettings(getOwnerGestureData(await getOwnerGestureControlSettings()))
  } catch (error) {
    console.error(error)
    renderGestureMappings()
  }
}

function connectRecognitionStream() {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
  recognitionSocket = new WebSocket(`${protocol}//${location.host}/api/recognition/stream`)

  recognitionSocket.addEventListener('open', () => {
    els.triggerState.textContent = '识别服务已连接'
  })

  recognitionSocket.addEventListener('message', event => {
    try {
      applyServiceState(JSON.parse(event.data))
    } catch (error) {
      console.error(error)
    }
  })

  recognitionSocket.addEventListener('close', () => {
    if (!shouldReconnectSocket) return
    els.triggerState.textContent = '识别服务重连中'
    window.setTimeout(connectRecognitionStream, 1000)
  })
}

async function startCamera() {
  if (mediaStream) return true
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'user' },
      audio: false
    })
    els.webcam.srcObject = mediaStream
    if (els.countdownWebcam) {
      els.countdownWebcam.srcObject = mediaStream
    }
    await els.webcam.play()
    resizeCanvas()
    els.cameraEmpty.hidden = true
    els.startCameraBtn.disabled = true
    els.stopCameraBtn.disabled = false
    updateRecordButton()
    predictLoop()
    return true
  } catch (error) {
    console.error(error)
    els.recordHint.textContent = '摄像头启动失败：请在浏览器里允许摄像头权限。'
    return false
  }
}

function stopCamera() {
  if (animationFrame) {
    cancelAnimationFrame(animationFrame)
  }
  animationFrame = undefined
  window.clearInterval(countdownTimer)
  isCountdownOpen.value = false
  recordingCountdown.value = 3
  lastPredictFrameAt = 0
  lastBuiltInGestureCode = ''
  lastBuiltInGestureAt = 0
  lastBuiltInMatchAt = 0
  builtInGestureStableCode = ''
  builtInGestureStableSince = 0
  builtInGestureVectors = []
  mediaStream?.getTracks().forEach(track => track.stop())
  mediaStream = undefined
  if (els.webcam) {
    els.webcam.srcObject = null
  }
  if (els.countdownWebcam) {
    els.countdownWebcam.srcObject = null
  }
  if (ctx && els.overlay) {
    ctx.clearRect(0, 0, els.overlay.width, els.overlay.height)
  }
  if (els.cameraEmpty) {
    els.cameraEmpty.hidden = false
    els.startCameraBtn.disabled = false
    els.stopCameraBtn.disabled = true
    updateRecordButton()
  }
  if (isRecording) {
    void stopRecording({ keepHint: true })
  }
}

function predictLoop() {
  if (!recognizer || !mediaStream) return

  try {
    const now = performance.now()
    if (now - lastPredictFrameAt < GESTURE_FRAME_INTERVAL_MS) {
      return
    }
    lastPredictFrameAt = now

    if (els.webcam.videoWidth && els.webcam.videoHeight) {
      resizeCanvas()
    }

    if (els.webcam.currentTime !== lastVideoTime) {
      lastVideoTime = els.webcam.currentTime
      const result = recognizer.recognizeForVideo(els.webcam, now)
      drawResult(result)
      updateRecognition(result)
    }
  } catch (error) {
    console.error('Gesture recognition frame failed.', error)
    els.triggerState.textContent = '识别帧异常，正在恢复'
  } finally {
    if (recognizer && mediaStream) {
      animationFrame = requestAnimationFrame(predictLoop)
    }
  }
}

function drawResult(result) {
  ctx.clearRect(0, 0, els.overlay.width, els.overlay.height)
  const landmarks = result.landmarks?.[0]
  if (!landmarks) return

  drawingUtils.drawConnectors(landmarks, GestureRecognizer.HAND_CONNECTIONS, {
    color: '#00b4d8',
    lineWidth: 3
  })
  drawingUtils.drawLandmarks(landmarks, {
    color: '#080c14',
    fillColor: '#00e676',
    lineWidth: 1,
    radius: 4
  })
}

function updateRecognition(result) {
  const landmarks = result.landmarks?.[0]
  if (!landmarks) {
    resetBuiltInGestureState()
    restoreLastRecognizedGestureDisplay()
    els.triggerState.textContent = '未检测到手'
    return
  }

  const vector = extractFeatureVector(landmarks, result.worldLandmarks?.[0])
  handleBuiltInRecognition(result.gestures?.[0]?.[0], vector)
  sendRecognitionFrame(vector)
}

function handleBuiltInRecognition(category, vector) {
  if (isRecording) return
  const gestureCode = category?.categoryName
  const score = Number(category?.score || 0)
  const now = performance.now()
  if (!gestureCode || gestureCode === 'None' || score < BUILT_IN_GESTURE_THRESHOLD) {
    resetBuiltInGestureState()
    return
  }

  const config = builtInGestureConfig()
  const gestureName = translateBuiltin(gestureCode)
  const recognitionHoldMs = builtInStaticRecognitionHoldMs(config)
  const triggerHoldMs = builtInGestureHoldMs(gestureCode)
  const motion = trackBuiltInGestureMotion(gestureCode, vector, config)
  lastBuiltInMatchAt = now

  if (motion > builtInStaticMotionLimit(config)) {
    builtInGestureStableSince = 0
    els.prototypeMatch.textContent = '静态确认中'
    els.similarityScore.textContent = '--'
    els.triggerState.textContent = '请保持静止'
    return
  }

  if (!builtInGestureStableSince) {
    builtInGestureStableSince = now
  }
  const stableElapsed = now - builtInGestureStableSince
  if (stableElapsed < recognitionHoldMs) {
    els.prototypeMatch.textContent = '静态确认中'
    els.similarityScore.textContent = '--'
    els.triggerState.textContent = builtInGestureHoldLabel(recognitionHoldMs - stableElapsed)
    return
  }

  lastBuiltInMatchAt = now
  rememberRecognizedGestureDisplay(gestureName, formatGestureScore(score))

  if (gestureCode === lastBuiltInGestureCode && now - lastBuiltInGestureAt < BUILT_IN_GESTURE_COOLDOWN_MS) {
    return
  }

  const binding = controlSettings.find(item => String(item.gestureCode) === String(gestureCode))
  if (!binding?.enabled || binding.actionType === 'NONE') {
    els.triggerState.textContent = '已识别，未关联车辆功能'
    return
  }

  if (stableElapsed < triggerHoldMs) {
    els.triggerState.textContent = `稳定中 ${formatHoldSeconds(triggerHoldMs - stableElapsed)}s`
    return
  }

  lastBuiltInGestureCode = gestureCode
  lastBuiltInGestureAt = now
  void executeRecognizedGesture({
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

function openManagementDialog() {
  isManagementOpen.value = true
  renderPrototypes()
  renderGestureMappings()
}

function closeManagementDialog() {
  if (isRecording || isCountdownOpen.value) return
  isManagementOpen.value = false
}

async function startCountdownRecording() {
  const name = els.gestureNameInput.value.trim()
  if (!name) {
    els.recordHint.textContent = '请先输入动作名称。'
    els.gestureNameInput.focus()
    return
  }
  if (!recognizer) {
    els.recordHint.textContent = '模型仍在加载，请稍后再录入。'
    return
  }
  if (!mediaStream) {
    const started = await startCamera()
    if (!started) return
  }

  window.clearInterval(countdownTimer)
  recordingCountdown.value = 3
  isCountdownOpen.value = true
  await syncCountdownPreview()
  updateRecordButton()
  countdownTimer = window.setInterval(async () => {
    recordingCountdown.value -= 1
    if (recordingCountdown.value > 0) return
    window.clearInterval(countdownTimer)
    isCountdownOpen.value = false
    updateRecordButton()
    await beginRecording()
  }, 1000)
}

async function syncCountdownPreview() {
  if (!els.countdownWebcam || !mediaStream) return
  if (els.countdownWebcam.srcObject !== mediaStream) {
    els.countdownWebcam.srcObject = mediaStream
  }
  try {
    await els.countdownWebcam.play()
  } catch (error) {
    console.warn('Countdown camera preview could not autoplay.', error)
  }
}

async function beginRecording() {
  const name = els.gestureNameInput.value.trim()
  if (!name) {
    els.recordHint.textContent = '请先输入动作名称。'
    els.gestureNameInput.focus()
    return
  }

  try {
    const state = await apiRequest('/api/recordings/start', {
      method: 'POST',
      body: {
        name,
        kind: els.gestureKindSelect.value,
        holdMs: Number(els.holdMsSelect.value)
      }
    })
    els.recordHint.textContent = recordingPhaseHint({
      active: true,
      phase: 'sampling',
      kind: els.gestureKindSelect.value,
      sampleCount: 0,
      sampleTarget: sampleTarget()
    })
    applyServiceState(state)
  } catch (error) {
    console.error(error)
    els.recordHint.textContent = '录入启动失败，请确认识别服务正在运行。'
  }
}

async function stopRecording(options = {}) {
  try {
    applyServiceState(await apiRequest('/api/recordings/cancel', { method: 'POST' }))
  } catch (error) {
    console.error(error)
  } finally {
    if (!options.keepHint) {
      els.recordHint.textContent = recordingHint()
    }
  }
}

function recordingHint() {
  return `先选择静态姿态或动态轨迹，点击录入后倒数 3 秒并采集 ${sampleTarget()} 帧保存手势。`
}

function sendRecognitionFrame(vector) {
  if (!recognitionSocket || recognitionSocket.readyState !== WebSocket.OPEN) {
    els.triggerState.textContent = '识别服务未连接'
    return
  }
  recognitionSocket.send(JSON.stringify({ type: 'frame', vector }))
}

async function apiRequest(path, options = {}) {
  const response = await fetch(path, {
    method: options.method || 'GET',
    headers: options.body ? { 'Content-Type': 'application/json' } : undefined,
    body: options.body ? JSON.stringify(options.body) : undefined
  })

  if (!response.ok) {
    throw new Error(`API ${path} failed: ${response.status}`)
  }

  return response.json()
}

function applyServiceState(state) {
  if (state.config) {
    serviceConfig = state.config
  }

  if (state.prototypes) {
    prototypes = state.prototypes
    renderPrototypes()
    renderGestureMappings()
  }

  if (state.recording) {
    isRecording = state.recording.active
    els.sampleCount.textContent = recordingProgressText(state.recording)
    if (isRecording && state.recording.kind && els.gestureKindSelect) {
      els.gestureKindSelect.value = state.recording.kind
    }
    els.cancelRecordBtn.disabled = !isRecording
    updateRecordButton()
    if (isRecording) {
      els.recordHint.textContent = recordingPhaseHint(state.recording)
    }
  }

  if (state.recordingComplete) {
    els.recordHint.textContent = `已录入“${state.recordingComplete.name}”为${kindLabel(state.recordingComplete.kind)}。`
    if (els.gestureKindSelect) {
      els.gestureKindSelect.value = state.recordingComplete.kind || els.gestureKindSelect.value
    }
    els.gestureNameInput.value = ''
    void loadControlSettings()
  }

  if (state.recognition) {
    const recognition = state.recognition
    const shouldKeepBuiltInDisplay =
      !recognition.accepted &&
      lastBuiltInMatchAt &&
      performance.now() - lastBuiltInMatchAt < BUILT_IN_DISPLAY_GRACE_MS

    const scoreText =
      recognition.score === null || recognition.score === undefined
        ? recognition.motionLabel || '--'
        : formatGestureScore(recognition.score)
    const recognized = recognition.accepted && rememberRecognizedGestureDisplay(recognition.name, scoreText)

    if (!shouldKeepBuiltInDisplay) {
      if (!recognized) {
        restoreLastRecognizedGestureDisplay()
      }
      els.triggerState.textContent = recognition.triggerState
    }
    if (recognition.triggered) {
      void executeRecognizedGesture(recognition)
    }
  }

  if (state.vehicle) {
    syncVehiclePanel()
  }
}

function formatGestureScore(score) {
  const numericScore = Number(score)
  return Number.isFinite(numericScore) ? numericScore.toFixed(3) : '--'
}

function rememberRecognizedGestureDisplay(name, scoreText) {
  const gestureName = String(name || '').trim()
  const normalizedName = gestureName.toLowerCase()
  if (!gestureName || ['unknown', 'none', '未识别', '未录入'].includes(normalizedName)) {
    return false
  }

  lastRecognizedGestureDisplay = {
    name: gestureName,
    scoreText: scoreText || '--'
  }
  els.prototypeMatch.textContent = lastRecognizedGestureDisplay.name
  els.similarityScore.textContent = lastRecognizedGestureDisplay.scoreText
  return true
}

function restoreLastRecognizedGestureDisplay() {
  if (lastRecognizedGestureDisplay) {
    els.prototypeMatch.textContent = lastRecognizedGestureDisplay.name
    els.similarityScore.textContent = lastRecognizedGestureDisplay.scoreText
    return
  }

  els.prototypeMatch.textContent = prototypes.length ? '等待识别' : '未录入'
  els.similarityScore.textContent = '--'
}

function translateBuiltin(name) {
  return BUILT_IN_GESTURE_LABELS[name] || name
}

function builtInGestureHoldMs(gestureCode) {
  const setting = controlSettings.find(item => String(item.gestureCode) === String(gestureCode))
  return positiveMs(setting?.holdMs, positiveMs(serviceConfig?.defaultHoldMs, BUILT_IN_GESTURE_FALLBACK_HOLD_MS))
}

function builtInStaticRecognitionHoldMs(config) {
  return positiveMs(config.staticRecognitionHoldMs, OWNER_GESTURE_RECOGNITION_CONFIG.staticRecognitionHoldMs)
}

function builtInStaticMotionLimit(config) {
  return positiveMs(config.staticMotionHardLimit, positiveMs(config.staticStillMotionLimit, OWNER_GESTURE_RECOGNITION_CONFIG.staticStillMotionLimit))
}

function builtInGestureConfig() {
  return { ...OWNER_GESTURE_RECOGNITION_CONFIG, ...(serviceConfig || {}) }
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

function applyControlSettings(data = {}) {
  if (data.config) {
    serviceConfig = { ...(serviceConfig || {}), ...data.config }
  }
  actionOptions = Array.isArray(data.actions) && data.actions.length ? data.actions : OWNER_GESTURE_ACTIONS
  controlSettings = Array.isArray(data.settings) ? data.settings : []
  renderPrototypes()
  renderGestureMappings()
}

function updateRecordButton() {
  if (els.recordBtn) {
    els.recordBtn.disabled = isRecording || isCountdownOpen.value || !recognizer
  }
  if (els.gestureKindSelect) {
    els.gestureKindSelect.disabled = isRecording || isCountdownOpen.value
  }
}

async function createRecognizer(vision) {
  const options = {
    baseOptions: {
      modelAssetPath: MODEL_PATH,
      delegate: 'GPU'
    },
    runningMode: 'VIDEO',
    numHands: 1
  }

  try {
    return await GestureRecognizer.createFromOptions(vision, options)
  } catch (error) {
    console.warn('GPU delegate unavailable, falling back to CPU.', error)
    return GestureRecognizer.createFromOptions(vision, {
      ...options,
      baseOptions: {
        modelAssetPath: MODEL_PATH,
        delegate: 'CPU'
      }
    })
  }
}

function renderPrototypes() {
  const rows = gestureManagementRows()
  els.prototypeCount.textContent = `${rows.length} 个`
  if (!rows.length) {
    els.prototypeList.innerHTML = '<div class="empty-list">暂无动作，录入后会显示在这里。</div>'
    return
  }

  els.prototypeList.innerHTML = ''
  for (const row of rows) {
    const item = document.createElement('div')
    item.className = 'prototype-item'
    item.innerHTML = `
      <div>
        <strong>${escapeHtml(row.gestureName)}</strong>
        <span>${sourceLabel(row.gestureSource)} · ${kindLabel(row.gestureKind)} · ${row.enabled ? escapeHtml(row.actionLabel) : '未关联控制'}</span>
      </div>
      <button type="button">管理</button>
    `
    item.querySelector('button').addEventListener('click', openManagementDialog)
    els.prototypeList.append(item)
  }
}

async function clearPrototypes() {
  try {
    applyServiceState(await apiRequest('/api/prototypes', { method: 'DELETE' }))
    await loadControlSettings()
    lastRecognizedGestureDisplay = undefined
    els.prototypeMatch.textContent = '未录入'
    els.similarityScore.textContent = '--'
  } catch (error) {
    console.error(error)
  }
}

function renderGestureMappings() {
  if (!els.gestureMappingList) return
  const rows = gestureManagementRows()
  if (!rows.length) {
    els.gestureMappingList.innerHTML = '<div class="empty-list">暂无可管理手势。</div>'
    return
  }

  els.gestureMappingList.innerHTML = ''
  for (const row of rows) {
    const item = document.createElement('div')
    item.className = `mapping-item ${row.enabled ? 'bound' : ''}`
    item.innerHTML = `
      <div class="mapping-meta">
        <strong>${escapeHtml(row.gestureName)}</strong>
        <span>${sourceLabel(row.gestureSource)} · ${kindLabel(row.gestureKind)}</span>
      </div>
      <select aria-label="关联 ${escapeHtml(row.gestureName)} 到车辆功能" data-gesture-code="${escapeHtml(row.gestureCode)}">
        ${actionOptionsHtml(row.actionType)}
      </select>
      <button class="delete-gesture-button" type="button" ${isSystemGesture(row) ? 'disabled' : ''}>删除</button>
    `
    item.querySelector('select').addEventListener('change', event => {
      updateLocalControlSetting(row, event.target.value)
      item.classList.toggle('bound', event.target.value !== 'NONE')
    })
    item.querySelector('.delete-gesture-button').addEventListener('click', () => {
      void deleteGesture(row)
    })
    els.gestureMappingList.append(item)
  }
}

async function deleteGesture(row) {
  if (isSystemGesture(row)) return
  const gestureCode = row?.gestureCode
  if (!gestureCode) return
  try {
    applyServiceState(await apiRequest(`/api/prototypes/${encodeURIComponent(gestureCode)}`, { method: 'DELETE' }))
    await loadControlSettings()
    ElMessage.success('手势已删除')
  } catch (error) {
    console.error(error)
  }
}

function gestureManagementRows() {
  const rows = new Map()
  for (const prototype of prototypes) {
    const gestureCode = prototype.id || prototype.gestureCode || prototype.name
    rows.set(String(gestureCode), {
      gestureCode: String(gestureCode),
      gestureName: prototype.name || prototype.gestureName || String(gestureCode),
      gestureKind: prototype.kind || 'static',
      gestureSource: prototype.source || 'custom',
      holdMs: positiveMs(prototype.holdMs, positiveMs(serviceConfig?.defaultHoldMs, BUILT_IN_GESTURE_FALLBACK_HOLD_MS)),
      actionType: 'NONE',
      actionLabel: '不触发控制',
      enabled: false
    })
  }
  for (const setting of controlSettings) {
    const gestureCode = String(setting.gestureCode || '')
    if (!gestureCode) continue
    rows.set(gestureCode, {
      ...(rows.get(gestureCode) || {}),
      ...setting,
      gestureCode,
      gestureName: setting.gestureName || rows.get(gestureCode)?.gestureName || gestureCode,
      holdMs: positiveMs(setting.holdMs, rows.get(gestureCode)?.holdMs || positiveMs(serviceConfig?.defaultHoldMs, BUILT_IN_GESTURE_FALLBACK_HOLD_MS)),
      actionType: setting.actionType || 'NONE',
      actionLabel: setting.actionLabel || actionLabel(setting.actionType),
      enabled: Boolean(setting.enabled) && setting.actionType !== 'NONE'
    })
  }
  return Array.from(rows.values())
}

function updateLocalControlSetting(row, actionType) {
  const normalized = actionType || 'NONE'
  const nextSetting = {
    ...row,
    actionType: normalized,
    actionLabel: actionLabel(normalized),
    enabled: normalized !== 'NONE'
  }
  const index = controlSettings.findIndex(item => String(item.gestureCode) === String(row.gestureCode))
  if (index >= 0) {
    controlSettings[index] = nextSetting
  } else {
    controlSettings.push(nextSetting)
  }
  renderPrototypes()
}

async function saveControlBindings() {
  const settings = gestureManagementRows().map(row => ({
    gestureCode: row.gestureCode,
    gestureName: row.gestureName,
    gestureKind: row.gestureKind,
    gestureSource: row.gestureSource,
    holdMs: positiveMs(row.holdMs, positiveMs(serviceConfig?.defaultHoldMs, BUILT_IN_GESTURE_FALLBACK_HOLD_MS)),
    actionType: row.actionType || 'NONE',
    enabled: Boolean(row.actionType && row.actionType !== 'NONE')
  }))

  try {
    els.saveControlBindingsBtn.disabled = true
    applyControlSettings(getOwnerGestureData(await saveOwnerGestureControlSettings({ settings })))
    ElMessage.success('手势功能关联已保存')
  } catch (error) {
    console.error(error)
  } finally {
    els.saveControlBindingsBtn.disabled = false
  }
}

async function executeRecognizedGesture(recognition) {
  const prototype = prototypes.find(item => item.name === recognition.name)
  const gestureCode = recognition.gestureCode || recognition.id || prototype?.id || recognition.name
  try {
    const control = getOwnerGestureData(await executeOwnerGestureControl({
      gestureCode,
      gestureName: recognition.name,
      confidence: recognition.score
    }))
    if (!control?.enabled) {
      els.triggerState.textContent = '已识别，未关联车辆功能'
      return
    }
    vehicleStore.applyGestureControl(control)
    syncVehiclePanel()
    els.triggerState.textContent = `已触发：${control.actionLabel}`
  } catch (error) {
    console.error(error)
    els.triggerState.textContent = '控制绑定查询失败'
  }
}

function syncVehiclePanel() {
  const vehicle = vehicleStore.vehicle
  els.vehiclePower.textContent = vehicle.systemAwake ? '已唤醒' : '待唤醒'
  els.volumeSlider.value = vehicle.audio?.volume ?? 35
  els.tempSlider.value = vehicle.climate?.temperature ?? 24
  els.phoneState.textContent = vehicle.phone?.status || '待机'
  els.featureState.textContent = vehicle.activeModule || '驾驶'
}

function resizeCanvas() {
  const width = els.webcam.videoWidth
  const height = els.webcam.videoHeight
  if (!width || !height) return
  if (els.overlay.width !== width || els.overlay.height !== height) {
    els.overlay.width = width
    els.overlay.height = height
  }
}

function actionLabel(action) {
  return actionOptions.find(item => item.actionType === action)?.actionLabel || action || '不触发控制'
}

function controlSettingForGesture(prototype) {
  const gestureCode = String(prototype.id || prototype.gestureCode || '')
  return controlSettings.find(item => String(item.gestureCode) === gestureCode)
}

function controlLabelForGesture(prototype) {
  const setting = controlSettingForGesture(prototype)
  return setting?.enabled ? setting.actionLabel || actionLabel(setting.actionType) : '未关联控制'
}

function actionOptionsHtml(selectedAction) {
  return actionOptions.map(action => {
    const selected = action.actionType === selectedAction ? ' selected' : ''
    return `<option value="${escapeHtml(action.actionType)}"${selected}>${escapeHtml(action.actionLabel)}</option>`
  }).join('')
}

function sourceLabel(source) {
  return source === 'built_in' || source === 'system' ? '系统手势' : '自定义手势'
}

function isSystemGesture(row) {
  return row.gestureSource === 'built_in' || row.gestureSource === 'system'
}

function kindLabel(kind) {
  return kind === 'dynamic' ? '动态轨迹' : '静态姿态'
}

function sampleTarget() {
  return serviceConfig?.sampleTarget || 45
}

function recordingProgressText(recording) {
  if (!recording?.active) {
    return `0 / ${sampleTarget()} 帧`
  }
  return `采样 ${recording.sampleCount ?? recording.count ?? 0} / ${recording.sampleTarget ?? sampleTarget()} 帧`
}

function recordingPhaseHint(recording) {
  if (recording?.phase === 'sampling') {
    const count = recording.sampleCount ?? 0
    const target = recording.sampleTarget ?? sampleTarget()
    return `正在录入${kindLabel(recording.kind)}：${count} / ${target} 帧。`
  }
  return recordingHint()
}

function escapeHtml(value = '') {
  return String(value).replace(/[&<>"']/g, char => {
    const entities = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }
    return entities[char]
  })
}
</script>

<style scoped>
.owner-gesture-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
  min-height: 0;
  color: var(--text-primary);
}

.owner-gesture-page *,
.owner-gesture-page *::before,
.owner-gesture-page *::after {
  box-sizing: border-box;
}

.owner-gesture-page button,
.owner-gesture-page input,
.owner-gesture-page select {
  font: inherit;
  color: inherit;
}

.owner-gesture-page button {
  min-height: 40px;
  border: 1px solid var(--border-card);
  border-radius: 12px;
  padding: 0 14px;
  color: var(--text-secondary);
  background: rgba(255, 255, 255, 0.03);
  cursor: pointer;
  font-size: 13px;
  font-weight: 700;
  transition: border-color var(--duration-fast) var(--ease-out),
    background var(--duration-fast) var(--ease-out),
    color var(--duration-fast) var(--ease-out),
    transform var(--duration-fast) var(--ease-out);
}

.owner-gesture-page button:hover:not(:disabled) {
  border-color: var(--border-active);
  color: var(--text-primary);
  background: var(--bg-card-hover);
}

.owner-gesture-page button:active:not(:disabled) {
  transform: translateY(1px);
}

.owner-gesture-page button:disabled {
  cursor: not-allowed;
  color: var(--text-muted);
  background: rgba(255, 255, 255, 0.025);
  opacity: 0.58;
}

.primary {
  border-color: var(--primary-color);
  color: var(--text-inverse);
  background: linear-gradient(135deg, var(--primary-color), #0096c7);
  box-shadow: 0 4px 18px var(--primary-glow);
}

.primary:hover:not(:disabled) {
  border-color: #00cdf0;
  color: var(--text-inverse);
  background: linear-gradient(135deg, #00cdf0, var(--primary-color));
  box-shadow: 0 6px 26px rgba(0, 180, 216, 0.35);
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex: 0 0 auto;
}

.top-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.eyebrow {
  margin: 0 0 4px;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0;
}

h1,
h2,
h3 {
  margin: 0;
  letter-spacing: 0;
}

h1 {
  font-size: 24px;
  line-height: 1.2;
  color: var(--text-primary);
}

h2 {
  font-size: 15px;
  line-height: 1.35;
  color: var(--text-primary);
}

h3 {
  font-size: 14px;
  line-height: 1.35;
  color: var(--text-primary);
}

.status-pill {
  min-width: 112px;
  border: 1px solid rgba(255, 171, 0, 0.28);
  border-radius: 999px;
  padding: 8px 12px;
  color: var(--warning-color);
  background: rgba(255, 171, 0, 0.08);
  font-size: 12px;
  font-weight: 700;
  text-align: center;
}

.status-pill.ready {
  color: var(--success-color);
  background: rgba(0, 230, 118, 0.08);
  border-color: rgba(0, 230, 118, 0.28);
}

.status-pill.error {
  color: var(--danger-color);
  background: rgba(255, 61, 0, 0.08);
  border-color: rgba(255, 61, 0, 0.28);
}

.layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  align-items: start;
  gap: 16px;
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
}

.camera-panel,
.panel {
  border: 1px solid var(--border-card);
  border-radius: var(--radius-md);
  background: var(--bg-card);
  box-shadow: none;
}

.camera-panel {
  min-width: 0;
  overflow: hidden;
}

.video-shell {
  position: relative;
  aspect-ratio: 16 / 9;
  min-height: 0;
  background: #080c14;
}

video,
canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

video,
canvas {
  transform: scaleX(-1);
}

video {
  z-index: 0;
  background: #070b12;
}

canvas {
  z-index: 1;
  background: transparent;
  pointer-events: none;
}

.camera-empty {
  position: absolute;
  z-index: 2;
  inset: 0;
  display: grid;
  place-content: center;
  gap: 10px;
  padding: 24px;
  color: var(--text-muted);
  text-align: center;
  background:
    linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px),
    linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px);
  background-size: 40px 40px;
}

.camera-empty[hidden] {
  display: none;
}

.camera-empty strong {
  color: var(--text-secondary);
  font-size: 18px;
}

.camera-empty span {
  color: var(--text-muted);
  font-size: 13px;
}

.viewport-top {
  position: absolute;
  z-index: 3;
  top: 14px;
  left: 16px;
  display: flex;
  gap: 8px;
  pointer-events: none;
}

.chip {
  padding: 5px 12px;
  background: rgba(0,0,0,0.6);
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  color: var(--text-secondary);
  backdrop-filter: blur(6px);
}

.chip.live {
  color: var(--danger-color);
  border-color: rgba(255, 61, 0, 0.4);
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding: 14px;
  border-bottom: 1px solid var(--border-subtle);
}

.readout-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  border-top: 1px solid var(--border-subtle);
}

.readout {
  min-width: 0;
  padding: 16px;
  border-right: 1px solid var(--border-subtle);
}

.readout:last-child {
  border-right: 0;
}

.readout span,
label,
.prototype-item span,
.vehicle-state span,
.hint {
  color: var(--text-muted);
  font-size: 12px;
}

.readout strong {
  display: block;
  margin-top: 6px;
  overflow: hidden;
  color: var(--text-primary);
  font-size: 18px;
  line-height: 1.25;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.side-panel {
  display: grid;
  gap: 14px;
  align-content: start;
  min-width: 0;
}

.panel {
  padding: 16px;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.panel-head span {
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 700;
}

.management-head {
  align-items: flex-start;
}

.compact-button {
  min-height: 34px;
  padding: 0 12px;
  font-size: 12px;
}

label {
  display: grid;
  gap: 7px;
  margin-bottom: 12px;
  font-weight: 700;
  color: var(--text-secondary);
}

input[type="text"],
select {
  width: 100%;
  min-height: 40px;
  border: 1px solid var(--border-card);
  border-radius: 10px;
  padding: 0 11px;
  color: var(--text-primary);
  background: var(--bg-surface);
}

input[type="text"]:focus,
select:focus,
button:focus-visible {
  outline: 2px solid var(--border-active);
  outline-offset: 2px;
}

input[type="range"] {
  width: 100%;
  accent-color: var(--primary-color);
}

.button-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.field-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.hint {
  margin: 12px 0 0;
  line-height: 1.55;
}

.prototype-list {
  display: grid;
  gap: 8px;
}

.gesture-mapping-list {
  display: grid;
  gap: 8px;
}

.mapping-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 152px auto;
  gap: 10px;
  align-items: center;
  border: 1px solid var(--border-card);
  border-radius: var(--radius-sm);
  padding: 10px;
  background: rgba(255,255,255,0.025);
}

.mapping-item.bound {
  border-color: rgba(0, 180, 216, 0.32);
  background: var(--primary-soft);
}

.mapping-meta {
  min-width: 0;
}

.mapping-meta strong,
.mapping-meta span {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mapping-meta span {
  margin-top: 3px;
  color: var(--text-muted);
  font-size: 12px;
}

.mapping-item select {
  min-height: 36px;
}

.delete-gesture-button {
  min-height: 36px;
  padding: 0 10px;
}

:deep(.mapping-item) {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 152px auto;
  gap: 10px;
  align-items: center;
  border: 1px solid var(--border-card);
  border-radius: var(--radius-sm);
  padding: 10px;
  background: rgba(255,255,255,0.025);
}

:deep(.mapping-item.bound) {
  border-color: rgba(0, 180, 216, 0.32);
  background: var(--primary-soft);
}

:deep(.mapping-meta) {
  min-width: 0;
}

:deep(.mapping-meta strong),
:deep(.mapping-meta span) {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

:deep(.mapping-meta span) {
  margin-top: 3px;
  color: var(--text-muted);
  font-size: 12px;
}

:deep(.mapping-item select) {
  min-height: 36px;
  border: 1px solid var(--border-card);
  border-radius: 10px;
  padding: 0 10px;
  color: var(--text-primary);
  background: var(--bg-surface);
}

:deep(.delete-gesture-button) {
  min-height: 36px;
  padding: 0 10px;
  border: 1px solid var(--border-card);
  border-radius: 10px;
  color: var(--text-secondary);
  background: rgba(255, 255, 255, 0.03);
  font-size: 12px;
  font-weight: 700;
}

:deep(.delete-gesture-button:hover:not(:disabled)) {
  border-color: rgba(255, 61, 0, 0.36);
  color: var(--danger-color);
  background: rgba(255, 61, 0, 0.08);
}

.prototype-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border: 1px solid var(--border-card);
  border-radius: var(--radius-sm);
  padding: 10px;
  background: rgba(255,255,255,0.025);
}

.prototype-item div {
  min-width: 0;
}

.prototype-item strong,
.prototype-item span {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.prototype-item button {
  min-height: 34px;
  padding: 0 10px;
}

:deep(.prototype-item) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border: 1px solid var(--border-card);
  border-radius: var(--radius-sm);
  padding: 10px;
  background: rgba(255,255,255,0.025);
}

:deep(.prototype-item div) {
  min-width: 0;
}

:deep(.prototype-item strong),
:deep(.prototype-item span) {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

:deep(.prototype-item span) {
  color: var(--text-muted);
  font-size: 12px;
}

:deep(.prototype-item button) {
  min-height: 34px;
  padding: 0 10px;
  border: 1px solid var(--border-card);
  border-radius: 10px;
  color: var(--text-secondary);
  background: rgba(255, 255, 255, 0.03);
  font-size: 12px;
  font-weight: 700;
}

:deep(.prototype-item button:hover:not(:disabled)) {
  border-color: var(--border-active);
  color: var(--text-primary);
  background: var(--bg-card-hover);
}

.empty-list {
  border: 1px dashed var(--border-card);
  border-radius: var(--radius-sm);
  padding: 14px;
  color: var(--text-muted);
  background: rgba(255,255,255,0.025);
  font-size: 13px;
  text-align: center;
}

:deep(.empty-list) {
  border: 1px dashed var(--border-card);
  border-radius: var(--radius-sm);
  padding: 14px;
  color: var(--text-muted);
  background: rgba(255,255,255,0.025);
  font-size: 13px;
  text-align: center;
}

.vehicle-panel {
  display: grid;
  gap: 10px;
}

.vehicle-state {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border: 1px solid var(--border-card);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  background: rgba(255,255,255,0.025);
}

.vehicle-state strong {
  color: var(--primary-color);
}

.modal-backdrop,
.countdown-screen {
  position: fixed;
  inset: 0;
  z-index: 3000;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(0, 0, 0, 0.58);
  backdrop-filter: blur(6px);
}

.modal-backdrop[style*="display: none"],
.countdown-screen[style*="display: none"] {
  pointer-events: none;
}

.gesture-manager {
  width: min(980px, calc(100vw - 32px));
  max-height: min(780px, calc(100vh - 48px));
  overflow: hidden;
  border: 1px solid var(--border-card);
  border-radius: var(--radius-lg);
  background: var(--bg-surface);
  box-shadow: var(--shadow-elevated);
}

.manager-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 18px;
  border-bottom: 1px solid var(--border-subtle);
  background: rgba(255,255,255,0.025);
}

.manager-body {
  display: grid;
  grid-template-columns: 340px minmax(0, 1fr);
  gap: 14px;
  max-height: calc(min(780px, 100vh - 48px) - 78px);
  overflow: auto;
  padding: 14px;
}

.manager-section {
  min-width: 0;
  border: 1px solid var(--border-card);
  border-radius: var(--radius-md);
  padding: 14px;
  background: var(--bg-card);
}

.record-section {
  align-self: start;
}

.countdown-screen {
  z-index: 3100;
}

.countdown-panel {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 180px;
  gap: 16px;
  align-items: stretch;
  width: min(780px, calc(100vw - 48px));
  border: 1px solid var(--border-card);
  border-radius: var(--radius-lg);
  padding: 16px;
  color: var(--text-primary);
  background: var(--bg-surface);
  box-shadow: var(--shadow-elevated);
}

.countdown-preview {
  position: relative;
  overflow: hidden;
  min-height: 280px;
  border-radius: var(--radius-md);
  background: #070b12;
  aspect-ratio: 16 / 9;
}

.countdown-badge {
  position: absolute;
  top: 12px;
  left: 12px;
  border: 1px solid rgba(0, 230, 118, 0.34);
  border-radius: 999px;
  padding: 6px 10px;
  color: var(--success-color);
  background: rgba(0, 0, 0, 0.62);
  font-size: 12px;
  font-weight: 800;
}

.countdown-info {
  display: grid;
  place-items: center;
  align-content: center;
  gap: 8px;
  min-width: 0;
  border-left: 1px solid var(--border-subtle);
  padding-left: 16px;
  text-align: center;
}

.countdown-info span {
  color: var(--text-secondary);
  font-size: 15px;
  font-weight: 800;
}

.countdown-info strong {
  font-size: 96px;
  line-height: 1;
  color: var(--primary-color);
  text-shadow: 0 0 28px var(--primary-glow);
}

.countdown-info p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.45;
}

@media (max-width: 1100px) {
  .owner-gesture-page {
    height: auto;
    min-height: 100%;
  }

  .layout {
    grid-template-columns: 1fr;
    flex: 0 0 auto;
    overflow: visible;
  }

  .side-panel {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .owner-gesture-page {
    height: auto;
    min-height: 100%;
  }

  .topbar {
    align-items: flex-start;
    flex-direction: column;
  }

  .top-actions {
    width: 100%;
    align-items: stretch;
    flex-direction: column-reverse;
  }

  h1 {
    font-size: 23px;
  }

  .video-shell {
    min-height: 240px;
  }

  .readout-grid,
  .side-panel {
    grid-template-columns: 1fr;
  }

  .mapping-item {
    grid-template-columns: 1fr;
  }

  :deep(.mapping-item) {
    grid-template-columns: 1fr;
  }

  .manager-body {
    grid-template-columns: 1fr;
  }

  .gesture-manager {
    width: calc(100vw - 24px);
    max-height: calc(100vh - 32px);
  }

  .countdown-screen {
    padding: 12px;
  }

  .countdown-panel {
    grid-template-columns: 1fr;
    width: 100%;
    gap: 12px;
    padding: 12px;
  }

  .countdown-preview {
    min-height: 0;
  }

  .countdown-info {
    border-left: 0;
    border-top: 1px solid rgba(226, 238, 233, 0.14);
    padding: 12px 0 0;
  }

  .countdown-info strong {
    font-size: 72px;
  }

  .readout {
    border-right: 0;
    border-bottom: 1px solid var(--border-subtle);
  }

  .readout:last-child {
    border-bottom: 0;
  }
}
</style>
