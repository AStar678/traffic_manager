<template>
  <div class="dashboard">
    <div class="hero-row">
      <!-- 左：速度表 + 档位 + 续航 -->
      <div class="speedo-col">
        <div class="speed-ring">
          <svg viewBox="0 0 200 200">
            <defs>
              <linearGradient id="speedGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="#1a73e8" /><stop offset="100%" stop-color="#4a9af5" />
              </linearGradient>
            </defs>
            <circle cx="100" cy="100" r="86" fill="none" stroke="rgba(255,255,255,0.04)" stroke-width="8" />
            <circle cx="100" cy="100" r="86" fill="none" stroke="url(#speedGrad)" stroke-width="8"
              stroke-linecap="round" :stroke-dasharray="`${Math.min(1, vehicle.speed / 120) * 520} 520`"
              stroke-dashoffset="0" transform="rotate(-90 100 100)" class="speed-arc" />
          </svg>
          <div class="speed-num"><strong>{{ vehicle.speed }}</strong><span>km/h</span></div>
        </div>
        <div class="badge-row">
          <div class="gear-badge"><span>档位</span><strong>{{ vehicle.gear }}</strong></div>
          <div class="range-badge"><strong>{{ vehicle.range }}</strong><span>km</span></div>
        </div>
      </div>

      <!-- 中：摄像头画面 -->
      <div class="cam-card">
        <div class="cam-box">
          <!-- 始终渲染 video，id 定位避开 ref 时序问题，去掉 transform 防 Edge 渲染bug -->
          <video
            id="dash-cam"
            class="cam-video"
            :style="{ opacity: camActive ? 1 : 0 }"
            autoplay playsinline muted
          ></video>

          <!-- 降级占位 -->
          <div v-if="!camActive" class="cam-start" @click="openCamera">
            <el-icon :size="48"><VideoCamera /></el-icon>
            <strong v-if="camError">{{ camError }}</strong>
            <strong v-else>摄像头启动中...</strong>
          </div>

          <div v-if="camActive" class="scan-line-animated"></div>

          <div class="cam-top">
            <span v-if="camActive" class="tag live">● LIVE</span>
            <span v-else class="tag">○ 待机</span>
            <span class="tag adas">ADAS</span>
          </div>

          <!-- 自动检测气泡 -->
          <div v-if="camActive && detection.police" class="detect-toast police" @click="$router.push('/police-gesture')">
            <span class="toast-icon">👮</span>
            <div class="toast-body">
              <strong>检测到交警手势</strong>
              <span>{{ detection.police.name }} · 置信度 {{ detection.police.conf }}%</span>
            </div>
            <span class="toast-arrow">查看详情 →</span>
          </div>
          <div v-if="camActive && detection.plate" class="detect-toast plate" @click="$router.push('/license-plate')">
            <span class="toast-icon">🚗</span>
            <div class="toast-body">
              <strong>检测到车牌</strong>
              <span>{{ detection.plate.number }} · {{ detection.plate.type }}</span>
            </div>
            <span class="toast-arrow">查看详情 →</span>
          </div>

          <button v-if="camActive" class="cam-flip" @click="flipCamera" title="切换摄像头">
            <el-icon><Switch /></el-icon>
          </button>
        </div>
      </div>

      <!-- 右：系统状态 -->
      <div class="status-col">
        <div class="card s-card" v-for="s in statusCards" :key="s.label">
          <div class="s-head"><span>{{ s.label }}</span><span class="status-dot" :class="s.dot"></span></div>
          <strong>{{ s.val }}</strong><p>{{ s.desc }}</p>
        </div>
      </div>
    </div>

    <div class="info-row">
      <div class="card"><h4>胎压监测</h4>
        <div class="tire-grid">
          <div v-for="t in vehicle.tirePressure" :key="t.name" class="tire-item" :class="{ warn: t.status === 'warning' }">
            <span>{{ t.name }}</span><strong>{{ t.value }}<small>bar</small></strong>
          </div>
        </div>
      </div>
      <div class="card"><h4>空调</h4>
        <div class="climate"><el-icon :size="28"><Sunny /></el-icon><strong>{{ vehicle.climate.temperature }}°</strong><span>{{ vehicle.climate.mode }} · 风量 {{ vehicle.climate.fan }}</span></div>
      </div>
      <div class="card"><h4>正在播放</h4>
        <div class="media"><div class="media-art"><el-icon :size="28"><Headset /></el-icon></div><div><strong>{{ vehicle.audio.track }}</strong><span>音量 {{ vehicle.audio.volume }}%</span></div></div>
      </div>
      <div class="card"><h4>电话</h4>
        <div class="phone"><el-icon :size="28"><Phone /></el-icon><strong>{{ vehicle.phone.status }}</strong><span>{{ vehicle.phone.caller }}</span></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted, onBeforeUnmount } from 'vue'
import { mockVehicleState, mockSystemHealth } from '@/utils/mockData'

const vehicle = mockVehicleState
const health = mockSystemHealth

// ===== 摄像头（最简实现，绕过所有 Edge 坑） =====
const camActive = ref(false)
const camError = ref('')
let camStream = null

async function openCamera() {
  if (camStream) return
  camError.value = ''

  try {
    // 1. 获取流
    camStream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'user' },
      audio: false,
    })

    // 2. 先让 video 可见（不用 ref，直接 DOM 查询，彻底绕开 ref 时序）
    camActive.value = true
    await new Promise(r => setTimeout(r, 200))

    // 3. 用原生 DOM 绑定
    const el = document.querySelector('#dash-cam')
    if (el) {
      el.srcObject = camStream
      try { await el.play() } catch (_) {}
    }
  } catch (err) {
    console.warn('[Camera]', err.name, err.message)
    if (err.name === 'NotAllowedError')
      camError.value = '摄像头权限被拒绝，请点击地址栏左侧锁图标 → 允许摄像头'
    else if (err.name === 'NotFoundError')
      camError.value = '未检测到摄像头设备'
    else {
      // 最宽松重试
      try {
        camStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false })
        camActive.value = true
        await new Promise(r => setTimeout(r, 200))
        const el = document.querySelector('#dash-cam')
        if (el) { el.srcObject = camStream; try { await el.play() } catch (_) {} }
        camError.value = ''
        return
      } catch (_) {}
      camError.value = err.message
    }
  }
}

function closeCamera() {
  if (camStream) {
    camStream.getTracks().forEach(t => t.stop())
    camStream = null
  }
  camActive.value = false
}

async function flipCamera() {
  if (!camStream) return
  const facing = camStream.getVideoTracks()[0]?.getSettings()?.facingMode
  closeCamera()
  try {
    camStream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 1280 }, height: { ideal: 720 },
        facingMode: facing === 'user' ? 'environment' : 'user' },
      audio: false,
    })
    camActive.value = true
    await new Promise(r => setTimeout(r, 200))
    const el = document.querySelector('#dash-cam')
    if (el) { el.srcObject = camStream; try { await el.play() } catch (_) {} }
  } catch (err) {
    camError.value = '切换失败: ' + err.message
  }
}

// ===== 自动检测模拟 =====
const detection = reactive({ police: null, plate: null })
let detectTimer = null

function simulateDetection() {
  if (!camActive.value) { detection.police = null; detection.plate = null; return }
  const r = Math.random()
  if (r < 0.35) {
    detection.police = { name: '停止信号', conf: 93 }; detection.plate = null
  } else if (r < 0.65) {
    detection.police = null; detection.plate = { number: '京A12345', type: '蓝牌小型车' }
  } else if (r < 0.85) {
    detection.police = { name: '直行信号', conf: 87 }; detection.plate = { number: '沪B8K218', type: '新能源车牌' }
  } else {
    detection.police = null; detection.plate = null
  }
}

const statusCards = [
  { label: '模型服务', val: health[0].value, desc: health[0].detail, dot: health[0].status === 'normal' ? 'online' : 'warning-dot' },
  { label: '后端服务', val: health[1].value, desc: health[1].detail, dot: health[1].status === 'normal' ? 'online' : 'warning-dot' },
  { label: '告警通道', val: health[2].value, desc: health[2].detail, dot: health[2].status === 'normal' ? 'online' : 'warning-dot' },
]

onMounted(async () => {
  await openCamera()
  detectTimer = setInterval(simulateDetection, 4000)
})

onBeforeUnmount(() => {
  clearInterval(detectTimer)
  closeCamera()
})
</script>

<style scoped>
.dashboard { display: flex; flex-direction: column; gap: 14px; }

.hero-row { display: grid; grid-template-columns: 185px minmax(0, 1fr) 240px; gap: 14px; min-height: 300px; }

.speedo-col { display: flex; flex-direction: column; align-items: center; gap: 10px; }
.speed-ring { position: relative; width: 170px; height: 170px; }
.speed-ring svg { width: 100%; height: 100%; }
.speed-arc { transition: stroke-dasharray 500ms var(--ease-out); filter: drop-shadow(0 0 8px rgba(26,115,232,0.3)); }
.speed-num { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.speed-num strong { font-size: 54px; font-weight: 700; line-height: 1; letter-spacing: -2px; color: var(--text-primary); }
.speed-num span { margin-top: 2px; font-size: 13px; font-weight: 600; color: var(--text-secondary); }

.badge-row { display: flex; gap: 8px; width: 100%; }
.gear-badge { flex: 1; display: flex; flex-direction: column; align-items: center; padding: 8px 0; background: var(--primary-color); border-radius: var(--radius-md); }
.gear-badge span { font-size: 10px; color: rgba(255,255,255,0.7); font-weight: 600; }
.gear-badge strong { font-size: 28px; color: #fff; font-weight: 800; line-height: 1; }
.range-badge { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 8px 0; background: var(--bg-card); border: 1px solid var(--border-card); border-radius: var(--radius-md); }
.range-badge strong { font-size: 22px; color: var(--success-color); }
.range-badge span { font-size: 10px; color: var(--text-muted); }

.cam-card { }
.cam-box {
  position: relative; height: 100%; min-height: 300px;
  border-radius: var(--radius-lg); overflow: hidden;
  background: #040810; border: 1px solid var(--border-subtle);
}
.cam-video {
  position: absolute; inset: 0; width: 100%; height: 100%;
  object-fit: cover; background: #000;
}
.cam-start {
  position: absolute; inset: 0;
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 10px;
  background: radial-gradient(ellipse at 50% 60%, #162035 0%, #080c14 70%);
  color: var(--text-secondary); cursor: pointer;
}
.cam-start .el-icon { color: var(--primary-color); }
.cam-start strong { font-size: 15px; color: var(--text-primary); text-align: center; max-width: 280px; line-height: 1.5; }
.cam-top { position: absolute; top: 10px; left: 12px; display: flex; gap: 6px; z-index: 6; }
.tag { padding: 3px 8px; border-radius: 999px; font-size: 10px; font-weight: 700; background: rgba(0,0,0,0.5); color: var(--text-secondary); backdrop-filter: blur(4px); }
.tag.live { color: var(--danger-color); }
.tag.adas { color: var(--success-color); border: 1px solid rgba(52,168,83,0.3); }

.cam-flip {
  position: absolute; bottom: 14px; right: 14px; z-index: 10;
  width: 32px; height: 32px; border-radius: 50%; border: 1px solid rgba(255,255,255,0.15);
  background: rgba(0,0,0,0.45); color: #fff; cursor: pointer; display: grid; place-items: center;
}
.cam-flip:hover { background: rgba(0,0,0,0.65); }

.detect-toast {
  position: absolute; left: 14px; right: 50px; display: flex; align-items: center; gap: 10px;
  padding: 10px 14px; border-radius: 12px; cursor: pointer; z-index: 8;
  backdrop-filter: blur(8px); animation: slideUp 300ms var(--ease-out);
}
.detect-toast:hover { transform: translateY(-1px); }
.detect-toast.police { bottom: 60px; background: rgba(234,67,53,0.15); border: 1px solid rgba(234,67,53,0.35); }
.detect-toast.plate { bottom: 14px; background: rgba(52,168,83,0.15); border: 1px solid rgba(52,168,83,0.35); }
.toast-icon { font-size: 22px; }
.toast-body strong { display: block; font-size: 13px; color: #fff; }
.toast-body span { font-size: 11px; color: rgba(255,255,255,0.7); }
.toast-arrow { margin-left: auto; font-size: 12px; color: rgba(255,255,255,0.5); font-weight: 600; white-space: nowrap; }

@keyframes slideUp { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }

.status-col { display: flex; flex-direction: column; gap: 8px; }
.s-card { padding: 13px 16px; }
.s-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
.s-head span { font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; }
.s-card > strong { font-size: 17px; color: var(--text-primary); }
.s-card > p { margin-top: 2px; font-size: 11px; color: var(--text-muted); }

.info-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }
.info-row h4 { font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px; }

.tire-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 6px; }
.tire-item { display: flex; flex-direction: column; align-items: center; padding: 8px; background: rgba(255,255,255,0.02); border-radius: 8px; border: 1px solid transparent; }
.tire-item.warn { background: rgba(251,188,4,0.06); border-color: rgba(251,188,4,0.15); }
.tire-item span { font-size: 10px; color: var(--text-muted); }
.tire-item strong { font-size: 16px; color: var(--text-primary); }
.tire-item.warn strong { color: var(--warning-color); }
.tire-item strong small { font-size: 10px; color: var(--text-muted); margin-left: 2px; }

.climate { display: flex; flex-direction: column; align-items: center; gap: 4px; }
.climate .el-icon { color: var(--warning-color); }
.climate strong { font-size: 28px; color: var(--text-primary); }
.climate span { font-size: 11px; color: var(--text-muted); }

.media { display: flex; align-items: center; gap: 12px; }
.media-art { width: 50px; height: 50px; display: grid; place-items: center; background: linear-gradient(135deg, #1a3050, #253a56); border-radius: var(--radius-md); color: var(--primary-color); }
.media strong { display: block; font-size: 13px; color: var(--text-primary); }
.media span { font-size: 11px; color: var(--text-muted); }

.phone { display: flex; flex-direction: column; align-items: center; gap: 4px; }
.phone .el-icon { color: var(--success-color); }
.phone strong { font-size: 15px; color: var(--text-primary); }
.phone span { font-size: 11px; color: var(--text-muted); }
</style>
