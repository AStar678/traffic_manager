<template>
  <div
    class="multi-camera-detail"
    data-stream-source="backend-processed-jpeg"
    :data-stream-count="cameraJpegFrameCount"
  >
    <header class="detail-status-bar">
      <div>
        <span>{{ taskTitle }}</span>
        <strong>{{ focusedSlotId ? `CAM ${focusedSlotId} 放大查看` : '三路并发感知' }}</strong>
      </div>
      <div class="detail-live" :class="{ off: !recognizing }"><i></i>{{ recognizing ? '持续识别中' : '识别已关闭' }}</div>
    </header>

    <section class="camera-result-grid" :class="{ focused: focusedSlotId }">
      <article
        v-for="camera in visibleCameras"
        :key="camera.slotId"
        class="camera-result-card"
        :class="[camera.status, { expanded: focusedSlotId === camera.slotId }]"
      >
        <div class="camera-result-head">
          <div><span>CAM {{ camera.slotId }}</span><strong>{{ camera.cameraName || camera.name }}</strong></div>
          <small>{{ sourceTypeLabel(camera.sourceType) }}</small>
        </div>

        <div class="camera-result-viewport">
          <img v-if="cameraPreviewUrls[camera.slotId]" :src="cameraPreviewUrls[camera.slotId]" :alt="`摄像头 ${camera.slotId} 后端叠框 JPEG`">
          <div v-else class="camera-result-empty">
            <el-icon :size="34"><VideoCamera /></el-icon>
            <span>{{ cameraFramePlaceholder(camera) }}</span>
          </div>
          <StaticWeatherTexture v-if="camera.weatherSimulationEnabled && hasCameraMedia(camera)" />
          <div class="camera-frame-label">
            <span>{{ camera.status === 'error' ? '异常' : (recognizing && camera.sourceType !== 'OFF' ? 'BACKEND AI' : 'OFF') }}</span>
            <small>{{ cameraTransportLabel(camera) }}</small>
          </div>
        </div>

        <aside class="camera-result-side">
          <div class="result-panel-title">
            <span>识别结果</span>
            <small>CAM {{ camera.slotId }}</small>
          </div>

          <div v-if="taskType === 'license_plate'" class="camera-detections plate-detections">
            <div v-for="item in detectionsFor(camera)" :key="item.objectId || item.plateNumber">
              <strong>{{ item.plateNumber || '未知车牌' }}</strong>
              <span>{{ plateColorName(item) }}</span>
              <small>置信度 {{ confidence(item) }}</small>
            </div>
            <p v-if="!detectionsFor(camera).length">{{ camera.sourceType === 'OFF' ? '该路已关闭' : '暂无车牌' }}</p>
          </div>

          <div v-else-if="taskType === 'vehicle_type'" class="camera-detections vehicle-detections">
            <div v-for="item in detectionsFor(camera)" :key="item.objectId || item.trackId">
              <strong>{{ vehicleTypeName(item) }}</strong>
              <span>轨迹 #{{ item.trackId ?? '--' }} · {{ vehicleColorName(item) }}</span>
              <small>置信度 {{ confidence(item) }}</small>
            </div>
            <p v-if="!detectionsFor(camera).length">{{ camera.sourceType === 'OFF' ? '该路已关闭' : '暂无车辆' }}</p>
          </div>

          <div v-else class="camera-detections police-detection">
            <template v-if="detectionsFor(camera).length">
              <strong>{{ detectionsFor(camera)[0].gestureName || '姿态识别中' }}</strong>
              <span>{{ detectionsFor(camera)[0].action || '等待交通指令' }}</span>
              <small>{{ confidence(detectionsFor(camera)[0]) }}</small>
            </template>
            <p v-else>{{ camera.sourceType === 'OFF' ? '该路已关闭' : '暂无交通手势' }}</p>
          </div>

          <button
            class="camera-zoom-button"
            type="button"
            :aria-label="focusedSlotId ? '返回三路摄像头视图' : `放大摄像头 ${camera.slotId}`"
            @click="toggleCameraFocus(camera.slotId)"
          >
            <el-icon><component :is="focusedSlotId ? 'Grid' : 'FullScreen'" /></el-icon>
            {{ focusedSlotId ? '返回三路视图' : '放大查看' }}
          </button>
        </aside>
      </article>
    </section>

    <footer class="detail-summary">
      <div><span>开启摄像头</span><strong>{{ activeCount }} / 3</strong></div>
      <div><span>识别结果</span><strong>{{ totalDetections }}</strong></div>
      <div><span>三路总耗时</span><strong>{{ renderResult?.latencyMs || 0 }} ms</strong></div>
      <div><span>传输方式</span><strong>JPEG · 精确帧后端叠框</strong></div>
    </footer>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import StaticWeatherTexture from '@/components/common/StaticWeatherTexture.vue'
import { useProcessedCameraStreams } from '@/composables/useCameraSource'

const props = defineProps({
  taskType: { type: String, required: true },
  result: { type: Object, default: () => ({}) },
  recognizing: { type: Boolean, default: false }
})

const focusedSlotId = ref(null)
const resultSource = useProcessedCameraStreams(props.taskType)
const { cameraSlots, cameraPreviewUrls } = resultSource
const cameraJpegFrameCount = computed(() => Object.keys(cameraPreviewUrls || {}).length)
const renderResult = computed(() => props.result || {})

const cameras = computed(() => {
  const resultCameras = renderResult.value?.cameras || []
  const baseCameras = cameraSlots.value.length ? cameraSlots.value : resultCameras
  return baseCameras.map(slot => ({
    ...slot,
    ...resultCameras.find(item => item.slotId === slot.slotId)
  }))
})
const visibleCameras = computed(() => focusedSlotId.value
  ? cameras.value.filter(camera => camera.slotId === focusedSlotId.value)
  : cameras.value
)
const activeCount = computed(() => cameras.value.filter(slot => slot.sourceType !== 'OFF').length)
const totalDetections = computed(() => renderResult.value?.detectionCount ?? renderResult.value?.detections?.length ?? 0)
const taskTitle = computed(() => ({
  license_plate: '车牌识别',
  vehicle_type: '车辆类型识别',
  police_gesture: '交警手势'
}[props.taskType] || props.taskType))

function toggleCameraFocus(slotId) {
  focusedSlotId.value = focusedSlotId.value === slotId ? null : slotId
}

function detectionsFor(camera) {
  if (camera.result?.detections) return camera.result.detections
  return (renderResult.value?.detections || []).filter(item => item.cameraSlotId === camera.slotId)
}

function hasCameraMedia(camera) {
  return Boolean(cameraPreviewUrls[camera.slotId])
}

function cameraFramePlaceholder(camera) {
  if (camera.sourceType === 'OFF') return '已关闭'
  if (camera.error) return camera.error
  return props.recognizing ? '正在生成后端叠框 JPEG' : '识别已关闭'
}

function cameraTransportLabel() {
  return 'JPEG · 后端已处理'
}

function confidence(item) {
  const value = Number(item.ocrConfidence ?? item.confidence)
  return Number.isFinite(value) ? `${Math.round(value * 100)}%` : '--'
}

function plateColorKey(item) {
  const value = String(item?.plateColor || item?.plateType || '').toLowerCase()
  if (value.includes('blue') || value.includes('蓝')) return 'blue'
  if (value.includes('green') || value.includes('绿') || value.includes('新能源')) return 'green'
  if (value.includes('yellow') || value.includes('黄')) return 'yellow'
  if (value.includes('white') || value.includes('白')) return 'white'
  if (value.includes('black') || value.includes('黑')) return 'black'
  return 'unknown'
}

function plateColorName(item) {
  return { blue: '蓝色', green: '绿色', yellow: '黄色', white: '白色', black: '黑色', unknown: '颜色未知' }[plateColorKey(item)]
}

function vehicleTypeName(item) {
  return item?.vehicleTypeName || {
    sedan: '轿车', suv: 'SUV', van: '面包车', hatchback: '两厢车', mpv: 'MPV',
    pickup: '皮卡', bus: '客车', truck: '货车', estate: '旅行车', unknown: '未知车型'
  }[String(item?.vehicleType || 'unknown').toLowerCase()] || item?.vehicleType || '未知车型'
}

function vehicleColorName(item) {
  const key = String(item?.vehicleColor || 'unknown').toLowerCase()
  return {
    black: '黑色', white: '白色', gray: '灰色', silver: '银色', red: '红色',
    blue: '蓝色', green: '绿色', yellow: '黄色', brown: '棕色', unknown: '颜色未知'
  }[key] || item?.vehicleColor || '颜色未知'
}

function sourceTypeLabel(value) {
  return { SANDBOX: '沙盘', RTSP: '真实视频流', IMAGE: '图片', VIDEO: '视频', DEVICE: '本机设备', OFF: '关闭' }[value] || value
}
</script>

<style scoped>
.multi-camera-detail { min-height: 100%; display: flex; flex-direction: column; gap: 14px; }
.detail-status-bar { display: flex; align-items: center; justify-content: space-between; gap: 14px; padding: 11px 14px; border: 1px solid var(--border-card); border-radius: 11px; background: var(--bg-card); }
.detail-status-bar span, .detail-status-bar strong { display: block; }
.detail-status-bar span { color: var(--text-secondary); font-size: 12px; }
.detail-status-bar strong { margin-top: 2px; font-size: 15px; }
.detail-live { display: inline-flex; align-items: center; gap: 7px; color: var(--success-color); font-size: 12px; font-weight: 800; }
.detail-live i { width: 8px; height: 8px; border-radius: 50%; background: currentColor; box-shadow: 0 0 10px currentColor; }
.detail-live.off { color: var(--text-muted); }
.camera-result-grid { flex: 1; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
.camera-result-grid.focused { grid-template-columns: minmax(0, 1fr); }
.camera-result-card { min-width: 0; display: flex; flex-direction: column; gap: 10px; padding: 11px; border: 1px solid var(--border-card); border-radius: var(--radius-md); background: var(--bg-card); }
.camera-result-card.expanded { display: grid; grid-template-columns: minmax(0, 1fr) minmax(280px, 340px); grid-template-areas: "head head" "viewport side"; align-items: stretch; border-color: var(--border-active); box-shadow: 0 0 24px rgba(0,180,216,.1); }
.camera-result-card.error { border-color: rgba(255,61,0,.3); }
.camera-result-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.camera-result-head div { min-width: 0; }
.camera-result-head span, .camera-result-head strong { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.camera-result-head span { color: var(--primary-color); font: 800 11px/1 "SF Mono", monospace; }
.camera-result-head strong { margin-top: 4px; font-size: 13px; }
.camera-result-head small { flex: 0 0 auto; color: var(--text-secondary); font-size: 11px; }
.camera-result-card.expanded .camera-result-head { grid-area: head; }
.camera-result-viewport { position: relative; aspect-ratio: 16/9; overflow: hidden; border-radius: 10px; background: #070b12; }
.camera-result-viewport img { width: 100%; height: 100%; display: block; object-fit: contain; }
.camera-result-card.expanded .camera-result-viewport { grid-area: viewport; height: clamp(380px, 62vh, 680px); aspect-ratio: auto; }
.camera-result-card.expanded .camera-result-viewport img { object-fit: contain; }
.camera-result-empty { height: 100%; display: grid; place-content: center; justify-items: center; gap: 8px; color: var(--text-secondary); font-size: 12px; }
.camera-frame-label { position: absolute; z-index: 3; left: 8px; right: 8px; bottom: 8px; display: flex; justify-content: space-between; padding: 5px 7px; border-radius: 6px; background: rgba(8,12,20,.76); }
.camera-frame-label span { color: var(--success-color); font: 800 11px/1 "SF Mono", monospace; }
.camera-frame-label small { color: #b7c3d6; font-size: 11px; }
.camera-result-side { min-width: 0; display: flex; flex: 1; flex-direction: column; gap: 10px; }
.camera-result-card.expanded .camera-result-side { grid-area: side; padding: 16px; border: 1px solid var(--border-card); border-radius: 10px; background: rgba(8,12,20,.55); }
.result-panel-title { display: none; align-items: center; justify-content: space-between; padding-bottom: 12px; border-bottom: 1px solid var(--border-card); }
.result-panel-title span { color: var(--text-primary); font-size: 15px; font-weight: 800; }
.result-panel-title small { color: var(--primary-color); font: 800 11px/1 "SF Mono", monospace; }
.camera-result-card.expanded .result-panel-title { display: flex; }
.camera-detections { min-height: 86px; overflow-y: auto; }
.plate-detections div { display: grid; grid-template-columns: 1fr auto auto; gap: 7px; padding: 7px 5px; border-bottom: 1px solid var(--border-subtle); }
.plate-detections strong { color: var(--text-primary); font: 800 13px/1 "SF Mono", monospace; }
.plate-detections span, .plate-detections small { color: var(--text-secondary); font-size: 11px; }
.camera-result-card.expanded .plate-detections div { grid-template-columns: 1fr; gap: 8px; padding: 14px 12px; border: 1px solid var(--border-card); border-radius: 9px; background: var(--bg-card); }
.camera-result-card.expanded .plate-detections strong { font-size: 18px; }
.vehicle-detections div { display: grid; gap: 5px; padding: 8px 5px; border-bottom: 1px solid var(--border-subtle); }
.vehicle-detections strong { color: var(--text-primary); font-size: 13px; }
.vehicle-detections span, .vehicle-detections small { color: var(--text-secondary); font-size: 11px; }
.camera-result-card.expanded .vehicle-detections div { padding: 14px 12px; border: 1px solid var(--border-card); border-radius: 9px; background: var(--bg-card); }
.camera-result-card.expanded .vehicle-detections strong { color: var(--primary-color); font-size: 18px; }
.police-detection { display: grid; place-content: center; text-align: center; }
.police-detection strong { font-size: 18px; } .police-detection span { margin-top: 6px; color: var(--text-secondary); font-size: 13px; } .police-detection small { margin-top: 5px; color: var(--warning-color); font-size: 12px; }
.camera-result-card.expanded .police-detection { place-content: start; padding: 18px 12px; border: 1px solid var(--border-card); border-radius: 9px; background: var(--bg-card); text-align: left; }
.camera-result-card.expanded .police-detection strong { font-size: 24px; }
.camera-detections p { padding: 24px 4px; color: var(--text-secondary); font-size: 12px; text-align: center; }
.camera-zoom-button { width: 100%; min-height: 40px; display: inline-flex; align-items: center; justify-content: center; gap: 7px; margin-top: auto; border: 1px solid var(--border-card); border-radius: 9px; color: var(--text-primary); background: rgba(255,255,255,.055); cursor: pointer; font-family: inherit; font-size: 12px; font-weight: 700; line-height: 1; transition: border-color var(--duration-fast) var(--ease-out), color var(--duration-fast) var(--ease-out), background var(--duration-fast) var(--ease-out); }
.camera-zoom-button:hover, .camera-zoom-button:focus-visible { border-color: var(--border-active); color: var(--primary-color); background: rgba(0,180,216,.08); outline: none; }
.camera-result-card.expanded .camera-zoom-button { color: var(--primary-color); border-color: rgba(0,180,216,.35); }
.detail-summary { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; }
.detail-summary div { padding: 9px 11px; border: 1px solid var(--border-card); border-radius: 9px; background: rgba(255,255,255,.025); }
.detail-summary span, .detail-summary strong { display: block; } .detail-summary span { color: var(--text-secondary); font-size: 11px; } .detail-summary strong { margin-top: 4px; font-size: 13px; }
@media (max-width: 900px) { .camera-result-grid { grid-template-columns: 1fr; } .camera-result-card.expanded { display: flex; } .camera-result-card.expanded .camera-result-viewport { height: min(52vh, 480px); } .camera-result-card.expanded .camera-result-side { padding: 12px; } .detail-summary { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 480px) { .detail-summary { grid-template-columns: 1fr; } }
</style>
