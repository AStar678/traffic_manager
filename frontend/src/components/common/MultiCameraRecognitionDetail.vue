<template>
  <div class="multi-camera-detail">
    <header class="detail-status-bar">
      <div>
        <span>{{ taskType === 'license_plate' ? '车牌识别' : '交警手势' }}</span>
        <strong>三路并发感知</strong>
      </div>
      <div class="detail-live" :class="{ off: !recognizing }"><i></i>{{ recognizing ? '持续识别中' : '识别已关闭' }}</div>
    </header>

    <section class="camera-result-grid">
      <article v-for="camera in cameras" :key="camera.slotId" class="camera-result-card" :class="camera.status">
        <div class="camera-result-head">
          <div><span>CAM {{ camera.slotId }}</span><strong>{{ camera.cameraName || camera.name }}</strong></div>
          <small>{{ sourceTypeLabel(camera.sourceType) }}</small>
        </div>

        <div class="camera-result-viewport">
          <img v-if="cameraPreviewUrls[camera.slotId]" :src="cameraPreviewUrls[camera.slotId]" :alt="`摄像头 ${camera.slotId}`">
          <div v-else class="camera-result-empty">
            <el-icon :size="34"><VideoCamera /></el-icon>
            <span>{{ camera.sourceType === 'OFF' ? '已关闭' : (camera.error || '等待文件帧') }}</span>
          </div>
          <svg
            v-if="taskType === 'license_plate' && cameraPreviewUrls[camera.slotId] && overlayDetections(camera).length"
            class="plate-box-overlay"
            :viewBox="imageViewBox(camera)"
            preserveAspectRatio="xMidYMid slice"
            aria-label="车牌检测框"
          >
            <g v-for="item in overlayDetections(camera)" :key="`box-${item.objectId || item.plateNumber}`">
              <rect
                class="plate-detect-box"
                :x="item.bbox.x1"
                :y="item.bbox.y1"
                :width="Math.max(1, item.bbox.x2 - item.bbox.x1)"
                :height="Math.max(1, item.bbox.y2 - item.bbox.y1)"
                :stroke="plateAccent(item)"
              />
              <g :transform="`translate(${plateLabelX(item, camera)}, ${plateLabelY(item, camera)})`">
                <rect
                  class="plate-box-label-bg"
                  :width="plateLabelWidth(item)"
                  height="64"
                  rx="10"
                  :stroke="plateAccent(item)"
                />
                <text class="plate-box-label" x="16" y="43">{{ plateOverlayLabel(item) }}</text>
              </g>
            </g>
          </svg>
          <div class="camera-frame-label">
            <span>{{ camera.status === 'error' ? '异常' : (recognizing && camera.sourceType !== 'OFF' ? 'LIVE' : 'OFF') }}</span>
            <small>文件帧直读</small>
          </div>
        </div>

        <div v-if="taskType === 'license_plate'" class="camera-detections plate-detections">
          <div v-for="item in detectionsFor(camera)" :key="item.objectId || item.plateNumber">
            <strong>{{ item.plateNumber || '未知车牌' }}</strong>
            <span>{{ plateColorName(item) }}</span>
            <small>置信度 {{ confidence(item) }}</small>
          </div>
          <p v-if="!detectionsFor(camera).length">{{ camera.sourceType === 'OFF' ? '该路已关闭' : '暂无车牌' }}</p>
        </div>

        <div v-else class="camera-detections police-detection">
          <template v-if="detectionsFor(camera).length">
            <strong>{{ detectionsFor(camera)[0].gestureName || '姿态识别中' }}</strong>
            <span>{{ detectionsFor(camera)[0].action || '等待交通指令' }}</span>
            <small>{{ confidence(detectionsFor(camera)[0]) }}</small>
          </template>
          <p v-else>{{ camera.sourceType === 'OFF' ? '该路已关闭' : '暂无交通手势' }}</p>
        </div>
      </article>
    </section>

    <footer class="detail-summary">
      <div><span>开启摄像头</span><strong>{{ activeCount }} / 3</strong></div>
      <div><span>识别结果</span><strong>{{ totalDetections }}</strong></div>
      <div><span>三路总耗时</span><strong>{{ result?.latencyMs || 0 }} ms</strong></div>
      <div><span>传输方式</span><strong>共享文件</strong></div>
    </footer>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useCameraSource } from '@/composables/useCameraSource'

const props = defineProps({
  taskType: { type: String, required: true },
  result: { type: Object, default: () => ({}) },
  recognizing: { type: Boolean, default: false }
})

const { cameraSlots, cameraPreviewUrls } = useCameraSource()
const cameras = computed(() => cameraSlots.value.map(slot => ({
  ...slot,
  ...(props.result?.cameras || []).find(item => item.slotId === slot.slotId)
})))
const activeCount = computed(() => cameraSlots.value.filter(slot => slot.sourceType !== 'OFF').length)
const totalDetections = computed(() => props.result?.detectionCount ?? props.result?.detections?.length ?? 0)

function detectionsFor(camera) {
  if (camera.result?.detections) return camera.result.detections
  return (props.result?.detections || []).filter(item => item.cameraSlotId === camera.slotId)
}

function overlayDetections(camera) {
  return detectionsFor(camera).filter(item => {
    const box = item?.bbox
    return box && [box.x1, box.y1, box.x2, box.y2].every(value => Number.isFinite(Number(value)))
  })
}

function imageSize(camera) {
  return {
    width: Number(camera.result?.image?.width) || 1920,
    height: Number(camera.result?.image?.height) || 1080
  }
}

function imageViewBox(camera) {
  const { width, height } = imageSize(camera)
  return `0 0 ${width} ${height}`
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

function plateAccent(item) {
  return { blue: '#4da3ff', green: '#00e676', yellow: '#ffd43b', white: '#f8fafc', black: '#cbd5e1', unknown: '#00e5ff' }[plateColorKey(item)]
}

function plateOverlayLabel(item) {
  return `${item.plateNumber || '未知车牌'} · ${plateColorName(item)} · ${confidence(item)}`
}

function plateLabelWidth(item) {
  return Math.min(900, Math.max(400, plateOverlayLabel(item).length * 40 + 32))
}

function plateLabelX(item, camera) {
  const { width } = imageSize(camera)
  return Math.max(0, Math.min(Number(item.bbox.x1), width - plateLabelWidth(item)))
}

function plateLabelY(item, camera) {
  const { height } = imageSize(camera)
  const y1 = Number(item.bbox.y1)
  const y2 = Number(item.bbox.y2)
  return y1 >= 74 ? y1 - 70 : Math.min(height - 64, y2 + 8)
}

function sourceTypeLabel(value) {
  return { SANDBOX: '沙盘', RTSP: '真实视频流', IMAGE: '图片', VIDEO: '视频', DEVICE: '本机设备', OFF: '关闭' }[value] || value
}
</script>

<style scoped>
.multi-camera-detail { min-height: 100%; display: flex; flex-direction: column; gap: 14px; }
.detail-status-bar { display: flex; align-items: center; justify-content: space-between; gap: 14px; padding: 11px 14px; border: 1px solid var(--border-card); border-radius: 11px; background: var(--bg-card); }
.detail-status-bar span, .detail-status-bar strong { display: block; }
.detail-status-bar span { color: var(--text-muted); font-size: 10px; }
.detail-status-bar strong { margin-top: 2px; font-size: 15px; }
.detail-live { display: inline-flex; align-items: center; gap: 7px; color: var(--success-color); font-size: 11px; font-weight: 800; }
.detail-live i { width: 8px; height: 8px; border-radius: 50%; background: currentColor; box-shadow: 0 0 10px currentColor; }
.detail-live.off { color: var(--text-muted); }
.camera-result-grid { flex: 1; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
.camera-result-card { min-width: 0; display: flex; flex-direction: column; gap: 10px; padding: 11px; border: 1px solid var(--border-card); border-radius: var(--radius-md); background: var(--bg-card); }
.camera-result-card.error { border-color: rgba(255,61,0,.3); }
.camera-result-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.camera-result-head div { min-width: 0; }
.camera-result-head span, .camera-result-head strong { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.camera-result-head span { color: var(--primary-color); font: 800 9px/1 "SF Mono", monospace; }
.camera-result-head strong { margin-top: 4px; font-size: 12px; }
.camera-result-head small { flex: 0 0 auto; color: var(--text-muted); font-size: 9px; }
.camera-result-viewport { position: relative; aspect-ratio: 16/9; overflow: hidden; border-radius: 10px; background: #070b12; }
.camera-result-viewport img { width: 100%; height: 100%; display: block; object-fit: cover; }
.plate-box-overlay { position: absolute; inset: 0; z-index: 2; width: 100%; height: 100%; pointer-events: none; }
.plate-detect-box { fill: none; stroke-width: 6; vector-effect: non-scaling-stroke; filter: drop-shadow(0 0 5px rgba(0,0,0,.9)); }
.plate-box-label-bg { fill: rgba(7,11,18,.9); stroke-width: 3; vector-effect: non-scaling-stroke; }
.plate-box-label { fill: #f8fafc; font: 800 38px/1 "SF Mono", "Cascadia Code", monospace; letter-spacing: 1px; }
.camera-result-empty { height: 100%; display: grid; place-content: center; justify-items: center; gap: 8px; color: var(--text-muted); font-size: 10px; }
.camera-frame-label { position: absolute; z-index: 3; left: 8px; right: 8px; bottom: 8px; display: flex; justify-content: space-between; padding: 5px 7px; border-radius: 6px; background: rgba(8,12,20,.76); }
.camera-frame-label span { color: var(--success-color); font: 800 8px/1 "SF Mono", monospace; }
.camera-frame-label small { color: var(--text-muted); font-size: 8px; }
.camera-detections { min-height: 86px; overflow-y: auto; }
.plate-detections div { display: grid; grid-template-columns: 1fr auto auto; gap: 7px; padding: 7px 5px; border-bottom: 1px solid var(--border-subtle); }
.plate-detections strong { color: var(--text-primary); font: 800 12px/1 "SF Mono", monospace; }
.plate-detections span, .plate-detections small { color: var(--text-muted); font-size: 9px; }
.police-detection { display: grid; place-content: center; text-align: center; }
.police-detection strong { font-size: 17px; } .police-detection span { margin-top: 4px; color: var(--text-secondary); font-size: 11px; } .police-detection small { margin-top: 3px; color: var(--warning-color); font-size: 10px; }
.camera-detections p { padding: 24px 4px; color: var(--text-muted); font-size: 10px; text-align: center; }
.detail-summary { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; }
.detail-summary div { padding: 9px 11px; border: 1px solid var(--border-card); border-radius: 9px; background: rgba(255,255,255,.025); }
.detail-summary span, .detail-summary strong { display: block; } .detail-summary span { color: var(--text-muted); font-size: 9px; } .detail-summary strong { margin-top: 3px; font-size: 12px; }
@media (max-width: 900px) { .camera-result-grid { grid-template-columns: 1fr; } .detail-summary { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 480px) { .detail-summary { grid-template-columns: 1fr; } }
</style>
