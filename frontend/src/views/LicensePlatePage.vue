<template>
  <MultiCameraRecognitionDetail
    v-if="props.embedded"
    task-type="license_plate"
    :result="props.externalResult"
    :recognizing="props.externalRecognizing"
    :preloaded-streams="props.preloadedStreams"
  />
  <div v-else class="plate-page">
    <!-- 主区域：摄像头大画面 -->
    <div class="viewport-area">
      <div class="viewport" :class="{ 'showing-synchronized-frame': synchronizedResultFrameUrl }">
        <video
          v-show="cameraVideoReady && !synchronizedResultFrameUrl"
          ref="cameraVideoRef"
          autoplay
          muted
          playsinline
          @loadeddata="markCameraVideoReady"
          @playing="markCameraVideoReady"
        ></video>
        <img
          v-if="synchronizedResultFrameUrl"
          :src="synchronizedResultFrameUrl"
          alt="与识别结果同步的车牌检测帧"
        />
        <img v-else-if="!cameraVideoReady && cameraDisplayUrl" :src="cameraDisplayUrl" alt="camera fallback" />
        <div v-if="!synchronizedResultFrameUrl && !cameraVideoReady && !cameraDisplayUrl" class="viewport-placeholder">
          <el-icon :size="48"><Camera /></el-icon>
          <span>{{ cameraError || '等待摄像头服务' }}</span>
        </div>

        <!-- 检测框叠加层 -->
        <svg
          class="detection-overlay"
          :viewBox="detectionViewBox"
          preserveAspectRatio="xMidYMid meet"
          v-if="result.detections.length && !synchronizedResultFrameUrl"
        >
          <g v-for="box in result.detections" :key="box.objectId">
            <rect
              :x="box.bbox.x1" :y="box.bbox.y1"
              :width="box.bbox.x2 - box.bbox.x1"
              :height="box.bbox.y2 - box.bbox.y1"
              fill="none"
              :stroke="plateTheme(box).accent"
              stroke-width="4"
              class="detect-rect"
            />
            <rect
              :x="box.bbox.x1"
              :y="Math.max(0, box.bbox.y1 - 32)"
              :width="plateLabelWidth(box)"
              height="28"
              rx="14"
              :fill="plateTheme(box).accent"
            />
            <text
              :x="box.bbox.x1 + 14"
              :y="Math.max(18, box.bbox.y1 - 11)"
              :fill="plateTheme(box).text"
              font-size="18"
              font-weight="800"
            >{{ plateOverlayText(box) }}</text>
          </g>
        </svg>

        <div class="scan-line-animated"></div>

        <!-- 顶部状态 -->
        <div class="viewport-top">
          <span class="chip live">{{ synchronizedResultFrameUrl ? '● 同步帧' : '● LIVE' }}</span>
          <span class="chip">{{ cameraLabel }}</span>
        </div>

        <!-- 底部检测信息 -->
        <div class="viewport-bottom" v-if="result.detections.length">
          <div class="detect-summary">
            <span>检测到 <strong>{{ result.detections.length }}</strong> 辆车</span>
            <span>耗时 {{ result.latencyMs }}ms</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 右侧操作面板 -->
    <div class="side-panel">
      <!-- 输入模式切换 -->
      <div class="card">
        <h3 class="card-title">识别控制</h3>
        <div class="camera-control">
          <div class="control-row">
            <span>视频输入</span>
            <strong>{{ selectedCameraSource?.name || '主服务摄像头模块' }}</strong>
          </div>
          <div class="control-row">
            <span>服务状态</span>
            <strong :class="['state-text', cameraStatus]">{{ cameraError || cameraStatusText }}</strong>
          </div>
          <div class="control-row">
            <span>识别状态</span>
            <strong :class="{ active: recognizing }">{{ recognizing ? '持续识别中' : '未启动' }}</strong>
          </div>
          <div class="control-row">
            <span>识别间隔</span>
            <strong>{{ recognitionIntervalMs / 1000 }}s</strong>
          </div>
        </div>

        <button
          v-if="!props.embedded"
          class="action-btn primary"
          :class="{ danger: recognizing }"
          :disabled="!selectedCameraSourceId && !recognizing"
          @click="toggleRecognition"
        >
          <el-icon v-if="loading" class="spinner"><Loading /></el-icon>
          {{ recognizing ? '停止识别' : (loading ? '识别中...' : '开始持续识别') }}
        </button>

        <button v-else class="action-btn primary external-control" type="button" disabled>
          识别由驾驶主界面统一控制
        </button>

        <button class="action-btn secondary compact" :disabled="recognizing" @click="refreshCameraSource">
          刷新视频输入
        </button>
      </div>

      <!-- 识别结果 -->
      <div class="card">
        <h3 class="card-title">识别结果</h3>
        <div v-if="result.detections.length" class="result-list">
          <div v-for="item in result.detections" :key="item.objectId" class="result-item">
            <div class="plate-tag" :style="plateTagStyle(item)">
              {{ item.plateNumber }}
            </div>
            <div class="result-meta">
              <span>{{ plateColorLabel(item) }}</span>
              <span>OCR {{ percent(item.ocrConfidence) }}</span>
            </div>
          </div>
        </div>
        <div v-else class="empty-result">
          <el-icon :size="32"><Picture /></el-icon>
          <span>暂无识别结果</span>
          <small>{{ recognizing ? '等待下一次识别结果' : '点击开始持续识别后输出结果' }}</small>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { TASK_TYPES } from '@/utils/constants'
import { getInferenceData, inferenceCameras } from '@/api/inference'
import { useCameraSource } from '@/composables/useCameraSource'
import MultiCameraRecognitionDetail from '@/components/common/MultiCameraRecognitionDetail.vue'

const props = defineProps({
  embedded: { type: Boolean, default: false },
  externalResult: { type: Object, default: null },
  externalRecognizing: { type: Boolean, default: false },
  preloadedStreams: { type: Object, default: null }
})
const emit = defineEmits(['toggle-recognition'])

const localResult = ref(emptyResult())
const loading = ref(false)
const localRecognizing = ref(false)
const result = computed(() => props.externalResult || localResult.value)
const recognizing = computed(() => props.externalResult ? props.externalRecognizing : localRecognizing.value)
const recognitionIntervalMs = 300
let recognitionTimer = null
const {
  selectedCameraSourceId,
  selectedCameraSource,
  cameraStatus,
  cameraError,
  cameraDisplayUrl,
  cameraVideoRef,
  cameraVideoReady,
  loadCameraSources,
  markCameraVideoReady,
  refreshCameraPreview
} = useCameraSource(TASK_TYPES.LICENSE_PLATE)

const cameraLabel = computed(() => {
  return selectedCameraSource.value?.name || '主服务摄像头模块'
})
const cameraStatusText = computed(() => {
  const labels = { idle: '未连接', loading: '连接中', ready: '已连接', empty: '无可用源', offline: '服务离线' }
  return labels[cameraStatus.value] || cameraStatus.value
})
const synchronizedResultFrameUrl = computed(() => {
  if (!result.value.detections.length) return ''
  return result.value.annotatedImageUrl || ''
})
const detectionViewBox = computed(() => {
  const width = result.value.image?.width || 1280
  const height = result.value.image?.height || 720
  return `0 0 ${width} ${height}`
})

const plateColorThemes = {
  blue: { accent: '#1a73e8', bg: '#163e7a', text: '#ffffff', border: 'rgba(116, 185, 255, 0.58)', label: '蓝牌' },
  green: { accent: '#00e676', bg: '#0b5f32', text: '#06140c', border: 'rgba(0, 230, 118, 0.62)', label: '绿牌' },
  yellow: { accent: '#ffd43b', bg: '#ffd43b', text: '#1d1600', border: 'rgba(255, 212, 59, 0.82)', label: '黄牌' },
  white: { accent: '#f8fafc', bg: '#f8fafc', text: '#111827', border: 'rgba(248, 250, 252, 0.7)', label: '白牌' },
  black: { accent: '#111827', bg: '#111827', text: '#f8fafc', border: 'rgba(255, 255, 255, 0.28)', label: '黑牌' },
  unknown: { accent: '#00e676', bg: '#1c2434', text: '#eef2f7', border: 'rgba(255, 255, 255, 0.16)', label: '未知颜色' }
}

function normalizePlateColor(item = {}) {
  const value = String(item.plateColor || item.plateType || '').toLowerCase()
  if (value.includes('yellow') || value.includes('黄')) return 'yellow'
  if (value.includes('blue') || value.includes('蓝')) return 'blue'
  if (value.includes('green') || value.includes('绿') || value.includes('新能源')) return 'green'
  if (value.includes('white') || value.includes('白')) return 'white'
  if (value.includes('black') || value.includes('黑')) return 'black'
  return 'unknown'
}

function plateTheme(item) {
  return plateColorThemes[normalizePlateColor(item)] || plateColorThemes.unknown
}

function plateColorLabel(item) {
  const type = item.plateType || plateTheme(item).label
  const confidence = typeof item.confidence === 'number' ? ` · 置信度 ${percent(item.confidence)}` : ''
  return `${type}${confidence}`
}

function percent(value) {
  return typeof value === 'number' && Number.isFinite(value) ? `${Math.round(value * 100)}%` : '--'
}

function plateOverlayText(item) {
  return item.plateNumber || item.objectId || '车牌'
}

function plateLabelWidth(item) {
  return Math.max(96, plateOverlayText(item).length * 22 + 28)
}

function plateTagStyle(item) {
  const theme = plateTheme(item)
  return {
    background: theme.bg,
    color: theme.text,
    borderColor: theme.border,
    boxShadow: `0 0 18px ${theme.border}`
  }
}

async function refreshCameraSource() {
  await loadCameraSources()
  refreshCameraPreview()
  ElMessage.success('视频输入已刷新')
}

async function recognizeOnce({ silent = false } = {}) {
  if (loading.value) return
  if (!selectedCameraSourceId.value) {
    if (!silent) ElMessage.warning('主服务摄像头模块暂无可用视频输入')
    return
  }

  loading.value = true
  try {
    const response = await inferenceCameras(TASK_TYPES.LICENSE_PLATE)
    const data = getInferenceData(response)
    const selectedResult = data?.cameras?.find(item => item.slotId === Number(selectedCameraSourceId.value))?.result
    localResult.value = {
      ...emptyResult(),
      ...(selectedResult || data || {}),
      detections: selectedResult?.detections || data?.detections || []
    }
  } catch (error) {
    console.error(error)
    if (!silent) ElMessage.error('识别失败，请检查主服务摄像头模块和车牌算法服务')
  } finally {
    loading.value = false
  }
}

function startRecognition() {
  if (!selectedCameraSourceId.value) {
    ElMessage.warning('主服务摄像头模块暂无可用视频输入')
    return
  }
  localRecognizing.value = true
  localResult.value = emptyResult()
  recognizeOnce({ silent: true })
  clearInterval(recognitionTimer)
  recognitionTimer = setInterval(() => {
    if (localRecognizing.value) recognizeOnce({ silent: true })
  }, recognitionIntervalMs)
  ElMessage.success('已开始持续识别')
}

function stopRecognition() {
  localRecognizing.value = false
  clearInterval(recognitionTimer)
  recognitionTimer = null
  ElMessage.info('已停止识别')
}

function toggleRecognition() {
  if (props.externalResult) {
    emit('toggle-recognition')
    return
  }
  if (localRecognizing.value) stopRecognition()
  else startRecognition()
}

function emptyResult() {
  return {
    taskType: TASK_TYPES.LICENSE_PLATE,
    latencyMs: 0,
    image: { width: 1280, height: 720 },
    detections: [],
    detectionCount: 0,
    annotatedImageUrl: ''
  }
}

onBeforeUnmount(() => {
  clearInterval(recognitionTimer)
})
</script>

<style scoped>
.plate-page {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  align-items: start;
  gap: 16px;
  height: 100%;
  overflow-y: auto;
}

.plate-page.embedded {
  height: 100%;
  min-height: 560px;
}

/* ---- 摄像头大画面 ---- */
.viewport-area {
  min-width: 0;
  display: flex;
  justify-content: center;
}

.viewport {
  position: relative;
  width: min(100%, 1120px, calc((100vh - 170px) * 16 / 9));
  aspect-ratio: 16 / 9;
  min-height: 0;
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: #080c14;
}

.viewport video,
.viewport img {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: contain;
  opacity: 0.9;
  background: #070b12;
}

.viewport.showing-synchronized-frame video {
  display: none !important;
}

.viewport-placeholder {
  height: 100%;
  min-height: 0;
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

.detection-overlay {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.detect-rect {
  animation: breathe 2s ease-in-out infinite;
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

.viewport-bottom {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 14px 18px;
  background: linear-gradient(transparent, rgba(0,0,0,0.7));
}

.detect-summary {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
  color: var(--text-primary);
}

.detect-summary strong {
  color: var(--success-color);
  font-size: 18px;
}

/* ---- 侧边面板 ---- */
.side-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
  overflow-y: auto;
}

.card-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 14px;
}

.camera-control {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.control-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px;
  background: rgba(255,255,255,0.025);
  border: 1px solid var(--border-card);
  border-radius: var(--radius-sm);
}

.control-row span {
  flex: 0 0 auto;
  font-size: 12px;
  font-weight: 700;
  color: var(--text-muted);
}

.control-row strong {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
  color: var(--text-secondary);
}

.control-row strong.active,
.state-text.ready {
  color: var(--success-color);
}

.state-text.loading {
  color: var(--warning-color);
}

.state-text.offline,
.state-text.empty {
  color: var(--danger-color);
}

.action-btn {
  width: 100%;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 16px;
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

.action-btn.primary.danger {
  background: linear-gradient(135deg, var(--danger-color), #c5221f);
  color: #fff;
  box-shadow: 0 4px 18px rgba(255,61,0,0.22);
}

.action-btn.primary:hover:not(:disabled) {
  box-shadow: 0 6px 26px rgba(0,180,216,0.35);
  transform: translateY(-1px);
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

/* 结果列表 */
.result-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.result-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: rgba(255,255,255,0.03);
  border-radius: var(--radius-sm);
}

.plate-tag {
  min-width: 100px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 6px;
  border: 1.5px solid rgba(255,255,255,0.16);
  font-size: 16px;
  font-weight: 800;
  letter-spacing: 1px;
}

.plate-tag.blue {
  background: #1a3a6b;
  color: #88c8ff;
  border: 1.5px solid rgba(100,160,255,0.4);
}

.plate-tag.green {
  background: #0a3a1a;
  color: #66e088;
  border: 1.5px solid rgba(0,230,118,0.4);
}

.result-meta span {
  display: block;
  font-size: 12px;
  color: var(--text-secondary);
}

.result-meta span + span {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 2px;
}

.empty-result {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 28px 0;
  color: var(--text-muted);
}

.empty-result span { font-size: 13px; }
.empty-result small { font-size: 11px; }

.spinner { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 900px) {
  .plate-page {
    grid-template-columns: 1fr;
    height: auto;
    min-height: 100%;
    padding-bottom: 12px;
  }

  .viewport-area {
    justify-content: stretch;
  }

  .viewport {
    width: 100%;
  }

  .side-panel {
    overflow: visible;
  }
}

@media (max-width: 480px) {
  .plate-page {
    gap: 12px;
  }

  .control-row {
    padding: 10px;
  }

  .control-row strong {
    max-width: 180px;
  }
}
</style>
