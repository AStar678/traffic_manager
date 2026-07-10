<template>
  <div class="dashboard">
    <!-- 核心驾驶信息：速度 + 档位 -->
    <div class="hero-row">
      <!-- 速度表区域 -->
      <div class="speedo-section">
        <div class="speed-ring">
          <svg viewBox="0 0 200 200" class="speed-svg">
            <circle cx="100" cy="100" r="88" fill="none" stroke="rgba(255,255,255,0.04)" stroke-width="10" />
            <circle
              cx="100" cy="100" r="88"
              fill="none"
              stroke="url(#speedGrad)"
              stroke-width="10"
              stroke-linecap="round"
              :stroke-dasharray="`${(vehicle.speed / 120) * 553} 553`"
              stroke-dashoffset="0"
              transform="rotate(-90 100 100)"
              class="speed-arc"
            />
            <defs>
              <linearGradient id="speedGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="#00b4d8" />
                <stop offset="100%" stop-color="#00e5ff" />
              </linearGradient>
            </defs>
          </svg>
          <div class="speed-value">
            <strong>{{ vehicle.speed }}</strong>
            <span>km/h</span>
          </div>
        </div>
        <!-- 档位 -->
        <div class="gear-badge">
          <span>档位</span>
          <strong>{{ vehicle.gear }}</strong>
        </div>
      </div>

      <!-- 中央：前置摄像头画面 -->
      <div class="camera-feed card">
        <div class="camera-inner">
          <video
            v-show="cameraVideoReady"
            ref="cameraVideoRef"
            class="camera-stream"
            autoplay
            muted
            playsinline
            @loadeddata="markCameraVideoReady"
            @playing="markCameraVideoReady"
          ></video>
          <img
            v-if="!cameraVideoReady && cameraDisplayUrl"
            class="camera-stream"
            :src="cameraDisplayUrl"
            alt="前置摄像头降级预览"
          >
          <div v-if="!cameraVideoReady && !cameraDisplayUrl" class="camera-placeholder">
            <el-icon :size="42"><Camera /></el-icon>
            <span>{{ cameraError || '等待摄像头服务' }}</span>
          </div>
          <div class="camera-overlay-info">
            <span class="camera-label">{{ selectedCameraSource?.name || '前置摄像头' }}</span>
            <span class="camera-live">● {{ cameraStatusText }}</span>
          </div>
          <div class="scan-line-animated"></div>
          <!-- 检测到车牌时显示浮层 -->
          <div class="detection-hint" v-if="vehicle.policeDetection.detected">
            <span class="status-dot warning"></span>
            检测到交警 · 置信度 {{ Math.round(vehicle.policeDetection.confidence * 100) }}%
            <button class="action-pill" @click="$router.push('/police-gesture')">查看</button>
          </div>
        </div>
      </div>

      <!-- 右侧：车辆健康状态卡片 -->
      <div class="health-stack">
        <div class="card health-item" v-for="item in health.slice(0, 3)" :key="item.name">
          <div class="health-head">
            <span>{{ item.name }}</span>
            <span class="status-dot" :class="item.status === 'normal' ? 'online' : 'warning'"></span>
          </div>
          <strong>{{ item.value }}</strong>
          <p>{{ item.detail }}</p>
        </div>
      </div>
    </div>

    <!-- 第二行：车辆状态 + 快捷操作 -->
    <div class="secondary-row">
      <!-- 胎压 + 空调 -->
      <div class="card status-grid" :class="{ active: lastGestureControl?.actionType?.startsWith('CLIMATE') }">
        <h3 class="card-title">车辆状态</h3>
        <div class="status-items">
          <div
            v-for="tire in vehicle.tirePressure"
            :key="tire.name"
            class="status-item"
            :class="{ alert: tire.status === 'warning' }"
          >
            <el-icon><Location /></el-icon>
            <div>
              <strong>{{ tire.value }} <small>bar</small></strong>
              <span>{{ tire.name }}胎压</span>
            </div>
          </div>
        </div>
        <div class="gradient-divider"></div>
        <div class="climate-row">
          <div class="climate-icon">
            <el-icon :size="28"><Sunny /></el-icon>
          </div>
          <div class="climate-info">
            <strong>{{ vehicle.climate.temperature }}°C</strong>
            <span>空调 · {{ vehicle.climate.mode }}</span>
          </div>
        </div>
      </div>

      <!-- 多媒体卡片 -->
      <div class="card media-card" :class="{ active: ['VOLUME_UP', 'VOLUME_DOWN', 'NEXT_MEDIA'].includes(lastGestureControl?.actionType) }">
        <h3 class="card-title">正在播放</h3>
        <div class="media-art">
          <el-icon :size="40"><Headset /></el-icon>
        </div>
        <strong class="media-track">{{ vehicle.audio.track }}</strong>
        <span class="media-meta">音量 {{ vehicle.audio.volume }}%</span>
        <div class="media-controls">
          <el-button circle><el-icon><VideoPlay /></el-icon></el-button>
          <el-button circle><el-icon><ArrowRight /></el-icon></el-button>
        </div>
      </div>

      <!-- 电话状态 -->
      <div class="card phone-card" :class="{ active: ['ANSWER_CALL', 'HANG_UP'].includes(lastGestureControl?.actionType) }">
        <h3 class="card-title">电话</h3>
        <div class="phone-status">
          <el-icon :size="36"><Phone /></el-icon>
          <strong>{{ vehicle.phone.status }}</strong>
          <span>{{ vehicle.phone.caller }}</span>
        </div>
      </div>

      <div class="card gesture-control-card" :class="{ active: lastGestureControl }">
        <h3 class="card-title">手势控制</h3>
        <div v-if="lastGestureControl" class="gesture-control-state">
          <span class="gesture-badge">{{ lastGestureControl.gestureName }}</span>
          <strong>{{ lastGestureControl.actionLabel }}</strong>
          <small>{{ lastControlTime }} · 置信度 {{ Math.round(lastGestureControl.confidence * 100) }}%</small>
        </div>
        <div v-else class="gesture-control-empty">
          <el-icon :size="32"><Pointer /></el-icon>
          <span>等待手势控制</span>
        </div>
        <button class="gesture-open-button" type="button" @click="$router.push('/owner-gesture')">打开手势控车</button>
      </div>

      <!-- 告警快捷入口 -->
      <div class="card alert-card">
        <h3 class="card-title">系统告警</h3>
        <div class="alert-mini" v-for="alert in recentAlerts" :key="alert.id" @click="$router.push('/alert-dashboard')">
          <span class="status-dot" :class="alert.severity === 'CRITICAL' ? 'offline' : 'warning'"></span>
          <div>
            <strong>{{ alert.title }}</strong>
            <span>{{ alert.occurredAt }}</span>
          </div>
        </div>
        <button class="action-link" @click="$router.push('/alert-dashboard')">查看全部 →</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { mockSystemHealth, mockAlerts } from '@/utils/mockData'
import { useAlertStore } from '@/stores/alert'
import { useCameraSource } from '@/composables/useCameraSource'
import { useVehicleStore } from '@/stores/vehicle'

const alertStore = useAlertStore()
const vehicleStore = useVehicleStore()
const vehicle = vehicleStore.vehicle
const health = mockSystemHealth
const {
  selectedCameraSource,
  cameraStatus,
  cameraError,
  cameraDisplayUrl,
  cameraVideoRef,
  cameraVideoReady,
  markCameraVideoReady,
  refreshCameraPreview
} = useCameraSource()

const cameraStatusText = computed(() => {
  const labels = { idle: '待机', loading: '连接中', ready: 'LIVE', empty: '无源', offline: '离线' }
  return labels[cameraStatus.value] || cameraStatus.value
})
const lastGestureControl = computed(() => vehicleStore.lastGestureControl)
const lastControlTime = computed(() => {
  const timestamp = lastGestureControl.value?.triggeredAt
  if (!timestamp) return '--'
  return new Date(timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
})

onMounted(() => {
  alertStore.fetchAlerts()
  refreshCameraPreview()
})

const recentAlerts = computed(() => mockAlerts.slice(0, 2))
</script>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ===== 第一行：速度 + 摄像头 + 健康状态 ===== */
.hero-row {
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr) 280px;
  gap: 16px;
  min-height: 280px;
}

/* 速度表 */
.speedo-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.speed-ring {
  position: relative;
  width: 200px;
  height: 200px;
}

.speed-svg {
  width: 100%;
  height: 100%;
}

.speed-arc {
  transition: stroke-dasharray 600ms var(--ease-out);
}

.speed-value {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.speed-value strong {
  font-size: 64px;
  font-weight: 700;
  line-height: 1;
  letter-spacing: -2px;
  color: var(--text-primary);
}

.speed-value span {
  margin-top: 4px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
  letter-spacing: 1px;
}

.gear-badge {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px 28px;
  background: linear-gradient(135deg, var(--primary-color), #0096c7);
  border-radius: var(--radius-lg);
}

.gear-badge span {
  font-size: 11px;
  font-weight: 600;
  color: rgba(8, 12, 20, 0.7);
  letter-spacing: 1px;
  text-transform: uppercase;
}

.gear-badge strong {
  font-size: 36px;
  font-weight: 800;
  color: #080c14;
  line-height: 1;
}

/* 摄像头画面 */
.camera-feed {
  padding: 0;
  overflow: hidden;
  border-radius: var(--radius-lg);
}

.camera-inner {
  position: relative;
  height: 100%;
  min-height: 280px;
  background:
    linear-gradient(180deg, rgba(8,12,20,0.15) 0%, rgba(8,12,20,0.55) 100%),
    radial-gradient(ellipse at 50% 70%, #1a2940 0%, #0a1220 70%);
  display: flex;
  align-items: flex-end;
}

.camera-stream {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
  opacity: 0.9;
  background: #070b12;
}

.camera-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: var(--text-muted);
  font-size: 13px;
  font-weight: 700;
  background:
    linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px),
    linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px);
  background-size: 40px 40px;
}

.camera-overlay-info {
  position: absolute;
  top: 14px;
  left: 18px;
  right: 18px;
  display: flex;
  justify-content: space-between;
}

.camera-label {
  font-size: 13px;
  font-weight: 700;
  color: rgba(255,255,255,0.85);
}

.camera-live {
  font-size: 12px;
  font-weight: 700;
  color: var(--danger-color);
  animation: pulseNumber 1.5s ease-in-out infinite;
}

.detection-hint {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 12px 18px;
  background: rgba(255, 171, 0, 0.12);
  border-top: 1px solid rgba(255, 171, 0, 0.2);
  color: var(--warning-color);
  font-size: 14px;
  font-weight: 600;
}

.action-pill {
  margin-left: auto;
  padding: 6px 16px;
  border: 1px solid var(--warning-color);
  border-radius: 999px;
  background: transparent;
  color: var(--warning-color);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: all var(--duration-fast);
}

.action-pill:hover {
  background: var(--warning-color);
  color: #080c14;
}

/* 健康状态 */
.health-stack {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.health-item {
  padding: 14px 16px;
}

.health-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.health-head span {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-secondary);
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.health-item strong {
  display: block;
  margin-top: 6px;
  font-size: 18px;
  color: var(--text-primary);
}

.health-item p {
  margin-top: 4px;
  font-size: 12px;
  color: var(--text-muted);
}

/* ===== 第二行 ===== */
.secondary-row {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 16px;
}

.secondary-row .card.active {
  border-color: rgba(0,180,216,0.35);
  box-shadow: 0 0 22px var(--primary-glow);
}

.card-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 14px;
}

/* 车辆状态 */
.status-grid { }

.status-items {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  background: rgba(255,255,255,0.03);
  border-radius: var(--radius-sm);
  transition: background var(--duration-fast);
}

.status-item.alert {
  background: rgba(255, 171, 0, 0.08);
  border: 1px solid rgba(255, 171, 0, 0.15);
}

.status-item .el-icon {
  color: var(--text-muted);
  font-size: 20px;
}

.status-item strong {
  display: block;
  font-size: 16px;
  color: var(--text-primary);
}

.status-item strong small {
  font-size: 11px;
  color: var(--text-muted);
}

.status-item span {
  font-size: 11px;
  color: var(--text-muted);
}

.climate-row {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-top: 8px;
}

.climate-icon {
  width: 48px;
  height: 48px;
  display: grid;
  place-items: center;
  background: rgba(255,255,255,0.04);
  border-radius: var(--radius-sm);
  color: var(--warning-color);
}

.climate-info strong {
  display: block;
  font-size: 22px;
  color: var(--text-primary);
}

.climate-info span {
  font-size: 12px;
  color: var(--text-muted);
}

/* 多媒体 */
.media-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.media-art {
  width: 64px;
  height: 64px;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, #1a2940, #253a56);
  border-radius: var(--radius-md);
  margin-bottom: 12px;
  color: var(--primary-color);
}

.media-track {
  font-size: 15px;
  color: var(--text-primary);
}

.media-meta {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
}

.media-controls {
  display: flex;
  gap: 10px;
  margin-top: 14px;
}

/* 电话 */
.phone-card { }

.phone-status {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 16px 0;
}

.phone-status .el-icon {
  color: var(--success-color);
}

.phone-status strong {
  font-size: 18px;
  color: var(--text-primary);
}

.phone-status span {
  font-size: 12px;
  color: var(--text-muted);
}

/* 手势控制 */
.gesture-control-card {
  min-height: 180px;
}

.gesture-control-state,
.gesture-control-empty {
  min-height: 96px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  text-align: center;
}

.gesture-badge {
  max-width: 100%;
  padding: 5px 10px;
  border-radius: 999px;
  border: 1px solid rgba(0,180,216,0.3);
  background: var(--primary-soft);
  color: var(--primary-color);
  font-size: 12px;
  font-weight: 800;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.gesture-control-state strong {
  font-size: 17px;
  color: var(--text-primary);
}

.gesture-control-state small,
.gesture-control-empty span {
  font-size: 12px;
  color: var(--text-muted);
}

.gesture-control-empty .el-icon {
  color: var(--text-muted);
}

.gesture-open-button {
  width: 100%;
  min-height: 34px;
  border: 1px solid rgba(0, 180, 216, 0.34);
  border-radius: 8px;
  color: var(--primary-color);
  background: rgba(0, 180, 216, 0.1);
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
}

.gesture-open-button:hover {
  border-color: rgba(0, 180, 216, 0.56);
  background: rgba(0, 180, 216, 0.16);
}

/* 告警快捷卡片 */
.alert-card { }

.alert-mini {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 0;
  cursor: pointer;
  transition: opacity var(--duration-fast);
}

.alert-mini:hover {
  opacity: 0.8;
}

.alert-mini + .alert-mini {
  border-top: 1px solid var(--border-subtle);
}

.alert-mini strong {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.3;
}

.alert-mini span {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 2px;
}

.action-link {
  display: inline-block;
  margin-top: 10px;
  padding: 0;
  border: none;
  background: none;
  color: var(--primary-color);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: color var(--duration-fast);
}

.action-link:hover {
  color: #00e5ff;
}

@media (max-width: 1200px) {
  .hero-row {
    grid-template-columns: 1fr;
  }
  .secondary-row {
    grid-template-columns: repeat(2, 1fr);
  }
  .speedo-section {
    flex-direction: row;
    justify-content: center;
  }
}
</style>
