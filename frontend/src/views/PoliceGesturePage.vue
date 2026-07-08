<template>
  <div class="gesture-page">
    <!-- 主画面 -->
    <div class="viewport-area">
      <div class="viewport">
        <img v-if="result.annotatedImageUrl" :src="result.annotatedImageUrl" alt="camera" />
        <div v-else class="viewport-placeholder">
          <el-icon :size="48"><Aim /></el-icon>
          <span>路口摄像头待机</span>
        </div>

        <!-- 骨架叠加 -->
        <svg class="skeleton-overlay" viewBox="0 0 1200 720" preserveAspectRatio="none" v-if="result.detections.length">
          <g v-for="person in result.detections" :key="person.objectId">
            <!-- 人体框 -->
            <rect
              :x="person.bbox.x1" :y="person.bbox.y1"
              :width="person.bbox.x2 - person.bbox.x1"
              :height="person.bbox.y2 - person.bbox.y1"
              fill="none" stroke="rgba(255,255,255,0.3)" stroke-width="2" stroke-dasharray="6 4"
            />
            <!-- 骨架连线 -->
            <line v-for="(pair, i) in bonePairs" :key="i"
              :x1="getKp(person, pair[0]).x" :y1="getKp(person, pair[0]).y"
              :x2="getKp(person, pair[1]).x" :y2="getKp(person, pair[1]).y"
              stroke="rgba(0,230,118,0.7)" stroke-width="3" stroke-linecap="round"
            />
            <!-- 关键点 -->
            <circle v-for="kp in person.keypoints" :key="kp.name"
              :cx="kp.x" :cy="kp.y" r="6"
              fill="#00e676" stroke="#080c14" stroke-width="2"
            />
          </g>
        </svg>
      </div>

      <!-- 底部指令条 -->
      <div class="command-bar" v-if="result.detections.length">
        <div class="command-main">
          <span class="command-badge">{{ currentGesture }}</span>
          <span class="command-action">输出交通指令：{{ currentAction }}</span>
        </div>
        <div class="command-meta">
          <span>置信度 {{ Math.round(result.detections[0].confidence * 100) }}%</span>
          <span>端到端 ≤ 2s</span>
          <span>帧缓存 30</span>
        </div>
      </div>
    </div>

    <!-- 右侧信息面板 -->
    <div class="side-panel">
      <!-- 当前识别手势 -->
      <div class="card gesture-hero" :class="{ detected: result.detections.length }">
        <div class="gesture-code">{{ gestureCode }}</div>
        <strong>{{ currentGesture }}</strong>
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
import { mockInference, mockConfidence } from '@/utils/mockData'
import { POLICE_GESTURE_MAP, TASK_TYPES } from '@/utils/constants'

const result = mockInference[TASK_TYPES.POLICE_GESTURE]
const confidenceData = mockConfidence.police
const confidenceRef = ref(null)
let chart

const gestureCode = computed(() => result.detections[0]?.gestureCode || '--')
const currentGesture = computed(() => POLICE_GESTURE_MAP[gestureCode.value] || '等待识别')
const currentAction = computed(() => {
  const map = {
    STOP: '停车等待', GO_STRAIGHT: '允许通行', LEFT_TURN: '左转通行',
    LEFT_WAIT: '进入待转区', RIGHT_TURN: '右转通行', LANE_CHANGE: '变更车道',
    SLOW_DOWN: '减速慢行', PULL_OVER: '靠边停车'
  }
  return map[gestureCode.value] || '—'
})
const currentActionText = computed(() => `输出交通指令：${currentAction.value}`)

const standardGestures = Object.entries(POLICE_GESTURE_MAP).map(([code, label]) => ({ code, label }))

const pipelineSteps = ['摄像头帧输入', 'MediaPipe Pose', '关键点序列提取', 'ST-GCN/LSTM分类', '交通指令输出']

const bonePairs = [
  ['nose','left_shoulder'],['nose','right_shoulder'],['left_shoulder','right_shoulder'],
  ['left_shoulder','left_elbow'],['left_elbow','left_wrist'],
  ['right_shoulder','right_elbow'],['right_elbow','right_wrist'],
  ['left_shoulder','left_hip'],['right_shoulder','right_hip'],['left_hip','right_hip'],
  ['left_hip','left_knee'],['left_knee','left_ankle'],
  ['right_hip','right_knee'],['right_knee','right_ankle']
]

function getKp(person, name) {
  return person.keypoints?.find(k => k.name === name) || { x: 0, y: 0 }
}

function renderChart() {
  if (!confidenceRef.value) return
  chart ||= echarts.init(confidenceRef.value)
  chart.setOption({
    grid: { left: 0, right: 10, top: 4, bottom: 0, containLabel: true },
    xAxis: { type: 'value', max: 100, axisLine: { show: false }, axisTick: { show: false }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } } },
    yAxis: { type: 'category', inverse: true, data: confidenceData.map(d => d.name), axisLine: { show: false }, axisTick: { show: false }, axisLabel: { color: '#92a0b8' } },
    series: [{
      type: 'bar', data: confidenceData.map(d => d.value), barWidth: 12,
      itemStyle: { color: '#ea4335', borderRadius: [0, 6, 6, 0] },
      label: { show: true, position: 'right', formatter: '{c}%', color: '#92a0b8' }
    }]
  })
}

onMounted(() => { renderChart(); window.addEventListener('resize', renderChart) })
onBeforeUnmount(() => { window.removeEventListener('resize', renderChart); chart?.dispose() })
</script>

<style scoped>
.gesture-page {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 16px;
  height: 100%;
}

.viewport-area {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.viewport {
  position: relative;
  flex: 1;
  min-height: 380px;
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: #080c14;
}

.viewport img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  opacity: 0.88;
}

.viewport-placeholder {
  height: 100%;
  min-height: 380px;
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

.skeleton-overlay {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.command-bar {
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

.gesture-code {
  font-family: "SF Mono", "Consolas", monospace;
  font-size: 48px;
  font-weight: 800;
  color: var(--text-muted);
  letter-spacing: 2px;
}

.gesture-hero.detected .gesture-code {
  color: #ea4335;
  text-shadow: 0 0 16px rgba(234,67,53,0.3);
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
</style>
