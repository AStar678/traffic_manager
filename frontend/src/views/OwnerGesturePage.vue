<template>
  <div class="owner-page">
    <!-- 主画面：车内摄像头 + 手势叠加 -->
    <div class="viewport-area">
      <div class="viewport">
        <img v-if="result.annotatedImageUrl" :src="result.annotatedImageUrl" alt="cockpit" />
        <div v-else class="viewport-placeholder">
          <el-icon :size="48"><Pointer /></el-icon>
          <span>车内摄像头待机</span>
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
import { computed, reactive } from 'vue'
import { mockInference } from '@/utils/mockData'
import { OWNER_GESTURE_MAP, TASK_TYPES } from '@/utils/constants'

const result = mockInference[TASK_TYPES.OWNER_GESTURE]
const OWNER_MAP = OWNER_GESTURE_MAP

const gestureCode = computed(() => result.detections[0]?.gestureCode || '--')
const gesture = computed(() => OWNER_MAP[gestureCode.value] || null)

const gestureIcon = computed(() => {
  const icons = { '001': '✋', '002': '✊', '003': '👆', '004': '👈', '005': '👍', '006': '👎', '007': '👋' }
  return icons[gestureCode.value] || '🖐'
})

const controlState = reactive({ volume: 42, temperature: 24, mode: '音乐' })
const modes = ['音乐', '导航', '电话', '空调']

const triggerItems = [
  { label: '持续时间', value: '0.72s / 0.50s', ok: true },
  { label: '置信度', value: '91% / 70%', ok: true },
  { label: '确认状态', value: '已触发控制反馈', ok: true }
]

const handBones = [
  ['wrist','thumb_tip'],['wrist','index_tip'],['wrist','middle_tip'],
  ['wrist','ring_tip'],['wrist','pinky_tip']
]

function getKp(hand, name) {
  return hand.keypoints?.find(k => k.name === name) || { x: 0, y: 0 }
}

function triggerAction(action) {
  // mock触发
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
  object-fit: cover;
  opacity: 0.88;
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
</style>
