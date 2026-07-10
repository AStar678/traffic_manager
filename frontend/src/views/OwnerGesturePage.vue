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
            <h2>已录入动作</h2>
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
              <span id="sampleCount">0 / 105 帧</span>
            </div>
            <label>
              动作名称
              <input id="gestureNameInput" type="text" placeholder="例如：挥手返回主页" />
            </label>
            <div class="field-grid">
              <label>
                识别类型
                <span class="auto-kind-value" id="gestureKindStatus">自动判定</span>
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
            <p class="hint" id="recordHint">点击录入后会先倒数 3 秒，再采集 60 帧判断动态/静态，随后采集 45 帧保存手势。</p>
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
        <span>准备录入</span>
        <strong>{{ recordingCountdown }}</strong>
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
import { extractFeatureVector } from '@/utils/ownerGesturePrototype'
import { useVehicleStore } from '@/stores/vehicle'

const MODEL_PATH = '/models/gesture_recognizer.task'

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
let prototypes = []
let isRecording = false
let recognitionSocket
let serviceConfig
let shouldReconnectSocket = true
let controlSettings = []
let actionOptions = OWNER_GESTURE_ACTIONS
let countdownTimer

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
    overlay: find('#overlay'),
    cameraEmpty: find('#cameraEmpty'),
    startCameraBtn: find('#startCameraBtn'),
    stopCameraBtn: find('#stopCameraBtn'),
    manageGesturesBtn: find('#manageGesturesBtn'),
    prototypeMatch: find('#prototypeMatch'),
    similarityScore: find('#similarityScore'),
    triggerState: find('#triggerState'),
    gestureNameInput: find('#gestureNameInput'),
    gestureKindStatus: find('#gestureKindStatus'),
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
  mediaStream?.getTracks().forEach(track => track.stop())
  mediaStream = undefined
  if (els.webcam) {
    els.webcam.srcObject = null
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

  if (els.webcam.videoWidth && els.webcam.videoHeight) {
    resizeCanvas()
  }

  if (els.webcam.currentTime !== lastVideoTime) {
    lastVideoTime = els.webcam.currentTime
    const result = recognizer.recognizeForVideo(els.webcam, performance.now())
    drawResult(result)
    updateRecognition(result)
  }

  animationFrame = requestAnimationFrame(predictLoop)
}

function drawResult(result) {
  ctx.clearRect(0, 0, els.overlay.width, els.overlay.height)
  const landmarks = result.landmarks?.[0]
  if (!landmarks) return

  drawingUtils.drawConnectors(landmarks, GestureRecognizer.HAND_CONNECTIONS, {
    color: '#2f6f6b',
    lineWidth: 3
  })
  drawingUtils.drawLandmarks(landmarks, {
    color: '#d84f32',
    fillColor: '#f7f2ea',
    lineWidth: 1,
    radius: 4
  })
}

function updateRecognition(result) {
  const landmarks = result.landmarks?.[0]
  if (!landmarks) {
    els.prototypeMatch.textContent = prototypes.length ? 'unknown' : '未录入'
    els.similarityScore.textContent = '--'
    els.triggerState.textContent = '未检测到手'
    return
  }

  const vector = extractFeatureVector(landmarks, result.worldLandmarks?.[0])
  sendRecognitionFrame(vector)
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
        holdMs: Number(els.holdMsSelect.value)
      }
    })
    els.recordHint.textContent = recordingPhaseHint({ active: true, phase: 'detecting', detectCount: 0, detectTarget: warmupTarget() })
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
  return `点击录入后会先倒数 3 秒，再采集 ${warmupTarget()} 帧判断动态/静态，随后采集 ${sampleTarget()} 帧保存手势。`
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
    els.gestureKindStatus.textContent = isRecording ? kindLabel(state.recording.kind) : '自动判定'
    els.cancelRecordBtn.disabled = !isRecording
    updateRecordButton()
    if (isRecording) {
      els.recordHint.textContent = recordingPhaseHint(state.recording)
    }
  }

  if (state.recordingComplete) {
    els.recordHint.textContent = `已录入“${state.recordingComplete.name}”为${kindLabel(state.recordingComplete.kind)}。`
    els.gestureKindStatus.textContent = kindLabel(state.recordingComplete.kind)
    els.gestureNameInput.value = ''
    void loadControlSettings()
  }

  if (state.recognition) {
    const recognition = state.recognition
    els.prototypeMatch.textContent = recognition.name
    els.similarityScore.textContent =
      recognition.score === null || recognition.score === undefined
        ? recognition.motionLabel || '--'
        : `${recognition.score.toFixed(3)} · ${recognition.motionLabel}`
    els.triggerState.textContent = recognition.triggerState
    if (recognition.triggered) {
      void executeRecognizedGesture(recognition)
    }
  }

  if (state.vehicle) {
    syncVehiclePanel()
  }
}

function applyControlSettings(data = {}) {
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
  els.prototypeCount.textContent = `${prototypes.length} 个`
  if (!prototypes.length) {
    els.prototypeList.innerHTML = '<div class="empty-list">暂无动作，录入后会显示在这里。</div>'
    return
  }

  els.prototypeList.innerHTML = ''
  for (const prototype of prototypes) {
    const item = document.createElement('div')
    item.className = 'prototype-item'
    item.innerHTML = `
      <div>
        <strong>${escapeHtml(prototype.name)}</strong>
        <span>${kindLabel(prototype.kind)} · ${controlLabelForGesture(prototype)}</span>
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
      void deleteGesture(row.gestureCode)
    })
    els.gestureMappingList.append(item)
  }
}

async function deleteGesture(gestureCode) {
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
  if (kind === 'pending') return '自动判定中'
  return kind === 'dynamic' ? '动态轨迹' : '静态姿态'
}

function sampleTarget() {
  return serviceConfig?.sampleTarget || 45
}

function warmupTarget() {
  return serviceConfig?.recordingWarmupFrames || 60
}

function recordingProgressText(recording) {
  if (!recording?.active) {
    return `0 / ${warmupTarget() + sampleTarget()} 帧`
  }
  if (recording.phase === 'detecting') {
    return `判定 ${recording.detectCount ?? recording.count ?? 0} / ${recording.detectTarget ?? warmupTarget()} 帧`
  }
  return `采样 ${recording.sampleCount ?? recording.count ?? 0} / ${recording.sampleTarget ?? sampleTarget()} 帧`
}

function recordingPhaseHint(recording) {
  if (recording?.phase === 'detecting') {
    const count = recording.detectCount ?? 0
    const target = recording.detectTarget ?? warmupTarget()
    return `正在判断动态/静态：${count} / ${target} 帧。`
  }
  if (recording?.phase === 'sampling') {
    const count = recording.sampleCount ?? 0
    const target = recording.sampleTarget ?? sampleTarget()
    return `已判定为${kindLabel(recording.kind)}，正在采样建立原型：${count} / ${target} 帧。`
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
  min-height: calc(100vh - 48px - 72px - 32px);
  padding: 24px;
  color: #24302f;
  background: #f5f3ee;
  border-radius: 8px;
  font-family:
    Inter, "SF Pro Display", "PingFang SC", "Microsoft YaHei", system-ui, sans-serif;
  font-synthesis: none;
  text-rendering: optimizeLegibility;
  -webkit-font-smoothing: antialiased;
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
}

.owner-gesture-page button {
  min-height: 40px;
  border: 1px solid #c9d2cc;
  border-radius: 6px;
  padding: 0 14px;
  color: #22312f;
  background: #ffffff;
  cursor: pointer;
  transition:
    border-color 120ms ease,
    background 120ms ease,
    transform 120ms ease;
}

.owner-gesture-page button:hover:not(:disabled) {
  border-color: #7c9791;
  background: #f8fbf9;
}

.owner-gesture-page button:active:not(:disabled) {
  transform: translateY(1px);
}

.owner-gesture-page button:disabled {
  cursor: not-allowed;
  color: #8b9694;
  background: #ecefed;
}

.primary {
  border-color: #245c58;
  color: #ffffff;
  background: #245c58;
}

.primary:hover:not(:disabled) {
  border-color: #1b4945;
  background: #1b4945;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  max-width: 1440px;
  margin: 0 auto 18px;
}

.top-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.eyebrow {
  margin: 0 0 4px;
  color: #687673;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0;
  text-transform: uppercase;
}

h1,
h2,
h3 {
  margin: 0;
  letter-spacing: 0;
}

h1 {
  font-size: 28px;
  line-height: 1.2;
}

h2 {
  font-size: 17px;
  line-height: 1.35;
}

h3 {
  font-size: 16px;
  line-height: 1.35;
}

.status-pill {
  min-width: 112px;
  border: 1px solid #d7d1c5;
  border-radius: 999px;
  padding: 8px 12px;
  color: #7a5a25;
  background: #fff8e7;
  font-size: 13px;
  font-weight: 700;
  text-align: center;
}

.status-pill.ready {
  color: #245c58;
  background: #e8f5ef;
  border-color: #b8d7ce;
}

.status-pill.error {
  color: #9f321e;
  background: #fff0eb;
  border-color: #e7b7a9;
}

.layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 380px;
  gap: 18px;
  max-width: 1440px;
  margin: 0 auto;
}

.camera-panel,
.panel {
  border: 1px solid #d7ded9;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 8px 22px rgba(32, 40, 38, 0.06);
}

.camera-panel {
  min-width: 0;
  overflow: hidden;
}

.video-shell {
  position: relative;
  aspect-ratio: 16 / 9;
  min-height: 360px;
  background: #1f2928;
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

canvas {
  pointer-events: none;
}

.camera-empty {
  position: absolute;
  inset: 0;
  display: grid;
  place-content: center;
  gap: 8px;
  padding: 24px;
  color: #edf5f2;
  text-align: center;
  background:
    linear-gradient(rgba(31, 41, 40, 0.82), rgba(31, 41, 40, 0.82)),
    repeating-linear-gradient(45deg, #263330 0 14px, #22302d 14px 28px);
}

.camera-empty[hidden] {
  display: none;
}

.camera-empty strong {
  font-size: 22px;
}

.camera-empty span {
  color: #c8d6d2;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding: 14px;
  border-bottom: 1px solid #e4e8e5;
}

.readout-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  border-top: 1px solid #eef1ef;
}

.readout {
  min-width: 0;
  padding: 16px;
  border-right: 1px solid #eef1ef;
}

.readout:last-child {
  border-right: 0;
}

.readout span,
label,
.prototype-item span,
.vehicle-state span,
.hint {
  color: #66736f;
  font-size: 13px;
}

.readout strong {
  display: block;
  margin-top: 6px;
  overflow: hidden;
  color: #202b29;
  font-size: 18px;
  line-height: 1.25;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.side-panel {
  display: grid;
  gap: 14px;
  align-content: start;
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
  color: #6d7976;
  font-size: 13px;
  font-weight: 700;
}

.management-head {
  align-items: flex-start;
}

.compact-button {
  min-height: 34px;
  padding: 0 12px;
  font-size: 13px;
}

label {
  display: grid;
  gap: 7px;
  margin-bottom: 12px;
  font-weight: 700;
}

input[type="text"],
select,
.auto-kind-value {
  width: 100%;
  min-height: 40px;
  border: 1px solid #cbd5d0;
  border-radius: 6px;
  padding: 0 11px;
  color: #24302f;
  background: #ffffff;
}

.auto-kind-value {
  display: flex;
  align-items: center;
  color: #245c58;
  font-weight: 800;
}

input[type="text"]:focus,
select:focus,
button:focus-visible {
  outline: 3px solid rgba(47, 111, 107, 0.25);
  outline-offset: 2px;
}

input[type="range"] {
  width: 100%;
  accent-color: #245c58;
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
  border: 1px solid #e1e6e3;
  border-radius: 6px;
  padding: 10px;
  background: #fbfcfb;
}

.mapping-item.bound {
  border-color: #b8d7ce;
  background: #f3faf6;
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
  color: #66736f;
  font-size: 13px;
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
  border: 1px solid #e1e6e3;
  border-radius: 6px;
  padding: 10px;
  background: #fbfcfb;
}

:deep(.mapping-item.bound) {
  border-color: #b8d7ce;
  background: #f3faf6;
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
  color: #66736f;
  font-size: 13px;
}

:deep(.mapping-item select) {
  min-height: 36px;
}

:deep(.delete-gesture-button) {
  min-height: 36px;
  padding: 0 10px;
}

.prototype-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border: 1px solid #e1e6e3;
  border-radius: 6px;
  padding: 10px;
  background: #fbfcfb;
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
  border: 1px solid #e1e6e3;
  border-radius: 6px;
  padding: 10px;
  background: #fbfcfb;
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
  color: #66736f;
  font-size: 13px;
}

:deep(.prototype-item button) {
  min-height: 34px;
  padding: 0 10px;
}

.empty-list {
  border: 1px dashed #cbd5d0;
  border-radius: 6px;
  padding: 14px;
  color: #65716e;
  background: #fbfcfb;
  font-size: 14px;
  text-align: center;
}

:deep(.empty-list) {
  border: 1px dashed #cbd5d0;
  border-radius: 6px;
  padding: 14px;
  color: #65716e;
  background: #fbfcfb;
  font-size: 14px;
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
  border: 1px solid #e1e6e3;
  border-radius: 6px;
  padding: 10px 12px;
  background: #fbfcfb;
}

.vehicle-state strong {
  color: #245c58;
}

.modal-backdrop,
.countdown-screen {
  position: fixed;
  inset: 0;
  z-index: 3000;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(14, 21, 20, 0.58);
}

.modal-backdrop[style*="display: none"],
.countdown-screen[style*="display: none"] {
  pointer-events: none;
}

.gesture-manager {
  width: min(980px, calc(100vw - 32px));
  max-height: min(780px, calc(100vh - 48px));
  overflow: hidden;
  border: 1px solid #d7ded9;
  border-radius: 8px;
  background: #f7f6f1;
  box-shadow: 0 24px 80px rgba(9, 17, 15, 0.28);
}

.manager-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 18px;
  border-bottom: 1px solid #dde4df;
  background: #ffffff;
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
  border: 1px solid #d7ded9;
  border-radius: 8px;
  padding: 14px;
  background: #ffffff;
}

.record-section {
  align-self: start;
}

.countdown-screen {
  z-index: 3100;
}

.countdown-panel {
  display: grid;
  place-items: center;
  width: min(360px, calc(100vw - 48px));
  min-height: 260px;
  border: 1px solid rgba(226, 238, 233, 0.24);
  border-radius: 8px;
  color: #f5fbf8;
  background: #172321;
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.34);
}

.countdown-panel span {
  color: #b8c9c3;
  font-size: 15px;
  font-weight: 800;
}

.countdown-panel strong {
  font-size: 96px;
  line-height: 1;
}

@media (max-width: 1100px) {
  .layout {
    grid-template-columns: 1fr;
  }

  .side-panel {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .owner-gesture-page {
    min-height: calc(100dvh - 48px - 72px - 24px);
    padding: 14px;
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

  .readout {
    border-right: 0;
    border-bottom: 1px solid #eef1ef;
  }

  .readout:last-child {
    border-bottom: 0;
  }
}
</style>
