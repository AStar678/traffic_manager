<template>
  <div class="static-weather-texture" aria-hidden="true">
    <img :src="weatherTextureUrl" alt="" draggable="false">
  </div>
</template>

<script setup>
import weatherTextureUrl from '@/assets/weather/static-rain-snow-texture.svg'
</script>

<style scoped>
.static-weather-texture {
  position: absolute;
  z-index: 1;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
}

.static-weather-texture img {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover;
}
</style>
