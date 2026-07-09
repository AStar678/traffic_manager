<template>
  <div class="owner-page">
    <!-- 主画面：车内摄像头 + 手势叠加 -->
    <div class="viewport-area">
      <div class="viewport">
        <img v-if="viewportImageUrl" :src="viewportImageUrl" alt="cockpit" />
        <div v-else class="viewport-placeholder">
          <el-icon :size="48"><Pointer /></el-icon>
          <span>车内摄像头待机</span>
        </div>

        <div class="viewport-top">
          <span class="chip live">● LIVE</span>
          <span class="chip">{{ cameraLabel }}</span>
        </div>

        <!-- 手部关键点叠加 -->
        <svg class="hand-overlay" viewBox="0 0 1200 720" preserveAspectRatio="none" v-if="result.detections.length">
          <g v-for="hand in result.detections" :key="hand.objectId">
            <line v-for="(pair, i) in handBones" :key="i"
              :x1="getKp(hand, pair[0]).x" :y1="getKp(hand, pair[0]).y"
              :x2="getKp(hand, pair[1]).x" :y2="getKp(hand, pair[1]).y"
              stroke="rgba(0,180,216,0.8)" stroke-width="3" stroke-linecap="round"
            />
            <circle v-for="kp in hand.keypoints" :key="kp.name"
              :cx="kp.x" :cy="kp.y" r="5"
              fill="#00b4d8" stroke="#080c14" stroke-width="2"
            />
          </g>
        </svg>

        <!-- 手势标签 -->
        <div class="gesture-tag" v-if="gesture">
          <span class="gesture-icon">{{ gestureIcon }}</span>
          <span>{{ gesture.name }} → {{ gesture.action }}</span>
        </div>
      </div>

      <!-- 触发状态 -->
      <div class="trigger-bar">
        <div v-for="item in triggerItems" :key="item.label" class="trigger-item" :class="{ ok: item.ok }">
          <span>{{ item.label }}</span>
          <strong :class="{ pass: item.ok }">{{ item.value }}</strong>
        </div>
      </div>
    </div>

    <!-- 右侧面板 -->
    <div class="side-panel">
      <div class="card">
        <div class="mode-tabs">
          <button
            :class="{ active: inputMode === 'image' }"
            @click="setInputMode('image')"
          >图片识别</button>
          <button
            :class="{ active: inputMode === 'video' }"
            @click="setInputMode('video')"
          >虚拟摄像头</button>
        </div>

        <div v-if="inputMode === 'image'" class="upload-zone" @click="triggerUpload">
          <input ref="fileInput" type="file" accept=".jpg,.jpeg,.png,.bmp" style="display:none" @change="onFileSelected">
          <el-icon :size="28"><UploadFilled /></el-icon>
          <span>上传车内手势图片</span>
          <small>{{ selectedFileName || 'jpg / png / bmp · ≤ 10MB' }}</small>
        </div>

        <div v-if="inputMode === 'video'" class="camera-source">
          <label>虚拟摄像头源</label>
          <el-select
            v-model="selectedCameraSourceId"
            style="width:100%"
            :loading="cameraStatus === 'loading'"
            @change="activateCameraSource"
          >
            <el-option
              v-for="source in cameraSources"
              :key="source.id"
              :label="source.name"
              :value="source.id"
            />
          </el-select>
          <div class="camera-meta">
            <span class="source-kind">{{ selectedCameraSource?.sourceType || '--' }}</span>
            <span :class="['status-dot', cameraStatus]">{{ cameraError || cameraStatusText }}</span>
          </div>
          <button class="action-btn secondary compact" @click="refreshCameraPreview">刷新预览</button>
        </div>

        <button class="action-btn primary" :disabled="loading" @click="runInference">
          <el-icon v-if="loading" class="spinner"><Loading /></el-icon>
          {{ loading ? '识别中...' : (inputMode === 'image' ? '上传并识别' : '抓拍并识别') }}
        </button>
      </div>

      <!-- 手势指令显示 -->
      <div class="card gesture-hero" :class="{ active: result.detections.length }">
        <div class="gesture-code">{{ gestureCode }}</div>
        <strong>{{ gesture?.name || '等待手势' }}</strong>
        <p>{{ gesture?.action || '—' }}</p>
      </div>

      <!-- 车辆控制面板 -->
      <div class="card">
        <h3 class="card-title">车辆控制反馈</h3>

        <div class="control-item" :class="{ highlight: gesture?.action === '调节音量' }">
          <div class="control-head">
            <el-icon><Headset /></el-icon>
            <span>音量</span>
            <strong>{{ controlState.volume }}%</strong>
          </div>
          <el-slider v-model="controlState.volume" />
        </div>

        <div class="control-item" :class="{ highlight: gesture?.action === '切换功能' }">
          <div class="control-head">
            <el-icon><Sunny /></el-icon>
            <span>空调</span>
            <strong>{{ controlState.temperature }}°C</strong>
          </div>
          <el-slider v-model="controlState.temperature" :min="16" :max="30" />
        </div>

        <div class="mode-btns">
          <button
            v-for="m in modes" :key="m"
            :class="{ active: controlState.mode === m }"
            @click="controlState.mode = m"
          >{{ m }}</button>
        </div>

        <div class="phone-btns">
          <el-button
            :type="gesture?.action === '接听电话' ? 'success' : 'default'"
            @click="triggerAction('接听电话')"
          >接听</el-button>
          <el-button
            :type="gesture?.action === '挂断电话' ? 'danger' : 'default'"
            @click="triggerAction('挂断电话')"
          >挂断</el-button>
        </div>
      </div>

      <!-- 手势映射表 -->
      <div class="card">
        <h3 class="card-title">手势映射</h3>
        <div class="mapping-list">
          <div v-for="(item, code) in OWNER_MAP" :key="code" class="mapping-item" :class="{ active: code === gestureCode }">
            <strong>{{ code }}</strong>
            <div>
              <span>{{ item.name }}</span>
              <small>{{ item.action }}</small>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { OWNER_GESTURE_MAP, TASK_TYPES } from '@/utils/constants'
import { uploadImage } from '@/api/files'
import { getInferenceData, inferenceImage } from '@/api/inference'
import { useCameraSource } from '@/composables/useCameraSource'

const result = ref(emptyResult())
const OWNER_MAP = OWNER_GESTURE_MAP
const loading = ref(false)
const inputMode = ref('video')
const fileInput = ref(null)
const selectedFile = ref(null)
const selectedFileName = ref('')
const {
  cameraSources,
  selectedCameraSourceId,
  selectedCameraSource,
  cameraStatus,
  cameraError,
  cameraStreamUrl,
  activateCameraSource,
  refreshCameraPreview,
  getCameraSnapshotUrl
} = useCameraSource(TASK_TYPES.OWNER_GESTURE)

const gestureCode = computed(() => result.value.detections[0]?.gestureCode || '--')
const gesture = computed(() => OWNER_MAP[gestureCode.value] || null)
const viewportImageUrl = computed(() => result.value.annotatedImageUrl || cameraStreamUrl.value)
const cameraLabel = computed(() => {
  if (result.value.annotatedImageUrl && inputMode.value === 'image') return selectedFileName.value || '图片输入'
  return selectedCameraSource.value?.name || '虚拟摄像头'
})
const cameraStatusText = computed(() => {
  const labels = { idle: '未连接', loading: '连接中', ready: '已连接', empty: '无可用源', offline: '服务离线' }
  return labels[cameraStatus.value] || cameraStatus.value
})

const gestureIcon = computed(() => {
  const icons = { '001': '✋', '002': '✊', '003': '👆', '004': '👈', '005': '👍', '006': '👎', '007': '👋' }
  return icons[gestureCode.value] || '🖐'
})

const controlState = reactive({ volume: 42, temperature: 24, mode: '音乐' })
const modes = ['音乐', '导航', '电话', '空调']

const triggerItems = computed(() => {
  const detection = result.value.detections[0]
  const confidence = detection?.confidence || 0
  return [
    { label: '输入状态', value: detection ? '已检测到手部' : '等待图片', ok: Boolean(detection) },
    { label: '置信度', value: detection ? `${Math.round(confidence * 100)}%` : '--', ok: confidence >= 0.6 },
    { label: '控制反馈', value: result.value.vehicleControl?.triggered ? '已触发控制反馈' : '未触发', ok: Boolean(result.value.vehicleControl?.triggered) }
  ]
})

const handBones = [
  ['wrist','thumb_tip'],['wrist','index_finger_tip'],['wrist','middle_finger_tip'],
  ['wrist','ring_finger_tip'],['wrist','pinky_tip']
]

function getKp(hand, name) {
  return hand.keypoints?.find(k => k.name === name) || { x: 0, y: 0 }
}

function triggerAction(action) {
  // mock触发
}

function setInputMode(mode) {
  inputMode.value = mode
  result.value = emptyResult()
  refreshCameraPreview()
}

function triggerUpload() {
  fileInput.value?.click()
}

function onFileSelected(event) {
  const file = event.target.files?.[0]
  if (!file) return
  selectedFile.value = file
  selectedFileName.value = file.name
  result.value = {
    ...emptyResult(),
    annotatedImageUrl: URL.createObjectURL(file)
  }
  ElMessage.success(`已选择：${file.name}`)
}

async function runInference() {
  if (inputMode.value === 'image' && !selectedFile.value) {
    ElMessage.warning('请先选择一张车内手势图片')
    return
  }
  if (inputMode.value === 'video' && !selectedCameraSourceId.value) {
    ElMessage.warning('请先选择一个虚拟摄像头源')
    return
  }
  loading.value = true
  try {
    let imageUrl
    if (inputMode.value === 'image') {
      const uploaded = await uploadImage(selectedFile.value)
      imageUrl = uploaded.data?.url
    } else {
      const connected = await activateCameraSource()
      if (!connected) throw new Error('摄像头源连接失败')
      imageUrl = getCameraSnapshotUrl()
    }
    const response = await inferenceImage(TASK_TYPES.OWNER_GESTURE, imageUrl)
    result.value = getInferenceData(response)
    applyVehicleControl(result.value.vehicleControl)
    ElMessage.success('识别完成')
  } catch (error) {
    console.error(error)
    ElMessage.error('识别失败，请检查后端和算法服务是否已启动')
  } finally {
    loading.value = false
  }
}

function applyVehicleControl(vehicleControl) {
  const action = vehicleControl?.action
  if (action === '调节音量') controlState.volume = Math.min(100, controlState.volume + 8)
  if (action === '切换功能') controlState.mode = modes[(modes.indexOf(controlState.mode) + 1) % modes.length]
  if (action === '接听电话') controlState.mode = '电话'
  if (action === '挂断电话') controlState.mode = '音乐'
}

function emptyResult() {
  return {
    taskType: TASK_TYPES.OWNER_GESTURE,
    latencyMs: 0,
    image: { width: 1200, height: 720 },
    detections: [],
    detectionCount: 0,
    annotatedImageUrl: '',
    vehicleControl: null
  }
}
</script>

<style scoped>
.owner-page {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: 16px;
  height: 100%;
}

.viewport-area { display: flex; flex-direction: column; gap: 12px; }

.viewport {
  position: relative;
  flex: 1;
  min-height: 360px;
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: #080c14;
}

.viewport img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  opacity: 0.88;
  background: #070b12;
}

.viewport-placeholder {
  height: 100%;
  min-height: 360px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--text-muted);
  background:
    linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px),
    linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px);
  background-size: 40px 40px;
}

.hand-overlay {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.viewport-top {
  position: absolute;
  top: 14px;
  left: 16px;
  display: flex;
  gap: 8px;
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
  border-color: rgba(255,61,0,0.4);
}

.gesture-tag {
  position: absolute;
  bottom: 18px;
  left: 18px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: rgba(0,180,216,0.18);
  border: 1px solid rgba(0,180,216,0.3);
  border-radius: 999px;
  font-size: 14px;
  font-weight: 700;
  color: var(--primary-color);
  backdrop-filter: blur(8px);
}

.gesture-icon { font-size: 20px; }

.trigger-bar {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.trigger-item {
  padding: 12px 16px;
  background: var(--bg-card);
  border: 1px solid var(--border-card);
  border-radius: var(--radius-sm);
}

.trigger-item.ok {
  border-color: rgba(0,230,118,0.2);
  background: rgba(0,230,118,0.04);
}

.trigger-item span {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 600;
}

.trigger-item strong {
  display: block;
  margin-top: 4px;
  font-size: 14px;
  color: var(--text-primary);
}

.trigger-item strong.pass { color: var(--success-color); }

/* 右侧 */
.side-panel { display: flex; flex-direction: column; gap: 14px; overflow-y: auto; }

.card-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 14px;
}

.mode-tabs {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
  margin-bottom: 16px;
}

.mode-tabs button {
  padding: 10px;
  border: 1px solid var(--border-card);
  border-radius: 10px;
  background: transparent;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--duration-fast);
}

.mode-tabs button.active {
  border-color: var(--primary-color);
  background: var(--primary-soft);
  color: var(--primary-color);
}

.upload-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 22px;
  border: 1px dashed rgba(255,255,255,0.10);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--duration-fast);
}

.upload-zone:hover {
  border-color: var(--border-active);
  background: rgba(255,255,255,0.02);
}

.upload-zone .el-icon { color: var(--text-muted); }
.upload-zone span { font-size: 13px; font-weight: 600; }
.upload-zone small { font-size: 11px; color: var(--text-muted); text-align: center; }

.camera-source {
  margin-top: 2px;
}

.camera-source label {
  display: block;
  margin-bottom: 6px;
  font-size: 11px;
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
}

.camera-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 10px;
  font-size: 11px;
  color: var(--text-muted);
}

.source-kind {
  padding: 4px 8px;
  border: 1px solid var(--border-card);
  border-radius: 999px;
  text-transform: uppercase;
}

.status-dot.ready { color: var(--success-color); }
.status-dot.loading { color: var(--warning-color); }
.status-dot.offline,
.status-dot.empty { color: var(--danger-color); }

.action-btn {
  width: 100%;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 14px;
  border: none;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: all var(--duration-fast);
}

.action-btn.primary {
  background: linear-gradient(135deg, var(--primary-color), #0096c7);
  color: #080c14;
  box-shadow: 0 4px 18px var(--primary-glow);
}

.action-btn.primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.action-btn.secondary {
  background: transparent;
  border: 1px solid var(--border-card);
  color: var(--text-secondary);
}

.action-btn.secondary:hover {
  border-color: var(--border-active);
  color: var(--text-primary);
}

.action-btn.compact {
  height: 36px;
  margin-top: 10px;
  font-size: 12px;
}

.gesture-hero {
  text-align: center;
  padding: 24px;
}

.gesture-hero.active {
  border-color: rgba(0,180,216,0.35);
  box-shadow: 0 0 24px var(--primary-glow);
}

.gesture-code {
  font-family: "SF Mono", "Consolas", monospace;
  font-size: 48px;
  font-weight: 800;
  color: var(--text-muted);
}

.gesture-hero.active .gesture-code {
  color: var(--primary-color);
  text-shadow: 0 0 16px var(--primary-glow);
}

.gesture-hero strong {
  display: block;
  margin-top: 8px;
  font-size: 20px;
  color: var(--text-primary);
}

.gesture-hero p {
  margin-top: 4px;
  font-size: 13px;
  color: var(--text-secondary);
}

.control-item {
  padding: 14px;
  background: rgba(255,255,255,0.02);
  border-radius: var(--radius-sm);
  margin-bottom: 10px;
  border: 1px solid transparent;
  transition: all var(--duration-fast);
}

.control-item.highlight {
  border-color: var(--primary-color);
  background: var(--primary-soft);
}

.control-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
  font-size: 13px;
  color: var(--text-secondary);
}

.control-head strong {
  margin-left: auto;
  color: var(--primary-color);
  font-size: 16px;
}

.mode-btns {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin-bottom: 12px;
}

.mode-btns button {
  padding: 10px;
  border: 1px solid var(--border-card);
  border-radius: 8px;
  background: transparent;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--duration-fast);
}

.mode-btns button.active {
  border-color: var(--primary-color);
  background: var(--primary-soft);
  color: var(--primary-color);
}

.phone-btns {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.mapping-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.mapping-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid transparent;
  transition: all var(--duration-fast);
}

.mapping-item.active {
  background: var(--primary-soft);
  border-color: rgba(0,180,216,0.3);
}

.mapping-item strong {
  font-family: "SF Mono", "Consolas", monospace;
  font-size: 14px;
  color: var(--text-muted);
  min-width: 32px;
}

.mapping-item.active strong { color: var(--primary-color); }

.mapping-item span {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.mapping-item small {
  font-size: 11px;
  color: var(--text-muted);
}

.spinner { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
