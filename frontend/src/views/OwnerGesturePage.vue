<template>
  <div class="owner-page">
    <!-- 主画面：车内摄像头 + 手部骨架叠加 -->
    <div class="cam-area">
      <div class="viewport">
        <img :src="result.annotatedImageUrl" alt="车内摄像头" />
        <svg class="skel" viewBox="0 0 1200 720" preserveAspectRatio="none" v-if="result.detections.length">
          <g v-for="h in result.detections" :key="h.objectId">
            <line v-for="(pair,i) in handBones" :key="i"
              :x1="kp(h,pair[0]).x" :y1="kp(h,pair[0]).y" :x2="kp(h,pair[1]).x" :y2="kp(h,pair[1]).y"
              stroke="#1a73e8" stroke-width="3" stroke-linecap="round"/>
            <circle v-for="k in h.keypoints" :key="k.name" :cx="k.x" :cy="k.y" r="5"
              fill="#1a73e8" stroke="#080c14" stroke-width="2"/>
          </g>
        </svg>
        <!-- 当前手势标签 -->
        <div class="g-tag" v-if="gesture">
          <span>{{ gestureIcon }}</span>
          <span>{{ gesture.name }} → {{ gesture.action }}</span>
        </div>
      </div>

      <!-- 触发判定条 -->
      <div class="trig-bar">
        <div class="trig-item ok"><span>持续时间</span><strong>0.72s ≥ 0.50s ✓</strong></div>
        <div class="trig-item ok"><span>置信度</span><strong>91% ≥ 70% ✓</strong></div>
        <div class="trig-item ok"><span>状态</span><strong>已触发控制反馈</strong></div>
      </div>
    </div>

    <!-- 右侧面板 -->
    <div class="side">
      <!-- 手势显示 -->
      <div class="card g-card" :class="{ active: !!gesture }">
        <div class="g-code">{{ gestureCode }}</div>
        <strong>{{ gesture?.name || '等待手势' }}</strong>
        <p>{{ gesture?.action || '—' }}</p>
      </div>

      <!-- 车控面板 -->
      <div class="card">
        <h4>车辆控制反馈</h4>
        <div class="ctrl-item" :class="{ hl: gesture?.action === '调节音量' }">
          <div class="ctrl-head"><el-icon><Headset /></el-icon><span>音量</span><strong>{{ ctrl.volume }}%</strong></div>
          <el-slider v-model="ctrl.volume" />
        </div>
        <div class="ctrl-item" :class="{ hl: gesture?.action === '切换功能' }">
          <div class="ctrl-head"><el-icon><Sunny /></el-icon><span>空调</span><strong>{{ ctrl.temperature }}°C</strong></div>
          <el-slider v-model="ctrl.temperature" :min="16" :max="30" />
        </div>
        <div class="mode-row">
          <button v-for="m in modes" :key="m" :class="{ on: ctrl.mode === m }" @click="ctrl.mode = m">{{ m }}</button>
        </div>
        <div class="phone-row">
          <el-button :type="gesture?.action==='接听电话'?'success':'default'" size="small">接听</el-button>
          <el-button :type="gesture?.action==='挂断电话'?'danger':'default'" size="small">挂断</el-button>
        </div>
      </div>

      <!-- 手势映射 -->
      <div class="card">
        <h4>手势映射</h4>
        <div class="map-list">
          <div v-for="(v,k) in MAP" :key="k" class="map-item" :class="{ on: k === gestureCode }">
            <strong>{{ k }}</strong><div><span>{{ v.name }}</span><small>{{ v.action }}</small></div>
          </div>
        </div>
      </div>

      <button class="back-btn" @click="$router.push('/dashboard')">
        <el-icon><ArrowLeft /></el-icon> 返回驾驶主屏
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive } from 'vue'
import { mockInference } from '@/utils/mockData'
import { OWNER_GESTURE_MAP, TASK_TYPES } from '@/utils/constants'

const result = mockInference[TASK_TYPES.OWNER_GESTURE]
const MAP = OWNER_GESTURE_MAP

const gestureCode = computed(() => result.detections[0]?.gestureCode || '--')
const gesture = computed(() => MAP[gestureCode.value] || null)
const gestureIcon = computed(() => ({'001':'✋','002':'✊','003':'👆','004':'👈','005':'👍','006':'👎','007':'👋'}[gestureCode.value] || '🖐'))

const ctrl = reactive({ volume: 42, temperature: 24, mode: '音乐' })
const modes = ['音乐','导航','电话','空调']

const handBones = [['wrist','thumb_tip'],['wrist','index_tip'],['wrist','middle_tip'],['wrist','ring_tip'],['wrist','pinky_tip']]
function kp(hand, name) { return hand.keypoints?.find(k => k.name === name) || { x:0,y:0 } }
</script>

<style scoped>
.owner-page { display: grid; grid-template-columns: minmax(0,1fr) 320px; gap: 14px; height: 100%; }

.cam-area { display: flex; flex-direction: column; gap: 10px; }
.viewport { position: relative; flex: 1; min-height: 340px; border-radius: var(--radius-lg); overflow: hidden; background: #040810; }
.viewport img { width: 100%; height: 100%; object-fit: cover; opacity: 0.9; }
.skel { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; }

.g-tag {
  position: absolute; bottom: 16px; left: 16px;
  display: flex; align-items: center; gap: 8px;
  padding: 8px 14px; border-radius: 999px;
  background: rgba(26,115,232,0.18); border: 1px solid rgba(26,115,232,0.35);
  font-size: 14px; font-weight: 700; color: var(--primary-color);
  backdrop-filter: blur(8px);
}

.trig-bar { display: grid; grid-template-columns: repeat(3,1fr); gap: 8px; }
.trig-item { padding: 10px 12px; background: var(--bg-card); border: 1px solid var(--border-card); border-radius: var(--radius-sm); }
.trig-item.ok { background: rgba(52,168,83,0.04); border-color: rgba(52,168,83,0.2); }
.trig-item span { font-size: 10px; color: var(--text-muted); display: block; }
.trig-item strong { font-size: 13px; color: var(--text-primary); display: block; margin-top: 3px; }
.trig-item.ok strong { color: var(--success-color); }

/* 右侧 */
.side { display: flex; flex-direction: column; gap: 12px; overflow-y: auto; }
h4 { font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px; }

.g-card { text-align: center; padding: 22px; }
.g-card.active { border-color: rgba(26,115,232,0.35); box-shadow: 0 0 20px var(--primary-glow); }
.g-code { font-family: "SF Mono","Consolas",monospace; font-size: 42px; font-weight: 800; color: var(--text-muted); }
.g-card.active .g-code { color: var(--primary-color); text-shadow: 0 0 12px var(--primary-glow); }
.g-card strong { display: block; margin-top: 6px; font-size: 20px; }
.g-card p { margin-top: 4px; font-size: 12px; color: var(--text-secondary); }

.ctrl-item { padding: 12px; background: rgba(255,255,255,0.02); border-radius: var(--radius-sm); margin-bottom: 8px; border: 1px solid transparent; }
.ctrl-item.hl { border-color: var(--primary-color); background: var(--primary-soft); }
.ctrl-head { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; font-size: 13px; color: var(--text-secondary); }
.ctrl-head strong { margin-left: auto; color: var(--primary-color); font-size: 15px; }

.mode-row { display: grid; grid-template-columns: repeat(4,1fr); gap: 6px; margin-bottom: 10px; }
.mode-row button { padding: 8px; border: 1px solid var(--border-card); border-radius: 8px; background: transparent; color: var(--text-secondary); font-size: 11px; font-weight: 600; cursor: pointer; }
.mode-row button.on { border-color: var(--primary-color); background: var(--primary-soft); color: var(--primary-color); }
.phone-row { display: grid; grid-template-columns: repeat(2,1fr); gap: 8px; }

.map-list { display: flex; flex-direction: column; gap: 4px; }
.map-item { display: flex; align-items: center; gap: 10px; padding: 8px 10px; border-radius: 8px; border: 1px solid transparent; }
.map-item.on { background: var(--primary-soft); border-color: rgba(26,115,232,0.3); }
.map-item strong { font-family: "SF Mono","Consolas",monospace; font-size: 12px; color: var(--text-muted); min-width: 28px; }
.map-item.on strong { color: var(--primary-color); }
.map-item span { font-size: 12px; font-weight: 600; color: var(--text-primary); display: block; }
.map-item small { font-size: 10px; color: var(--text-muted); }

.back-btn {
  display: flex; align-items: center; justify-content: center; gap: 6px;
  width: 100%; padding: 10px; border: 1px solid var(--border-card); border-radius: 12px;
  background: transparent; color: var(--text-secondary); font-size: 13px; font-weight: 600; cursor: pointer;
}
.back-btn:hover { border-color: var(--border-active); color: var(--text-primary); }
</style>
