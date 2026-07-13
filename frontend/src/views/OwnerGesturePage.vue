<template>
  <div ref="pageRef" class="owner-gesture-page">
    <header class="topbar">
      <div>
        <p class="eyebrow">Owner Gesture Control</p>
        <h1>车主手势控车原型网络</h1>
      </div>
      <div class="top-actions">
        <div class="algorithm-badge" aria-label="当前手势识别算法">
          <span>DINOv2-S</span>
          <strong>TCN 视频原型</strong>
        </div>
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
            <strong>{{ cameraEmptyTitle }}</strong>
            <span>{{ cameraEmptyDescription }}</span>
          </div>
          <div class="viewport-top">
            <span class="chip" :class="{ live: cameraActive }">{{ cameraActive ? '● LIVE' : '○ CAMERA' }}</span>
            <span class="chip">车内摄像头</span>
            <span v-if="cameraActive" class="chip tracking">RGB + 21 点手部特征</span>
          </div>
        </div>

        <div class="toolbar">
          <button v-if="!props.embedded" class="primary" id="startCameraBtn" type="button" @click="startCamera">启动摄像头</button>
          <button v-if="!props.embedded" id="stopCameraBtn" type="button" disabled @click="stopCamera">停止</button>
          <button
            v-if="props.embedded"
            class="primary"
            type="button"
            :disabled="cameraActive || cameraStarting"
            @click="startCamera"
          >{{ cameraButtonText }}</button>
          <button id="manageGesturesBtn" type="button" @click="openManagementDialog">手势管理</button>
        </div>

        <div class="readout-grid">
          <div class="readout">
            <span>视频原型匹配</span>
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
            <h2>用户手势库</h2>
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
              <span id="sampleCount">0 / 12 帧</span>
            </div>
            <div class="record-preview" :class="{ active: cameraActive }">
              <video id="managementWebcam" autoplay playsinline muted></video>
              <div v-if="!cameraActive" class="record-preview-empty">
                <strong>{{ cameraStarting ? '正在打开摄像头' : '等待摄像头' }}</strong>
                <span>{{ cameraError || '打开管理面板后将自动启动预览' }}</span>
              </div>
              <span class="record-preview-status">{{ recordingActive ? '● 正在采样' : (cameraActive ? '● 实时预览' : '○ 待机') }}</span>
            </div>
            <label>
              动作名称
              <input id="gestureNameInput" type="text" placeholder="例如：挥手返回主页" />
            </label>
            <label>
              触发持续时间
              <select id="holdMsSelect">
                <option value="900">0.9 秒</option>
                <option value="1200" selected>1.2 秒</option>
                <option value="1800">1.8 秒</option>
              </select>
            </label>
            <div class="button-row">
              <button class="primary" id="recordBtn" type="button" disabled @click="startCountdownRecording">录入新手势</button>
              <button id="cancelRecordBtn" type="button" disabled @click="stopRecording">取消录入</button>
            </div>
            <p class="hint" id="recordHint">录制一段短视频，由 DINOv2-S 与手部几何特征共同生成视频原型。</p>
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
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { DrawingUtils, FilesetResolver, GestureRecognizer } from '@/vendor/tasks-vision/vision_bundle.mjs'
import {
  cancelOwnerGestureRecording,
  deleteOwnerGesturePrototype,
  executeOwnerGestureControl,
  getOwnerGestureControlSettings,
  getOwnerGestureData,
  getOwnerGestureState,
  recognizeOwnerGesture,
  startOwnerGestureRecording,
  saveOwnerGestureControlSettings
} from '@/api/ownerGestures'
import { OWNER_GESTURE_ACTIONS } from '@/utils/constants'
import { buildVideoPrototypePayload } from '@/utils/ownerGestureVideoPrototype'
import { announceOwnerGestureAction } from '@/utils/speechAnnouncements'
import { useVehicleStore } from '@/stores/vehicle'

const props = defineProps({
  embedded: { type: Boolean, default: false },
  openManagementOnMount: { type: Boolean, default: false }
})

const MODEL_PATH = '/models/gesture_recognizer.task'
const DEFAULT_HOLD_MS = 1200
const DEFAULT_SAMPLE_TARGET = 12
const VIDEO_GESTURE_KIND = 'dynamic'

const pageRef = ref(null)
const vehicleStore = useVehicleStore()
const isManagementOpen = ref(false)
const isCountdownOpen = ref(false)
const recordingActive = ref(false)
const recordingCountdown = ref(3)
const cameraActive = ref(false)
const cameraStarting = ref(false)
const cameraError = ref('')

const cameraButtonText = computed(() => {
  if (cameraStarting.value) return '正在打开电脑摄像头'
  if (cameraActive.value) return '电脑摄像头已自动打开'
  return cameraError.value ? '重新打开电脑摄像头' : '打开电脑摄像头'
})
const cameraEmptyTitle = computed(() => {
  if (cameraStarting.value) return '正在请求电脑摄像头权限'
  if (cameraError.value) return '电脑摄像头启动失败'
  return '摄像头未启动'
})
const cameraEmptyDescription = computed(() => {
  if (cameraError.value) return cameraError.value
  if (props.embedded) return '详情打开后会自动启动，并实时显示 21 点手部关键点'
  return '点击“启动摄像头”后开始录入或识别动作'
})

defineExpose({ openManagementDialog })

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
let serviceConfig
let serviceConnected = false
let recognitionRequestPending = false
let controlSettings = []
let actionOptions = OWNER_GESTURE_ACTIONS
let countdownTimer
let lastRecognizedGestureDisplay
let recordingGestureName = ''

onMounted(async () => {
  await nextTick()
  bindElements()
  if (props.openManagementOnMount) openManagementDialog()
  await init()
})

onBeforeUnmount(() => {
  window.clearInterval(countdownTimer)
  stopCamera()
})

function bindElements() {
  const root = pageRef.value
  const find = selector => root.querySelector(selector)
  els = {
    modelStatus: find('#modelStatus'),
    webcam: find('#webcam'),
    managementWebcam: find('#managementWebcam'),
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

  try {
    const vision = await FilesetResolver.forVisionTasks('/wasm')
    recognizer = await createRecognizer(vision)
    syncAlgorithmStatus()
    updateRecordButton()
    if (props.embedded) await startCamera()
  } catch (error) {
    console.error(error)
    els.modelStatus.textContent = '模型加载失败'
    els.modelStatus.classList.add('error')
    els.recordHint.textContent = '请确认已安装依赖并通过本地服务器访问页面。'
  }
}

async function loadServiceState() {
  try {
    applyServiceState(getOwnerGestureData(await getOwnerGestureState()))
    serviceConnected = true
    syncAlgorithmStatus()
  } catch (error) {
    console.error(error)
    serviceConnected = false
    syncAlgorithmStatus()
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

async function startCamera() {
  if (mediaStream) {
    await syncManagementPreview()
    cameraActive.value = true
    predictLoop()
    return true
  }
  cameraStarting.value = true
  cameraError.value = ''
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'user' },
      audio: false
    })
    els.webcam.srcObject = mediaStream
    if (els.countdownWebcam) {
      els.countdownWebcam.srcObject = mediaStream
    }
    if (els.managementWebcam) {
      els.managementWebcam.srcObject = mediaStream
    }
    await els.webcam.play()
    await syncManagementPreview()
    resizeCanvas()
    els.cameraEmpty.hidden = true
    cameraActive.value = true
    if (els.startCameraBtn) els.startCameraBtn.disabled = true
    if (els.stopCameraBtn) els.stopCameraBtn.disabled = false
    updateRecordButton()
    predictLoop()
    return true
  } catch (error) {
    console.error(error)
    cameraActive.value = false
    cameraError.value = '请在浏览器地址栏允许摄像头权限，然后点击重新打开。'
    els.recordHint.textContent = `摄像头启动失败：${cameraError.value}`
    return false
  } finally {
    cameraStarting.value = false
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
  recognitionRequestPending = false
  mediaStream?.getTracks().forEach(track => track.stop())
  mediaStream = undefined
  cameraActive.value = false
  if (els.webcam) {
    els.webcam.srcObject = null
  }
  if (els.countdownWebcam) {
    els.countdownWebcam.srcObject = null
  }
  if (els.managementWebcam) {
    els.managementWebcam.srcObject = null
  }
  if (ctx && els.overlay) {
    ctx.clearRect(0, 0, els.overlay.width, els.overlay.height)
  }
  if (els.cameraEmpty) {
    els.cameraEmpty.hidden = false
    if (els.startCameraBtn) els.startCameraBtn.disabled = false
    if (els.stopCameraBtn) els.stopCameraBtn.disabled = true
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
    if (now - lastPredictFrameAt < gestureFrameInterval()) {
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
    restoreLastRecognizedGestureDisplay()
    els.triggerState.textContent = '未检测到手'
    return
  }

  void sendRecognitionFrame(result)
}

async function openManagementDialog() {
  isManagementOpen.value = true
  renderPrototypes()
  renderGestureMappings()
  await nextTick()
  if (!mediaStream) {
    await startCamera()
  } else {
    await syncManagementPreview()
  }
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

async function syncManagementPreview() {
  if (!els.managementWebcam || !mediaStream) return
  if (els.managementWebcam.srcObject !== mediaStream) {
    els.managementWebcam.srcObject = mediaStream
  }
  try {
    await els.managementWebcam.play()
  } catch (error) {
    console.warn('Management camera preview could not autoplay.', error)
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
    recordingGestureName = name
    const state = getOwnerGestureData(await startOwnerGestureRecording({
      name,
      kind: VIDEO_GESTURE_KIND,
      holdMs: Number(els.holdMsSelect.value)
    }))
    els.recordHint.textContent = recordingPhaseHint({
      active: true,
      phase: 'sampling',
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
    applyServiceState(getOwnerGestureData(await cancelOwnerGestureRecording()))
  } catch (error) {
    console.error(error)
  } finally {
    recordingGestureName = ''
    if (!options.keepHint) {
      els.recordHint.textContent = recordingHint()
    }
  }
}

function recordingHint() {
  return `录入将采集 ${sampleTarget()} 帧 RGB 视频与手部几何特征，不使用系统预设手势。`
}

async function sendRecognitionFrame(result) {
  if (recognitionRequestPending) return
  const videoPayload = buildVideoPrototypePayload(els.webcam, result)
  if (!videoPayload) return
  recognitionRequestPending = true
  try {
    const state = getOwnerGestureData(await recognizeOwnerGesture({ type: 'frame', ...videoPayload }))
    serviceConnected = true
    applyServiceState(state)
    if (isRecording) {
      await loadServiceState()
    }
  } catch (error) {
    console.error(error)
    serviceConnected = false
    syncAlgorithmStatus()
    els.triggerState.textContent = '识别服务未连接'
  } finally {
    recognitionRequestPending = false
  }
}

function gestureFrameInterval() {
  const configured = Number(serviceConfig?.dinov2FrameIntervalMs)
  return Number.isFinite(configured) && configured >= 80 ? configured : 150
}

function applyServiceState(state) {
  if (!state) return
  syncAlgorithmStatus()
  if (state.config) {
    serviceConfig = state.config
  }

  if (state.prototypes) {
    prototypes = state.prototypes
    renderPrototypes()
    renderGestureMappings()
  }

  if (state.recording) {
    const wasRecording = isRecording
    isRecording = state.recording.active
    recordingActive.value = isRecording
    els.sampleCount.textContent = recordingProgressText(state.recording)
    els.cancelRecordBtn.disabled = !isRecording
    updateRecordButton()
    if (isRecording) {
      els.recordHint.textContent = recordingPhaseHint(state.recording)
    } else if (wasRecording && recordingGestureName) {
      els.recordHint.textContent = `已完成“${recordingGestureName}”的 DINOv2 视频原型录入。`
      els.gestureNameInput.value = ''
      recordingGestureName = ''
      void loadControlSettings()
    }
  }

  if (state.recordingComplete) {
    els.recordHint.textContent = `已完成“${state.recordingComplete.name}”的 DINOv2 视频原型录入。`
    els.gestureNameInput.value = ''
    void loadControlSettings()
  }

  if (state.recognition) {
    const recognition = state.recognition
    const scoreText =
      recognition.score === null || recognition.score === undefined
        ? recognition.motionLabel || '--'
        : formatGestureScore(recognition.score)
    const recognized = recognition.accepted && rememberRecognizedGestureDisplay(recognition.name, scoreText)

    if (!recognized) {
      restoreLastRecognizedGestureDisplay()
    }
    els.triggerState.textContent = recognition.triggerState || '识别中'
    if (recognition.triggered) {
      void executeRecognizedGesture(recognition)
    }
  }

  if (state.vehicle) {
    syncVehiclePanel()
  }
}

function syncAlgorithmStatus() {
  if (!els.modelStatus) return
  const ready = Boolean(recognizer && serviceConnected)
  els.modelStatus.textContent = ready ? 'DINOv2-TCN 已就绪' : '识别服务未就绪'
  els.modelStatus.classList.toggle('error', !ready)
  els.modelStatus.classList.toggle('ready', ready)
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
        <span>用户视频原型 · ${row.enabled ? escapeHtml(row.actionLabel) : '未关联控制'}</span>
      </div>
      <button type="button">管理</button>
    `
    item.querySelector('button').addEventListener('click', openManagementDialog)
    els.prototypeList.append(item)
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
        <span>用户视频原型</span>
      </div>
      <select aria-label="关联 ${escapeHtml(row.gestureName)} 到车辆功能" data-gesture-code="${escapeHtml(row.gestureCode)}">
        ${actionOptionsHtml(row.actionType)}
      </select>
      <button class="delete-gesture-button" type="button">删除</button>
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
  const gestureCode = row?.gestureCode
  if (!gestureCode) return
  try {
    applyServiceState(getOwnerGestureData(await deleteOwnerGesturePrototype(gestureCode)))
    await loadControlSettings()
    ElMessage.success('手势已删除')
  } catch (error) {
    console.error(error)
  }
}

function gestureManagementRows() {
  const settingsByCode = new Map(
    controlSettings.map(setting => [String(setting.gestureCode || ''), setting])
  )
  return prototypes.map(prototype => {
    const gestureCode = prototype.id || prototype.gestureCode || prototype.name
    const setting = settingsByCode.get(String(gestureCode)) || {}
    const actionType = setting.actionType || 'NONE'
    return {
      gestureCode: String(gestureCode),
      gestureName: prototype.name || prototype.gestureName || String(gestureCode),
      gestureKind: prototype.kind || VIDEO_GESTURE_KIND,
      gestureSource: 'custom',
      holdMs: positiveMs(setting.holdMs, positiveMs(prototype.holdMs, positiveMs(serviceConfig?.defaultHoldMs, DEFAULT_HOLD_MS))),
      actionType,
      actionLabel: setting.actionLabel || actionLabel(actionType),
      enabled: Boolean(setting.enabled) && actionType !== 'NONE'
    }
  })
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
    gestureSource: 'custom',
    holdMs: positiveMs(row.holdMs, positiveMs(serviceConfig?.defaultHoldMs, DEFAULT_HOLD_MS)),
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
    announceOwnerGestureAction(control.actionLabel)
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

function sampleTarget() {
  return serviceConfig?.sampleTarget || DEFAULT_SAMPLE_TARGET
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
    return `正在录入视频原型：${count} / ${target} 帧。`
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

.algorithm-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 42px;
  padding: 4px 12px 4px 5px;
  border: 1px solid var(--border-card);
  border-radius: 14px;
  background: var(--bg-surface);
}

.algorithm-badge span {
  display: grid;
  place-items: center;
  min-height: 32px;
  border-radius: 9px;
  padding: 0 11px;
  color: var(--primary-color);
  background: var(--primary-soft);
  box-shadow: inset 0 0 0 1px var(--border-active);
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
}

.algorithm-badge strong {
  color: var(--text-secondary);
  font-size: 12px;
  white-space: nowrap;
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

.chip.tracking {
  color: var(--success-color);
  border-color: rgba(0, 230, 118, 0.35);
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

.record-preview {
  position: relative;
  overflow: hidden;
  width: 100%;
  margin-bottom: 14px;
  border: 1px solid var(--border-card);
  border-radius: var(--radius-sm);
  background: #070b12;
  aspect-ratio: 16 / 9;
}

.record-preview.active {
  border-color: rgba(0, 230, 118, 0.3);
}

.record-preview video {
  z-index: 1;
}

.record-preview-empty {
  position: absolute;
  z-index: 2;
  inset: 0;
  display: grid;
  place-content: center;
  gap: 5px;
  padding: 18px;
  text-align: center;
  background:
    linear-gradient(90deg, rgba(255,255,255,0.018) 1px, transparent 1px),
    linear-gradient(rgba(255,255,255,0.018) 1px, transparent 1px);
  background-size: 28px 28px;
}

.record-preview-empty strong {
  color: var(--text-secondary);
  font-size: 14px;
}

.record-preview-empty span {
  color: var(--text-muted);
  font-size: 11px;
  line-height: 1.45;
}

.record-preview-status {
  position: absolute;
  z-index: 3;
  top: 9px;
  left: 9px;
  border: 1px solid rgba(0, 230, 118, 0.32);
  border-radius: 999px;
  padding: 5px 8px;
  color: var(--success-color);
  background: rgba(0, 0, 0, 0.64);
  font-size: 11px;
  font-weight: 800;
  backdrop-filter: blur(6px);
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

  .algorithm-badge {
    justify-content: center;
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
