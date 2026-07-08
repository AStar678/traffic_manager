<template>
  <div class="alert-stats-card">
    <span>{{ label }}</span>
    <strong>{{ value }}</strong>
    <p>{{ description }}</p>
  </div>
</template>

<script setup>
defineProps({
  label: {
    type: String,
    default: '告警'
  },
  value: {
    type: [String, Number],
    default: 0
  },
  description: {
    type: String,
    default: ''
  }
})
</script>

<style scoped>
.alert-stats-card {
  padding: 18px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: #fff;
  box-shadow: var(--shadow-sm);
}

span {
  color: var(--text-muted);
  font-size: 13px;
  font-weight: 800;
}

strong {
  display: block;
  margin-top: 8px;
  color: #172033;
  font-size: 32px;
  line-height: 1;
}

p {
  margin-top: 10px;
  color: var(--text-muted);
  font-size: 13px;
}
</style>
