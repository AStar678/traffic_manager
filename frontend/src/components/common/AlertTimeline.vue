<template>
  <div class="alert-timeline">
    <div v-for="alert in alerts" :key="alert.id" class="alert-item">
      <span class="dot" :class="alert.severity.toLowerCase()"></span>
      <div>
        <div class="alert-head">
          <strong>{{ alert.title }}</strong>
          <span :class="['metric-chip', severityClass(alert.severity)]">{{ severityLabel(alert.severity) }}</span>
        </div>
        <p>{{ alert.summary }}</p>
        <small>{{ alert.occurredAt }} · {{ alert.module }}</small>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  alerts: {
    type: Array,
    default: () => []
  }
})

function severityClass(value) {
  return {
    INFO: 'severity-info',
    WARNING: 'severity-warning',
    CRITICAL: 'severity-critical'
  }[value] || 'severity-info'
}

function severityLabel(value) {
  return {
    INFO: '提示',
    WARNING: '警告',
    CRITICAL: '严重'
  }[value] || value
}
</script>

<style scoped>
.alert-timeline {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.alert-item {
  display: grid;
  grid-template-columns: 14px minmax(0, 1fr);
  gap: 12px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--border-color);
}

.alert-item:last-child {
  border-bottom: 0;
  padding-bottom: 0;
}

.dot {
  width: 10px;
  height: 10px;
  margin-top: 8px;
  border-radius: 50%;
  background: var(--info-color);
}

.dot.warning {
  background: var(--warning-color);
}

.dot.critical {
  background: var(--danger-color);
}

.alert-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.alert-head strong {
  color: #172033;
}

p {
  margin-top: 7px;
  color: var(--text-muted);
  line-height: 1.6;
}

small {
  display: block;
  margin-top: 8px;
  color: #94a3b8;
}
</style>
