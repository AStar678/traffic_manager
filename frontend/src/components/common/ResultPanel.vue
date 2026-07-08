<template>
  <div class="result-panel">
    <div class="summary">
      <span>任务类型</span>
      <strong>{{ taskLabel }}</strong>
    </div>
    <div class="summary success">
      <span>检测结果</span>
      <strong>{{ result?.detectionCount || 0 }} 个目标</strong>
    </div>
    <div class="summary warning">
      <span>耗时</span>
      <strong>{{ result?.latencyMs || 0 }} ms</strong>
    </div>

    <div class="result-list">
      <div v-for="item in result?.detections || []" :key="item.objectId" class="result-item">
        <div>
          <strong>{{ item.plateNumber || item.gestureName || item.objectId }}</strong>
          <span>{{ item.objectType }} · 置信度 {{ percent(item.confidence) }}</span>
          <small v-if="item.bbox">
            bbox: [{{ item.bbox.x1 }}, {{ item.bbox.y1 }}, {{ item.bbox.x2 }}, {{ item.bbox.y2 }}]
          </small>
          <small v-if="item.position">
            position: center({{ item.position.centerX }}, {{ item.position.centerY }}) · {{ item.position.width }}x{{ item.position.height }}
          </small>
          <small v-if="item.frameNo">
            frame {{ item.frameNo }} · {{ item.timestamp }}
          </small>
        </div>
        <span class="result-tag">{{ colorLabel(item.plateColor) || item.gestureCode || 'OK' }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  taskType: {
    type: String,
    default: 'license_plate'
  },
  result: {
    type: Object,
    default: null
  }
})

const labels = {
  license_plate: '车牌识别',
  police_gesture: '交警手势',
  owner_gesture: '车主手势'
}

const taskLabel = computed(() => labels[props.taskType] || props.taskType)

function percent(value) {
  return `${Math.round((value || 0) * 100)}%`
}

function colorLabel(value) {
  const map = {
    blue: '蓝牌',
    green: '绿牌',
    white: '白牌'
  }
  return map[value] || value
}
</script>

<style scoped>
.result-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  min-height: 58px;
  padding: 0 14px;
  border-radius: 8px;
  background: #eef4ff;
}

.summary.success {
  background: #eaf7ef;
}

.summary.warning {
  background: #fff6dc;
}

.summary span {
  color: var(--text-muted);
  font-size: 13px;
  font-weight: 700;
}

.summary strong {
  color: #172033;
  font-size: 18px;
}

.result-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 4px;
}

.result-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
}

.result-item strong {
  display: block;
  color: #172033;
  font-size: 16px;
}

.result-item span {
  display: block;
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 12px;
}

.result-item small {
  display: block;
  margin-top: 4px;
  color: #64748b;
  font-family: "Cascadia Mono", "Consolas", monospace;
  font-size: 12px;
}
</style>
