<template>
  <div class="control-panel">
    <div class="control-section">
      <div class="section-title">
        <strong>音量</strong>
        <span>{{ state.volume }}%</span>
      </div>
      <el-slider v-model="state.volume" :class="{ active: activeAction === '调节音量' }" />
    </div>

    <div class="control-section">
      <div class="section-title">
        <strong>空调温度</strong>
        <span>{{ state.temperature }}°C</span>
      </div>
      <el-input-number v-model="state.temperature" :min="16" :max="30" />
    </div>

    <div class="mode-grid">
      <button
        v-for="mode in modes"
        :key="mode"
        :class="{ active: state.mode === mode || activeAction?.includes(mode) }"
        @click="state.mode = mode"
      >
        {{ mode }}
      </button>
    </div>

    <div class="phone-actions">
      <el-button :type="activeAction === '接听电话' ? 'success' : 'primary'">接听</el-button>
      <el-button :type="activeAction === '挂断电话' ? 'danger' : 'default'">挂断</el-button>
    </div>
  </div>
</template>

<script setup>
import { reactive } from 'vue'

defineProps({
  activeAction: {
    type: String,
    default: ''
  }
})

const modes = ['音乐', '导航', '电话', '空调']
const state = reactive({
  volume: 42,
  temperature: 24,
  mode: '音乐'
})
</script>

<style scoped>
.control-panel {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.control-section {
  padding: 14px;
  border-radius: 8px;
  background: var(--surface-muted);
}

.section-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.section-title span {
  color: var(--primary-color);
  font-weight: 900;
}

.mode-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.mode-grid button {
  min-height: 48px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: #fff;
  color: #172033;
  cursor: pointer;
  font-weight: 800;
}

.mode-grid button.active {
  border-color: var(--primary-color);
  background: var(--primary-soft);
  color: var(--primary-color);
}

.phone-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}
</style>
