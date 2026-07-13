<template>
  <div
    class="multi-camera-detail"
    :data-stream-source="usesPreloadedStreams ? 'preloaded' : 'local'"
    :data-stream-count="cameraWebRtcStreamCount"
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
          <video
            v-if="cameraWebRtcStreams[camera.slotId]"
            :key="`${camera.slotId}-${cameraWebRtcStreams[camera.slotId]?.id || 'stream'}`"
            :srcObject="cameraWebRtcStreams[camera.slotId]"
            autoplay
            muted
            playsinline
            @loadeddata="markCameraPlaybackReady(camera.slotId)"
            @playing="markCameraPlaybackReady(camera.slotId)"
            @emptied="markCameraPlaybackPending(camera.slotId)"
          ></video>
          <img v-else-if="!usesFrameSync && (cameraPreviewUrls[camera.slotId] || camera.frameUrl)" :src="cameraPreviewUrls[camera.slotId] || camera.frameUrl" :alt="`摄像头 ${camera.slotId}`">
          <div v-else class="camera-result-empty">
            <el-icon :size="34"><VideoCamera /></el-icon>
            <span>{{ cameraFramePlaceholder(camera) }}</span>
          </div>
          <div
            v-if="usesFrameSync && cameraWebRtcStreams[camera.slotId] && !cameraPlaybackReady[camera.slotId]"
            class="camera-result-empty stream-loading"
          >
            <el-icon :size="34"><VideoCamera /></el-icon>
            <span>视频缓冲中</span>
          </div>
          <StaticWeatherTexture v-if="camera.weatherSimulationEnabled && hasCameraMedia(camera)" />
          <svg
            v-if="taskType === 'license_plate' && hasCameraMedia(camera) && overlayDetections(camera).length"
            class="plate-box-overlay"
            :viewBox="imageViewBox(camera)"
            :preserveAspectRatio="focusedSlotId ? 'xMidYMid meet' : 'xMidYMid slice'"
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
          <svg
            v-if="taskType === 'vehicle_type' && hasCameraMedia(camera) && overlayDetections(camera).length"
            class="plate-box-overlay vehicle-box-overlay"
            :viewBox="imageViewBox(camera)"
            :preserveAspectRatio="focusedSlotId ? 'xMidYMid meet' : 'xMidYMid slice'"
            aria-label="车辆跟踪框"
          >
            <g v-for="item in overlayDetections(camera)" :key="`vehicle-${item.objectId || item.trackId}`">
              <rect
                class="plate-detect-box vehicle-detect-box"
                :x="item.bbox.x1"
                :y="item.bbox.y1"
                :width="Math.max(1, item.bbox.x2 - item.bbox.x1)"
                :height="Math.max(1, item.bbox.y2 - item.bbox.y1)"
              />
              <g :transform="`translate(${vehicleLabelX(item, camera)}, ${vehicleLabelY(item, camera)})`">
                <rect class="plate-box-label-bg vehicle-box-label-bg" :width="vehicleLabelWidth(item)" height="64" rx="10" />
                <text class="plate-box-label" x="16" y="43">{{ vehicleOverlayLabel(item) }}</text>
              </g>
            </g>
          </svg>
          <svg
            v-if="taskType === 'police_gesture' && hasCameraMedia(camera) && policeSkeletons(camera).length"
            class="police-skeleton-overlay"
            :viewBox="imageViewBox(camera)"
            :preserveAspectRatio="focusedSlotId ? 'xMidYMid meet' : 'xMidYMid slice'"
            aria-label="交警人体关键点"
          >
            <g v-for="skeleton in policeSkeletons(camera)" :key="`skeleton-${skeleton.id}`">
              <line
                v-for="bone in policeBones"
                :key="`${skeleton.id}-${bone[0]}-${bone[1]}`"
                class="skeleton-bone"
                :x1="skeleton.points[bone[0]]?.x"
                :y1="skeleton.points[bone[0]]?.y"
                :x2="skeleton.points[bone[1]]?.x"
                :y2="skeleton.points[bone[1]]?.y"
                v-show="skeleton.points[bone[0]] && skeleton.points[bone[1]]"
              />
              <circle
                v-for="point in skeleton.keypoints"
                :key="`${skeleton.id}-${point.name}`"
                class="skeleton-point"
                :class="{ core: point.name === 'nose' || point.name === 'neck' }"
                :cx="point.x"
                :cy="point.y"
                r="8"
              />
            </g>
          </svg>
          <div class="camera-frame-label">
            <span>{{ camera.status === 'error' ? '异常' : (recognizing && camera.sourceType !== 'OFF' ? (usesFrameSync ? 'FRAME SYNC' : 'LIVE') : 'OFF') }}</span>
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
      <div><span>传输方式</span><strong>{{ usesFrameSync ? `WebRTC · ${FRAME_SYNC_BUFFER_MS}ms 帧同步` : 'WebRTC / UDP' }}</strong></div>
    </footer>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue'
import StaticWeatherTexture from '@/components/common/StaticWeatherTexture.vue'
import {
  FRAME_SYNC_BUFFER_MS,
  useCameraSource,
  useDelayedCameraStreams
} from '@/composables/useCameraSource'

const props = defineProps({
  taskType: { type: String, required: true },
  result: { type: Object, default: () => ({}) },
  recognizing: { type: Boolean, default: false },
  preloadedStreams: { type: Object, default: null }
})

const focusedSlotId = ref(null)
const cameraPlaybackReady = reactive({})
const synchronizedCameraResults = reactive({})
const overlayCameraResults = reactive({})
const pendingResultTimers = new Map()
const overlayClearTimers = new Map()
const lastDisplayedCapturedAt = new Map()
const detailOpenedAt = Date.now()
const WEBRTC_PLAYOUT_COMPENSATION_MS = 70
const MAX_LATE_RESULT_MS = 220
const OVERLAY_HOLD_MS = 220
const MAX_PENDING_RESULTS_PER_CAMERA = 6
const usesFrameSync = ['license_plate', 'vehicle_type'].includes(props.taskType)
const usesPreloadedStreams = Boolean(props.preloadedStreams)
const resultSource = props.preloadedStreams || (usesFrameSync
  ? useDelayedCameraStreams(FRAME_SYNC_BUFFER_MS)
  : useCameraSource())
const { cameraSlots, cameraPreviewUrls, cameraWebRtcStreams } = resultSource
const cameraWebRtcStreamCount = computed(() => Object.keys(cameraWebRtcStreams || {}).length)
const renderResult = computed(() => {
  if (!usesFrameSync) return props.result
  const cameras = Object.values(synchronizedCameraResults)
  const detections = cameras.flatMap(camera => camera?.result?.detections || [])
  return {
    ...(props.result || {}),
    cameras,
    detections,
    detectionCount: detections.length
  }
})

watch(() => props.result, result => {
  if (!usesFrameSync) return
  for (const camera of result?.cameras || []) scheduleCameraResult(camera, result)
}, { immediate: true })

watch(
  () => cameraSlots.value.map(slot => [slot.slotId, cameraWebRtcStreams[slot.slotId]?.id || '']),
  (currentStreams, previousStreams = []) => {
    currentStreams.forEach(([slotId, streamId], index) => {
      if (streamId !== previousStreams[index]?.[1]) cameraPlaybackReady[slotId] = false
    })
  },
  { immediate: true }
)

onBeforeUnmount(() => {
  for (const timers of pendingResultTimers.values()) {
    for (const timer of timers.values()) window.clearTimeout(timer)
  }
  for (const timer of overlayClearTimers.values()) window.clearTimeout(timer)
  pendingResultTimers.clear()
  overlayClearTimers.clear()
})

function scheduleCameraResult(camera, aggregateResult) {
  const slotId = Number(camera?.slotId)
  if (!Number.isFinite(slotId)) return

  const firstDetection = camera?.result?.detections?.[0]
  const exactCapturedAt = Number(camera?.frameCapturedAtMs ?? firstDetection?.frameCapturedAtMs)
  const latencyMs = Number(aggregateResult?.latencyMs)
  const capturedAt = Number.isFinite(exactCapturedAt)
    ? exactCapturedAt
    : Date.now() - (Number.isFinite(latencyMs) ? latencyMs : 0)
  const serverTimeMs = Number(aggregateResult?.serverTimeMs)
  const capturedAtLocal = Number.isFinite(exactCapturedAt) && Number.isFinite(serverTimeMs)
    ? capturedAt + (Date.now() - serverTimeMs)
    : capturedAt

  // A result already present when the dialog opens belongs to a frame that was
  // emitted before this short-buffer WebRTC subscription existed.
  if (!usesPreloadedStreams && capturedAtLocal < detailOpenedAt) return

  const frameId = String(camera?.frameId || firstDetection?.frameId || `${slotId}-${capturedAt}`)
  const targetAt = capturedAtLocal + FRAME_SYNC_BUFFER_MS + WEBRTC_PLAYOUT_COMPENSATION_MS
  if (Date.now() - targetAt > MAX_LATE_RESULT_MS) return
  if (capturedAt <= (lastDisplayedCapturedAt.get(slotId) || 0)) return

  let timers = pendingResultTimers.get(slotId)
  if (!timers) {
    timers = new Map()
    pendingResultTimers.set(slotId, timers)
  }
  if (timers.has(frameId)) return

  while (timers.size >= MAX_PENDING_RESULTS_PER_CAMERA) {
    const oldestFrameId = timers.keys().next().value
    window.clearTimeout(timers.get(oldestFrameId))
    timers.delete(oldestFrameId)
  }

  const timer = window.setTimeout(() => {
    timers.delete(frameId)
    if (capturedAt <= (lastDisplayedCapturedAt.get(slotId) || 0)) return
    lastDisplayedCapturedAt.set(slotId, capturedAt)
    synchronizedCameraResults[slotId] = camera
    overlayCameraResults[slotId] = camera

    const previousClearTimer = overlayClearTimers.get(slotId)
    if (previousClearTimer) window.clearTimeout(previousClearTimer)
    const clearTimer = window.setTimeout(() => {
      if (overlayCameraResults[slotId] === camera) {
        delete overlayCameraResults[slotId]
      }
      overlayClearTimers.delete(slotId)
    }, OVERLAY_HOLD_MS)
    overlayClearTimers.set(slotId, clearTimer)
  }, Math.max(0, targetAt - Date.now()))
  timers.set(frameId, timer)
}

const policeBones = [
  ['nose', 'neck'],
  ['neck', 'right_shoulder'], ['right_shoulder', 'right_elbow'], ['right_elbow', 'right_wrist'],
  ['neck', 'left_shoulder'], ['left_shoulder', 'left_elbow'], ['left_elbow', 'left_wrist'],
  ['right_shoulder', 'left_shoulder'],
  ['right_shoulder', 'right_hip'], ['right_hip', 'right_knee'], ['right_knee', 'right_ankle'],
  ['left_shoulder', 'left_hip'], ['left_hip', 'left_knee'], ['left_knee', 'left_ankle'],
  ['right_hip', 'left_hip']
]
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

function markCameraPlaybackReady(slotId) {
  cameraPlaybackReady[slotId] = true
}

function markCameraPlaybackPending(slotId) {
  cameraPlaybackReady[slotId] = false
}

function detectionsFor(camera) {
  if (camera.result?.detections) return camera.result.detections
  return (renderResult.value?.detections || []).filter(item => item.cameraSlotId === camera.slotId)
}

function overlayDetections(camera) {
  const detections = usesFrameSync
    ? (overlayCameraResults[camera.slotId]?.result?.detections || [])
    : detectionsFor(camera)
  return detections.filter(item => {
    const box = item?.bbox
    return box && [box.x1, box.y1, box.x2, box.y2].every(value => Number.isFinite(Number(value)))
  })
}

function hasCameraMedia(camera) {
  if (usesFrameSync) {
    return Boolean(cameraWebRtcStreams[camera.slotId] && cameraPlaybackReady[camera.slotId])
  }
  return Boolean(cameraWebRtcStreams[camera.slotId] || cameraPreviewUrls[camera.slotId] || camera.frameUrl)
}

function cameraFramePlaceholder(camera) {
  if (camera.sourceType === 'OFF') return '已关闭'
  if (camera.error) return camera.error
  if (usesFrameSync) {
    return props.recognizing ? `正在建立 ${FRAME_SYNC_BUFFER_MS}ms 帧同步视频` : '识别已关闭'
  }
  return '等待文件帧'
}

function cameraTransportLabel(camera) {
  if (usesFrameSync) {
    return cameraWebRtcStreams[camera.slotId] ? 'WebRTC · frame_id / pts' : '等待帧同步流'
  }
  return cameraWebRtcStreams[camera.slotId] ? 'WebRTC 低延迟' : 'JPEG 降级'
}

function policeSkeletons(camera) {
  return detectionsFor(camera).map((detection, index) => {
    const keypoints = (detection?.keypoints || []).filter(point =>
      Number.isFinite(Number(point?.x)) &&
      Number.isFinite(Number(point?.y)) &&
      Number(point?.score ?? 1) > 0.05
    )
    return {
      id: detection.objectId || index,
      keypoints,
      points: Object.fromEntries(keypoints.map(point => [point.name, point]))
    }
  }).filter(skeleton => skeleton.keypoints.length)
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

function vehicleOverlayLabel(item) {
  return `#${item.trackId ?? '--'} · ${vehicleTypeName(item)} · ${vehicleColorName(item)} · ${confidence(item)}`
}

function vehicleLabelWidth(item) {
  return Math.min(980, Math.max(430, vehicleOverlayLabel(item).length * 40 + 32))
}

function vehicleLabelX(item, camera) {
  const { width } = imageSize(camera)
  return Math.max(0, Math.min(Number(item.bbox.x1), width - vehicleLabelWidth(item)))
}

function vehicleLabelY(item, camera) {
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
.camera-result-viewport img, .camera-result-viewport video { width: 100%; height: 100%; display: block; object-fit: cover; }
.camera-result-card.expanded .camera-result-viewport { grid-area: viewport; height: clamp(380px, 62vh, 680px); aspect-ratio: auto; }
.camera-result-card.expanded .camera-result-viewport img,
.camera-result-card.expanded .camera-result-viewport video { object-fit: contain; }
.plate-box-overlay { position: absolute; inset: 0; z-index: 4; width: 100%; height: 100%; pointer-events: none; }
.plate-detect-box { fill: none; stroke-width: 6; vector-effect: non-scaling-stroke; filter: drop-shadow(0 0 5px rgba(0,0,0,.9)); }
.plate-box-label-bg { fill: rgba(7,11,18,.9); stroke-width: 3; vector-effect: non-scaling-stroke; }
.plate-box-label { fill: #f8fafc; font: 800 38px/1 "SF Mono", "Cascadia Code", monospace; letter-spacing: 1px; }
.vehicle-detect-box { stroke: #00e5ff; }
.vehicle-box-label-bg { stroke: #00e5ff; }
.police-skeleton-overlay { position: absolute; inset: 0; z-index: 4; width: 100%; height: 100%; pointer-events: none; }
.skeleton-bone { stroke: #00e5ff; stroke-width: 6; stroke-linecap: round; vector-effect: non-scaling-stroke; filter: drop-shadow(0 0 4px rgba(0,0,0,.9)); }
.skeleton-point { fill: #00e676; stroke: #071018; stroke-width: 3; vector-effect: non-scaling-stroke; filter: drop-shadow(0 0 5px rgba(0,230,118,.8)); }
.skeleton-point.core { fill: #ffd43b; }
.camera-result-empty { height: 100%; display: grid; place-content: center; justify-items: center; gap: 8px; color: var(--text-secondary); font-size: 12px; }
.camera-result-empty.stream-loading { position: absolute; inset: 0; z-index: 2; background: #070b12; }
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
