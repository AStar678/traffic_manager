<template>
  <div class="image-canvas">
    <img v-if="imageSrc" :src="imageSrc" alt="识别预览图">
    <div v-else class="preview-placeholder">摄像头 / 图片预览区</div>

    <svg class="overlay" viewBox="0 0 1200 720" preserveAspectRatio="none">
      <template v-for="line in skeletonLines" :key="line.key">
        <line
          :x1="line.a.x"
          :y1="line.a.y"
          :x2="line.b.x"
          :y2="line.b.y"
          stroke="rgba(255,255,255,0.86)"
          stroke-width="5"
          stroke-linecap="round"
        />
      </template>
      <circle
        v-for="point in keypoints"
        :key="point.name"
        :cx="point.x"
        :cy="point.y"
        r="8"
        fill="#fbbc04"
        stroke="#111827"
        stroke-width="3"
      />
      <g v-for="box in boxes" :key="box.objectId">
        <rect
          :x="box.bbox.x1"
          :y="box.bbox.y1"
          :width="box.bbox.x2 - box.bbox.x1"
          :height="box.bbox.y2 - box.bbox.y1"
          fill="transparent"
          stroke="#34a853"
          stroke-width="6"
        />
        <rect
          :x="box.bbox.x1"
          :y="Math.max(0, box.bbox.y1 - 38)"
          :width="labelWidth(box)"
          height="34"
          rx="17"
          fill="#34a853"
        />
        <text
          :x="box.bbox.x1 + 14"
          :y="Math.max(24, box.bbox.y1 - 15)"
          fill="#fff"
          font-size="22"
          font-weight="800"
        >{{ labelText(box) }}</text>
      </g>
    </svg>

    <div v-if="activeLabel" class="active-label">{{ activeLabel }}</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  imageSrc: {
    type: String,
    default: ''
  },
  detections: {
    type: Array,
    default: () => []
  },
  keypoints: {
    type: Array,
    default: () => []
  },
  activeLabel: {
    type: String,
    default: ''
  }
})

const boxes = computed(() => props.detections.filter(item => item.bbox))

const skeletonPairs = [
  ['nose', 'left_shoulder'],
  ['nose', 'right_shoulder'],
  ['left_shoulder', 'right_shoulder'],
  ['left_shoulder', 'left_elbow'],
  ['left_elbow', 'left_wrist'],
  ['right_shoulder', 'right_elbow'],
  ['right_elbow', 'right_wrist'],
  ['left_shoulder', 'left_hip'],
  ['right_shoulder', 'right_hip'],
  ['left_hip', 'right_hip'],
  ['left_hip', 'left_knee'],
  ['left_knee', 'left_ankle'],
  ['right_hip', 'right_knee'],
  ['right_knee', 'right_ankle'],
  ['wrist', 'thumb_tip'],
  ['wrist', 'index_tip'],
  ['wrist', 'middle_tip'],
  ['wrist', 'ring_tip'],
  ['wrist', 'pinky_tip']
]

const skeletonLines = computed(() => {
  const map = new Map(props.keypoints.map(point => [point.name, point]))
  return skeletonPairs
    .filter(([a, b]) => map.has(a) && map.has(b))
    .map(([a, b]) => ({ key: `${a}-${b}`, a: map.get(a), b: map.get(b) }))
})

function labelText(box) {
  return box.plateNumber || box.gestureName || box.objectType || '目标'
}

function labelWidth(box) {
  return Math.max(110, labelText(box).length * 26)
}
</script>

<style scoped>
.image-canvas {
  position: relative;
  min-height: 420px;
  aspect-ratio: 5 / 3;
  overflow: hidden;
  border-radius: 8px;
  background: #111827;
}

img {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: contain;
  opacity: 0.82;
  background: #070b12;
}

.overlay {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.active-label {
  position: absolute;
  right: 18px;
  top: 18px;
  padding: 9px 14px;
  border-radius: 999px;
  background: rgba(26, 115, 232, 0.92);
  color: #fff;
  font-size: 18px;
  font-weight: 900;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.26);
}

.preview-placeholder {
  height: 100%;
  min-height: 420px;
  display: grid;
  place-items: center;
  color: rgba(255, 255, 255, 0.68);
  background:
    linear-gradient(90deg, rgba(255,255,255,0.04) 1px, transparent 1px),
    linear-gradient(rgba(255,255,255,0.04) 1px, transparent 1px),
    #111827;
  background-size: 36px 36px;
}
</style>
