<template>
  <ImageCanvas :image-src="imageSrc" :keypoints="keypoints" :active-label="activeLabel" />
</template>

<script setup>
import ImageCanvas from './ImageCanvas.vue'

defineProps({
  imageSrc: {
    type: String,
    default: ''
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
