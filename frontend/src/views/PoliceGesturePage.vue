<template>
  <MultiCameraRecognitionDetail
    v-if="props.embedded"
    task-type="police_gesture"
    :result="props.externalResult"
    :recognizing="props.externalRecognizing"
  />
  <div v-else class="gesture-page">
    <!-- 主画面 -->
    <div class="viewport-area">
      <div class="viewport">
        <img v-if="cameraDisplayUrl" :src="cameraDisplayUrl" alt="交警姿态后端叠框 JPEG" />
        <div v-else class="viewport-placeholder">
          <el-icon :size="48"><Aim /></el-icon>
          <span>{{ cameraError || '路口摄像头待机' }}</span>
        </div>

        <div class="viewport-top">
          <span class="chip live">● LIVE</span>
          <span class="chip">{{ cameraLabel }}</span>
        </div>

      </div>

      <!-- 底部指令条 -->
      <div class="command-bar" v-if="hasVisualSkeleton">
        <div class="command-main">
          <span class="command-badge">{{ hasGesture ? currentGesture : '目标跟踪中' }}</span>
          <span class="command-action">{{ hasGesture ? `输出交通指令：${currentAction}` : '等待交通指令' }}</span>
        </div>
        <div class="command-meta">
          <span v-if="hasGesture">置信度 {{ Math.round(currentDetection.confidence * 100) }}%</span>
          <span v-else>人体姿态已同步</span>
          <span>识别间隔 {{ recognitionIntervalMs / 1000 }}s</span>
          <span>JPEG · 精确帧后端 Pose 叠框</span>
        </div>
      </div>
    </div>

    <!-- 右侧信息面板 -->
    <div class="side-panel">
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

      <!-- 当前识别手势 -->
      <div class="card gesture-hero" :class="{ detected: hasGesture }">
        <div class="gesture-state">{{ hasGesture ? '已识别交通指令' : (hasVisualSkeleton ? '人体姿态识别中' : '等待识别') }}</div>
        <strong>{{ hasGesture ? currentGesture : (hasVisualSkeleton ? '暂无交通动作' : '等待识别') }}</strong>
        <p>{{ currentActionText }}</p>
      </div>

      <!-- 置信度 -->
      <div class="card">
        <h3 class="card-title">手势分类置信度</h3>
        <div ref="confidenceRef" class="chart"></div>
      </div>

      <!-- 8种标准手势 -->
      <div class="card">
        <h3 class="card-title">标准手势覆盖（8种）</h3>
        <div class="gesture-grid">
          <span
            v-for="g in standardGestures"
            :key="g.code"
            :class="{ active: g.code === gestureCode }"
          >{{ g.label }}</span>
        </div>
      </div>

      <!-- 识别流水线 -->
      <div class="card">
        <h3 class="card-title">推理流水线</h3>
        <div class="pipeline-list">
          <span v-for="(step, i) in pipelineSteps" :key="i">
            <small>{{ i + 1 }}</small> {{ step }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { mockConfidence } from '@/utils/mockData'
import { POLICE_GESTURE_MAP, TASK_TYPES } from '@/utils/constants'
import { getInferenceData, inferenceCameras } from '@/api/inference'
import { useCameraSource } from '@/composables/useCameraSource'
import MultiCameraRecognitionDetail from '@/components/common/MultiCameraRecognitionDetail.vue'
import { announcePoliceGesture } from '@/utils/speechAnnouncements'

const props = defineProps({
  embedded: { type: Boolean, default: false },
  externalResult: { type: Object, default: null },
  externalRecognizing: { type: Boolean, default: false }
})
const emit = defineEmits(['toggle-recognition'])

const localResult = ref(emptyResult())
const confidenceRef = ref(null)
const loading = ref(false)
const localRecognizing = ref(false)
const result = computed(() => props.externalResult || localResult.value)
const recognizing = computed(() => props.externalResult ? props.externalRecognizing : localRecognizing.value)
const recognitionIntervalMs = 500
let recognitionTimer = null
let chart
let lastAnnouncedGestureCode = ''

const {
  selectedCameraSourceId,
  selectedCameraSource,
  cameraStatus,
  cameraError,
  cameraDisplayUrl,
  loadCameraSources,
  refreshCameraPreview
} = useCameraSource(TASK_TYPES.POLICE_GESTURE, { processed: true, enabled: !props.embedded })

const currentDetection = computed(() => result.value.detections[0] || null)
const skeletonDetections = computed(() => result.value.detections.filter(item => item.keypoints?.length))
const hasSkeleton = computed(() => skeletonDetections.value.length > 0)
const hasVisualSkeleton = computed(() => hasSkeleton.value)
const hasGesture = computed(() => Boolean(currentDetection.value?.gestureCode))
const gestureCode = computed(() => currentDetection.value?.gestureCode || '--')
const currentGesture = computed(() => currentDetection.value?.gestureName || POLICE_GESTURE_MAP[gestureCode.value] || '等待识别')
const currentAction = computed(() => {
  if (currentDetection.value?.action) return currentDetection.value.action
  const map = {
    STOP: '停车等待', GO_STRAIGHT: '允许通行', LEFT_TURN: '左转通行',
    LEFT_WAIT: '进入待转区', RIGHT_TURN: '右转通行', LANE_CHANGE: '变更车道',
    SLOW_DOWN: '减速慢行', PULL_OVER: '靠边停车'
  }
  return map[gestureCode.value] || '—'
})
const currentActionText = computed(() => {
  if (hasGesture.value) return `输出交通指令：${currentAction.value}`
  if (hasVisualSkeleton.value) return '人体姿态持续识别中'
  return '输出交通指令：—'
})
const standardGestures = Object.entries(POLICE_GESTURE_MAP).map(([code, label]) => ({ code, label }))
const confidenceData = computed(() => {
  const top3 = result.value.detections[0]?.top3
  if (!top3?.length) return mockConfidence.police
  return top3.map(item => ({
    name: item.gestureName,
    value: Math.round(item.confidence * 100)
  }))
})

const pipelineSteps = ['摄像头帧输入', 'MediaPipe Pose', '姿态特征序列', 'ST-GCN/LSTM分类', '交通指令输出']
const cameraLabel = computed(() => {
  return selectedCameraSource.value?.name || '主服务摄像头模块'
})
const cameraStatusText = computed(() => {
  const labels = { idle: '未连接', loading: '连接中', ready: '已连接', empty: '无可用源', offline: '服务离线' }
  return labels[cameraStatus.value] || cameraStatus.value
})

function renderChart() {
  if (!confidenceRef.value) return
  chart ||= echarts.init(confidenceRef.value)
  chart.setOption({
    grid: { left: 0, right: 10, top: 4, bottom: 0, containLabel: true },
    xAxis: { type: 'value', max: 100, axisLine: { show: false }, axisTick: { show: false }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } } },
    yAxis: { type: 'category', inverse: true, data: confidenceData.value.map(d => d.name), axisLine: { show: false }, axisTick: { show: false }, axisLabel: { color: '#92a0b8' } },
    series: [{
      type: 'bar', data: confidenceData.value.map(d => d.value), barWidth: 12,
      itemStyle: { color: '#ea4335', borderRadius: [0, 6, 6, 0] },
      label: { show: true, position: 'right', formatter: '{c}%', color: '#92a0b8' }
    }]
  })
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
    const response = await inferenceCameras(TASK_TYPES.POLICE_GESTURE)
    const data = getInferenceData(response)
    const selectedResult = data?.cameras?.find(item => item.slotId === Number(selectedCameraSourceId.value))?.result
    localResult.value = {
      ...(selectedResult || data),
      detections: selectedResult?.detections || data?.detections || [],
      annotatedImageUrl: ''
    }
    announceGestureChange(localResult.value)
    renderChart()
  } catch (error) {
    console.error(error)
    if (!silent) ElMessage.error('识别失败，请检查主服务摄像头模块和交警算法服务')
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
  lastAnnouncedGestureCode = ''
  localResult.value = emptyResult()
  renderChart()
  recognizeOnce({ silent: true })
  clearInterval(recognitionTimer)
  recognitionTimer = setInterval(() => {
    if (localRecognizing.value) recognizeOnce({ silent: true })
  }, recognitionIntervalMs)
  ElMessage.success('已开始持续识别')
}

function announceGestureChange(nextResult) {
  if (props.embedded) return
  const detection = nextResult?.detections?.[0]
  const nextGestureCode = String(detection?.gestureCode || '').trim()
  if (!nextGestureCode || nextGestureCode === lastAnnouncedGestureCode) return

  lastAnnouncedGestureCode = nextGestureCode
  announcePoliceGesture(detection.gestureName || POLICE_GESTURE_MAP[nextGestureCode] || nextGestureCode)
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
    taskType: TASK_TYPES.POLICE_GESTURE,
    latencyMs: 0,
    image: { width: 1280, height: 720 },
    detections: [],
    detectionCount: 0,
    annotatedImageUrl: ''
  }
}

onMounted(() => { renderChart(); window.addEventListener('resize', renderChart) })
onBeforeUnmount(() => {
  clearInterval(recognitionTimer)
  window.removeEventListener('resize', renderChart)
  chart?.dispose()
})
watch(confidenceData, renderChart, { deep: true })
</script>

<style scoped>
.gesture-page {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  align-items: start;
  gap: 16px;
  height: 100%;
  overflow-y: auto;
}

.gesture-page.embedded {
  height: 100%;
  min-height: 560px;
}

.viewport-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.viewport {
  position: relative;
  flex: none;
  width: min(100%, 1040px, calc((100vh - 230px) * 16 / 9));
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
  opacity: 0.88;
  background: #070b12;
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
  color: #ea4335;
  border-color: rgba(234,67,53,0.4);
}

.command-bar {
  width: min(100%, 1040px, calc((100vh - 230px) * 16 / 9));
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  background: var(--bg-card);
  border: 1px solid var(--border-card);
  border-radius: var(--radius-md);
}

.command-main {
  display: flex;
  align-items: center;
  gap: 14px;
}

.command-badge {
  padding: 8px 18px;
  background: linear-gradient(135deg, #ea4335, #c5221f);
  border-radius: 999px;
  color: #fff;
  font-size: 16px;
  font-weight: 800;
  letter-spacing: 0.5px;
}

.command-action {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.command-meta {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: var(--text-muted);
  font-weight: 600;
}

/* 右侧面板 */
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

.state-text.loading { color: var(--warning-color); }

.state-text.offline,
.state-text.empty { color: var(--danger-color); }

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
  background: linear-gradient(135deg, #ea4335, #c5221f);
  color: #fff;
}

.action-btn.primary.danger {
  background: linear-gradient(135deg, var(--danger-color), #b91c1c);
  box-shadow: 0 4px 18px rgba(255,61,0,0.22);
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
  border-color: rgba(234,67,53,0.4);
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
  background: var(--bg-card);
  border: 1px solid var(--border-card);
  transition: border-color var(--duration-fast);
}

.gesture-hero.detected {
  border-color: rgba(234,67,53,0.4);
  box-shadow: 0 0 24px rgba(234,67,53,0.08);
}

.gesture-state {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 28px;
  padding: 5px 12px;
  border-radius: 999px;
  border: 1px solid var(--border-card);
  background: rgba(255,255,255,0.03);
  font-size: 12px;
  font-weight: 700;
  color: var(--text-muted);
}

.gesture-hero.detected .gesture-state {
  border-color: rgba(234,67,53,0.35);
  background: rgba(234,67,53,0.10);
  color: #ea4335;
}

.gesture-hero strong {
  display: block;
  margin-top: 8px;
  font-size: 20px;
  color: var(--text-primary);
}

.gesture-hero p {
  margin-top: 6px;
  font-size: 13px;
  color: var(--text-secondary);
}

.gesture-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.gesture-grid span {
  padding: 7px 14px;
  background: rgba(255,255,255,0.03);
  border: 1px solid var(--border-card);
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  transition: all var(--duration-fast);
}

.gesture-grid span.active {
  background: rgba(234,67,53,0.12);
  border-color: rgba(234,67,53,0.4);
  color: #ea4335;
}

.pipeline-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.pipeline-list span {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: rgba(255,255,255,0.02);
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  border-left: 3px solid var(--border-card);
}

.pipeline-list span small {
  width: 22px;
  height: 22px;
  display: grid;
  place-items: center;
  background: rgba(255,255,255,0.06);
  border-radius: 6px;
  font-size: 11px;
  color: var(--text-muted);
}

.chart { width: 100%; height: 200px; }
.spinner { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 900px) {
  .gesture-page {
    grid-template-columns: 1fr;
    gap: 12px;
    height: auto;
    min-height: 100%;
    padding-bottom: 12px;
    overflow-y: auto;
  }

  .viewport {
    flex: none;
    width: 100%;
    min-height: 0;
    aspect-ratio: 16 / 9;
  }

  .command-bar {
    width: 100%;
  }

  .side-panel {
    overflow: visible;
  }

  .command-bar {
    align-items: flex-start;
    flex-direction: column;
    gap: 8px;
  }

  .command-main,
  .command-meta {
    flex-wrap: wrap;
  }
}

@media (max-width: 480px) {
  .gesture-page {
    gap: 10px;
  }

  .viewport {
    min-height: 190px;
  }

  .control-row {
    padding: 10px;
  }

  .control-row strong {
    max-width: 180px;
  }

  .gesture-hero {
    padding: 22px 18px;
  }

  .chart {
    height: 180px;
  }
}
</style>
