<template>
  <ImageCanvas
    :image-src="imageSrc"
    :detections="detections"
    :keypoints="keypoints"
    :active-label="activeLabel"
  />
</template>

<script setup>
import ImageCanvas from './ImageCanvas.vue'

defineProps({
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
</script>
