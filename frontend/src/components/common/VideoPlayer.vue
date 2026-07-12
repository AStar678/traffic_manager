<template>
  <div class="video-player">
    <ImageCanvas :image-src="poster" :detections="detections" :keypoints="keypoints" :active-label="activeLabel" />
    <div class="video-toolbar">
      <el-button size="small" circle>
        <el-icon><VideoPlay /></el-icon>
      </el-button>
      <el-button size="small" circle>
        <el-icon><VideoPause /></el-icon>
      </el-button>
      <span>{{ label }}</span>
    </div>
  </div>
</template>

<script setup>
import ImageCanvas from './ImageCanvas.vue'

defineProps({
  poster: {
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
  },
  label: {
    type: String,
    default: '主服务摄像头画面'
  }
})
</script>

<style scoped>
.video-player {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.video-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-muted);
  font-size: 13px;
  font-weight: 700;
}
</style>
