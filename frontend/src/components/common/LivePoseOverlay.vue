<template>
  <canvas
    ref="canvasRef"
    class="live-pose-overlay"
    :style="{ objectFit: fit }"
    aria-hidden="true"
  ></canvas>
</template>

<script setup>
import { onBeforeUnmount, ref, watch } from 'vue'
import { DrawingUtils, PoseLandmarker } from '@/vendor/tasks-vision/vision_bundle.mjs'
import { getPoseVisionFileset } from '@/utils/poseVisionRuntime'

const props = defineProps({
  videoElement: { type: Object, default: null },
  active: { type: Boolean, default: false },
  fit: { type: String, default: 'cover' },
  maxFps: { type: Number, default: 10 }
})
const emit = defineEmits(['ready', 'latency', 'presence', 'error'])

const MODEL_PATH = '/models/pose_landmarker_lite.task'
const canvasRef = ref(null)
let poseLandmarker
let poseInitPromise
let drawingUtils
let context
let frameHandle
let frameHandleType = ''
let tracking = false
let lastInferenceAt = 0
let lastVideoTime = -1
let lastTimestamp = 0
let lastLatencyEmitAt = 0
let consecutiveErrors = 0

async function createPoseLandmarker(delegate) {
  const vision = await getPoseVisionFileset()
  return PoseLandmarker.createFromOptions(vision, {
    baseOptions: { modelAssetPath: MODEL_PATH, delegate },
    runningMode: 'VIDEO',
    numPoses: 1,
    minPoseDetectionConfidence: 0.5,
    minPosePresenceConfidence: 0.5,
    minTrackingConfidence: 0.5,
    outputSegmentationMasks: false
  })
}

async function ensurePoseLandmarker() {
  if (poseLandmarker) return poseLandmarker
  if (!poseInitPromise) {
    poseInitPromise = (async () => {
      try {
        poseLandmarker = await createPoseLandmarker('GPU')
      } catch (gpuError) {
        console.warn('MediaPipe Pose GPU delegate unavailable, falling back to CPU.', gpuError)
        poseLandmarker = await createPoseLandmarker('CPU')
      }
      return poseLandmarker
    })().catch(error => {
      poseInitPromise = undefined
      emit('error', error)
      throw error
    })
  }
  return poseInitPromise
}

async function startTracking() {
  if (tracking || !props.active || !props.videoElement) return
  tracking = true
  try {
    await ensurePoseLandmarker()
    if (!tracking || !props.active) return
    emit('ready')
    scheduleFrame()
  } catch (error) {
    console.error('浏览器本地人体关键点模型加载失败', error)
    stopTracking()
  }
}

function stopTracking() {
  tracking = false
  cancelScheduledFrame()
  lastInferenceAt = 0
  lastVideoTime = -1
  lastTimestamp = 0
  consecutiveErrors = 0
  clearOverlay()
  emit('presence', false)
}

function scheduleFrame() {
  if (!tracking || frameHandle !== undefined) return
  const video = props.videoElement
  if (video?.requestVideoFrameCallback) {
    frameHandleType = 'video'
    frameHandle = video.requestVideoFrameCallback(processFrame)
  } else {
    frameHandleType = 'animation'
    frameHandle = requestAnimationFrame(processFrame)
  }
}

function cancelScheduledFrame() {
  if (frameHandle === undefined) return
  const video = props.videoElement
  if (frameHandleType === 'video' && video?.cancelVideoFrameCallback) {
    video.cancelVideoFrameCallback(frameHandle)
  } else {
    cancelAnimationFrame(frameHandle)
  }
  frameHandle = undefined
  frameHandleType = ''
}

function processFrame(now) {
  frameHandle = undefined
  if (!tracking || !props.active || !poseLandmarker) return

  const video = props.videoElement
  const minimumInterval = 1000 / Math.max(1, Number(props.maxFps) || 10)
  if (
    video?.readyState >= 2 &&
    video.videoWidth &&
    video.videoHeight &&
    video.currentTime !== lastVideoTime &&
    now - lastInferenceAt >= minimumInterval
  ) {
    lastInferenceAt = now
    lastVideoTime = video.currentTime
    const startedAt = performance.now()
    try {
      const timestamp = Math.max(now, lastTimestamp + 0.01)
      lastTimestamp = timestamp
      const result = poseLandmarker.detectForVideo(video, timestamp)
      drawPose(result, video)
      consecutiveErrors = 0
      const measuredAt = performance.now()
      if (measuredAt - lastLatencyEmitAt >= 250) {
        lastLatencyEmitAt = measuredAt
        emit('latency', Math.round(measuredAt - startedAt))
      }
    } catch (error) {
      consecutiveErrors += 1
      if (consecutiveErrors >= 3) {
        console.error('浏览器本地人体关键点推理连续失败，回退服务端骨架', error)
        emit('error', error)
        stopTracking()
        return
      }
    }
  }
  scheduleFrame()
}

function drawPose(result, video) {
  resizeOverlay(video)
  clearOverlay()
  const landmarks = result?.landmarks?.[0]
  if (!landmarks?.length || !drawingUtils) {
    emit('presence', false)
    return
  }

  drawingUtils.drawConnectors(landmarks, PoseLandmarker.POSE_CONNECTIONS, {
    color: '#00e5ff',
    lineWidth: 4
  })
  drawingUtils.drawLandmarks(landmarks, {
    color: '#071018',
    fillColor: '#00e676',
    lineWidth: 2,
    radius: 5
  })
  emit('presence', true)
}

function resizeOverlay(video) {
  const canvas = canvasRef.value
  if (!canvas || !video?.videoWidth || !video?.videoHeight) return
  if (canvas.width === video.videoWidth && canvas.height === video.videoHeight && context) return
  canvas.width = video.videoWidth
  canvas.height = video.videoHeight
  context = canvas.getContext('2d')
  drawingUtils = context ? new DrawingUtils(context) : undefined
}

function clearOverlay() {
  const canvas = canvasRef.value
  if (!canvas) return
  context ||= canvas.getContext('2d')
  context?.clearRect(0, 0, canvas.width, canvas.height)
}

watch(
  () => [props.active, props.videoElement],
  ([active, video], previous = []) => {
    if (video !== previous[1]) {
      stopTracking()
    }
    if (active && video) void startTracking()
    else stopTracking()
  },
  { immediate: true, flush: 'post' }
)

onBeforeUnmount(() => {
  stopTracking()
  try {
    poseLandmarker?.close()
  } catch (error) {
    console.warn('MediaPipe Pose 资源释放失败', error)
  }
  poseLandmarker = undefined
})
</script>

<style scoped>
.live-pose-overlay {
  position: absolute;
  inset: 0;
  z-index: 5;
  width: 100%;
  height: 100%;
  display: block;
  pointer-events: none;
  filter: drop-shadow(0 0 4px rgba(0, 0, 0, 0.9));
}
</style>
