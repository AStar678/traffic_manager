<template>
  <div class="gesture-indicator">
    <span>{{ code }}</span>
    <strong>{{ name }}</strong>
    <p>{{ action }}</p>
  </div>
</template>

<script setup>
defineProps({
  code: {
    type: String,
    default: '--'
  },
  name: {
    type: String,
    default: '等待识别'
  },
  action: {
    type: String,
    default: '暂无触发动作'
  }
})
</script>

<style scoped>
.gesture-indicator {
  padding: 18px;
  border-radius: 8px;
  background: #0f2744;
  color: #fff;
}

span {
  display: inline-flex;
  min-height: 28px;
  align-items: center;
  padding: 0 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.12);
  font-weight: 900;
}

strong {
  display: block;
  margin-top: 14px;
  font-size: 24px;
  line-height: 1.2;
}

p {
  margin-top: 8px;
  color: rgba(255, 255, 255, 0.74);
}
</style>
