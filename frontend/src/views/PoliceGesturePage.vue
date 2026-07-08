<template>
  <div class="police-page">
    <!-- 主画面：路口摄像头 + 骨架叠加 -->
    <div class="cam-area">
      <div class="viewport">
        <img :src="result.annotatedImageUrl" alt="路口摄像头" />
        <!-- 骨架叠加 -->
        <svg class="skel" viewBox="0 0 1200 720" preserveAspectRatio="none" v-if="result.detections.length">
          <g v-for="p in result.detections" :key="p.objectId">
            <rect :x="p.bbox.x1" :y="p.bbox.y1" :width="p.bbox.x2-p.bbox.x1" :height="p.bbox.y2-p.bbox.y1"
              fill="none" stroke="rgba(255,255,255,0.25)" stroke-width="2" stroke-dasharray="6 4"/>
            <line v-for="(pair,i) in bones" :key="i"
              :x1="kp(p,pair[0]).x" :y1="kp(p,pair[0]).y" :x2="kp(p,pair[1]).x" :y2="kp(p,pair[1]).y"
              stroke="#34a853" stroke-width="3" stroke-linecap="round"/>
            <circle v-for="k in p.keypoints" :key="k.name" :cx="k.x" :cy="k.y" r="6"
              fill="#34a853" stroke="#080c14" stroke-width="2"/>
          </g>
        </svg>

        <!-- 底部指令条 -->
        <div class="cmd-bar" v-if="gestureCode !== '--'">
          <span class="cmd-badge">{{ currentGesture }}</span>
          <span>{{ currentAction }}</span>
          <span class="cmd-conf">置信度 {{ Math.round(result.detections[0].confidence * 100) }}%</span>
        </div>
      </div>
    </div>

    <!-- 右侧信息 -->
    <div class="side">
      <!-- 当前手势（大字突出） -->
      <div class="card g-card" :class="{ active: gestureCode !== '--' }">
        <div class="g-code">{{ gestureCode }}</div>
        <strong>{{ currentGesture }}</strong>
        <p>{{ currentAction }}</p>
      </div>

      <!-- 置信度分布 -->
      <div class="card">
        <h4>分类置信度</h4>
        <div ref="chartRef" class="chart"></div>
      </div>

      <!-- 8种手势覆盖 -->
      <div class="card">
        <h4>8种标准手势</h4>
        <div class="g-grid">
          <span v-for="g in gestures" :key="g.code" :class="{ on: g.code === gestureCode }">{{ g.label }}</span>
        </div>
      </div>

      <!-- 从主屏跟进来时可返回 -->
      <button class="back-btn" @click="$router.push('/dashboard')">
        <el-icon><ArrowLeft /></el-icon> 返回驾驶主屏
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onBeforeUnmount, ref } from 'vue'
import * as echarts from 'echarts'
import { mockInference, mockConfidence } from '@/utils/mockData'
import { POLICE_GESTURE_MAP, TASK_TYPES } from '@/utils/constants'

const result = mockInference[TASK_TYPES.POLICE_GESTURE]
const cd = mockConfidence.police

const gestureCode = computed(() => result.detections[0]?.gestureCode || '--')
const currentGesture = computed(() => POLICE_GESTURE_MAP[gestureCode.value] || '未检测到手势')
const currentAction = computed(() => {
  const m = { STOP:'停车等待', GO_STRAIGHT:'允许通行', LEFT_TURN:'左转通行', LEFT_WAIT:'进入待转区',
    RIGHT_TURN:'右转通行', LANE_CHANGE:'变更车道', SLOW_DOWN:'减速慢行', PULL_OVER:'靠边停车' }
  return m[gestureCode.value] || ''
})
const gestures = Object.entries(POLICE_GESTURE_MAP).map(([c,l]) => ({ code:c, label:l }))

const bones = [
  ['nose','left_shoulder'],['nose','right_shoulder'],['left_shoulder','right_shoulder'],
  ['left_shoulder','left_elbow'],['left_elbow','left_wrist'],
  ['right_shoulder','right_elbow'],['right_elbow','right_wrist'],
  ['left_shoulder','left_hip'],['right_shoulder','right_hip'],['left_hip','right_hip'],
  ['left_hip','left_knee'],['left_knee','left_ankle'],
  ['right_hip','right_knee'],['right_knee','right_ankle']
]
function kp(person, name) {
  return person.keypoints?.find(k => k.name === name) || { x:0, y:0 }
}

const chartRef = ref(null)
let chart
function render() {
  if (!chartRef.value) return
  chart ||= echarts.init(chartRef.value)
  chart.setOption({
    grid: { left: 0, right: 10, top: 4, bottom: 0, containLabel: true },
    xAxis: { type:'value', max:100, axisLine:{show:false}, axisTick:{show:false}, splitLine:{lineStyle:{color:'rgba(255,255,255,0.04)'}} },
    yAxis: { type:'category', inverse:true, data:cd.map(d=>d.name), axisLine:{show:false}, axisTick:{show:false}, axisLabel:{color:'#8e9aaf'} },
    series: [{ type:'bar', data:cd.map(d=>d.value), barWidth:12,
      itemStyle:{ color:'#ea4335', borderRadius:[0,6,6,0] },
      label:{ show:true, position:'right', formatter:'{c}%', color:'#8e9aaf' } }]
  })
}
onMounted(()=>{ render(); window.addEventListener('resize',render) })
onBeforeUnmount(()=>{ window.removeEventListener('resize',render); chart?.dispose() })
</script>

<style scoped>
.police-page { display: grid; grid-template-columns: minmax(0,1fr) 300px; gap: 14px; height: 100%; }

.cam-area { }
.viewport { position: relative; height: 100%; min-height: 420px; border-radius: var(--radius-lg); overflow: hidden; background: #040810; }
.viewport img { width: 100%; height: 100%; object-fit: cover; opacity: 0.9; }
.skel { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; }

.cmd-bar {
  position: absolute; bottom: 0; left: 0; right: 0;
  display: flex; align-items: center; gap: 14px;
  padding: 12px 18px;
  background: linear-gradient(transparent, rgba(0,0,0,0.7));
  color: #fff; font-size: 14px; font-weight: 600;
}
.cmd-badge {
  padding: 6px 14px; border-radius: 999px;
  background: #ea4335; color: #fff; font-size: 14px; font-weight: 800;
}
.cmd-conf { margin-left: auto; font-size: 12px; opacity: 0.75; }

/* 右侧 */
.side { display: flex; flex-direction: column; gap: 12px; }
h4 { font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px; }

.g-card { text-align: center; padding: 22px; border-color: var(--border-card); }
.g-card.active { border-color: rgba(234,67,53,0.4); box-shadow: 0 0 20px rgba(234,67,53,0.08); }
.g-code { font-family: "SF Mono","Consolas",monospace; font-size: 42px; font-weight: 800; color: var(--text-muted); }
.g-card.active .g-code { color: #ea4335; text-shadow: 0 0 12px rgba(234,67,53,0.3); }
.g-card strong { display: block; margin-top: 6px; font-size: 20px; }
.g-card p { margin-top: 4px; font-size: 12px; color: var(--text-secondary); }

.chart { width: 100%; height: 200px; }

.g-grid { display: flex; flex-wrap: wrap; gap: 6px; }
.g-grid span { padding: 5px 10px; border-radius: 999px; border: 1px solid var(--border-card); font-size: 11px; font-weight: 600; color: var(--text-secondary); transition: all var(--duration-fast); }
.g-grid span.on { background: rgba(234,67,53,0.12); border-color: rgba(234,67,53,0.4); color: #ea4335; }

.back-btn {
  display: flex; align-items: center; justify-content: center; gap: 6px;
  width: 100%; padding: 10px; border: 1px solid var(--border-card); border-radius: 12px;
  background: transparent; color: var(--text-secondary); font-size: 13px; font-weight: 600; cursor: pointer;
  transition: all var(--duration-fast);
}
.back-btn:hover { border-color: var(--border-active); color: var(--text-primary); }
</style>
