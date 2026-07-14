export const OWNER_GESTURE_ALGORITHMS = Object.freeze({
  MEDIAPIPE: 'mediapipe_prototype',
  DINO_TCN: 'dinov2_tcn_prototype'
})

export const DEFAULT_OWNER_GESTURE_ALGORITHM_OPTIONS = Object.freeze([
  {
    id: OWNER_GESTURE_ALGORITHMS.MEDIAPIPE,
    name: 'MediaPipe 关键点原型',
    description: '原有关键点余弦与轨迹匹配'
  },
  {
    id: OWNER_GESTURE_ALGORITHMS.DINO_TCN,
    name: 'DINOv2 + TCN 视频原型',
    description: 'RGB 视频与手部几何特征融合'
  }
])

const IMAGE_SIZE = 224
const CROP_EXPANSION = 2.0
let captureCanvas

export function buildVideoPrototypePayload(video, result) {
  const landmarks = result?.landmarks?.[0]
  if (!video?.videoWidth || !video?.videoHeight || !landmarks?.length) return null

  const worldLandmarks = result.worldLandmarks?.[0]
  const handedness = result.handedness?.[0]?.[0]
  const mediapipeGesture = result.gestures?.[0]?.[0]
  return {
    frame: captureHandCrop(video, landmarks),
    landmarks: landmarks.map(point => [number(point.x), number(point.y), number(point.z)]),
    worldLandmarks: worldLandmarks?.map(point => [number(point.x), number(point.y), number(point.z)]) || null,
    detectionScore: number(handedness?.score, 1),
    handedness: handedness?.categoryName || handedness?.displayName || '',
    mediapipeGesture: mediapipeGesture
      ? {
          categoryName: mediapipeGesture.categoryName || mediapipeGesture.displayName || '',
          score: number(mediapipeGesture.score)
        }
      : null
  }
}

function captureHandCrop(video, landmarks) {
  captureCanvas ||= document.createElement('canvas')
  captureCanvas.width = IMAGE_SIZE
  captureCanvas.height = IMAGE_SIZE
  const context = captureCanvas.getContext('2d', { alpha: false })
  const width = video.videoWidth
  const height = video.videoHeight
  const xs = landmarks.map(point => number(point.x) * width)
  const ys = landmarks.map(point => number(point.y) * height)
  const centerX = (Math.min(...xs) + Math.max(...xs)) / 2
  const centerY = (Math.min(...ys) + Math.max(...ys)) / 2
  const side = Math.max(Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys), 24) * CROP_EXPANSION
  const left = centerX - side / 2
  const top = centerY - side / 2
  const sourceX = Math.max(0, left)
  const sourceY = Math.max(0, top)
  const sourceWidth = Math.max(1, Math.min(width, left + side) - sourceX)
  const sourceHeight = Math.max(1, Math.min(height, top + side) - sourceY)
  const scale = IMAGE_SIZE / side

  context.fillStyle = '#080c14'
  context.fillRect(0, 0, IMAGE_SIZE, IMAGE_SIZE)
  context.drawImage(
    video,
    sourceX,
    sourceY,
    sourceWidth,
    sourceHeight,
    (sourceX - left) * scale,
    (sourceY - top) * scale,
    sourceWidth * scale,
    sourceHeight * scale
  )
  return captureCanvas.toDataURL('image/jpeg', 0.76)
}

function number(value, fallback = 0) {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}
