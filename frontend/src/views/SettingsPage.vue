<template>
  <div class="settings-page">
    <div class="page-top">
      <h1>系统设置</h1>
      <p>服务状态、识别阈值、上传约束与通知配置</p>
    </div>

    <div class="settings-grid">
      <!-- 服务状态 -->
      <div class="card">
        <h3 class="card-title">服务状态</h3>
        <div class="service-list">
          <div v-for="item in health" :key="item.name" class="service-row">
            <div>
              <span class="status-dot" :class="item.status === 'normal' ? 'online' : 'warning'"></span>
              <strong>{{ item.name }}</strong>
            </div>
            <div class="service-right">
              <span class="service-value">{{ item.value }}</span>
              <small>{{ item.detail }}</small>
            </div>
          </div>
        </div>
      </div>

      <!-- 识别阈值 -->
      <div class="card">
        <h3 class="card-title">识别阈值</h3>
        <div class="threshold-list">
          <label>
            <span>车牌检测置信度</span>
            <div class="slider-row">
              <el-slider v-model="thresholds.plate" :min="0" :max="1" :step="0.01" />
              <strong>{{ Math.round(thresholds.plate * 100) }}%</strong>
            </div>
          </label>
          <label>
            <span>手势识别置信度</span>
            <div class="slider-row">
              <el-slider v-model="thresholds.gesture" :min="0" :max="1" :step="0.01" />
              <strong>{{ Math.round(thresholds.gesture * 100) }}%</strong>
            </div>
          </label>
          <label>
            <span>告警失败率阈值</span>
            <div class="slider-row">
              <el-slider v-model="thresholds.failureRate" :min="0" :max="1" :step="0.01" />
              <strong>{{ Math.round(thresholds.failureRate * 100) }}%</strong>
            </div>
          </label>
        </div>
      </div>
    </div>

    <!-- 上传约束 -->
    <div class="card">
      <h3 class="card-title">上传与安全约束</h3>
      <div class="constraint-grid">
        <div class="constraint-item">
          <el-icon><Picture /></el-icon>
          <span>图片格式</span>
          <small>jpg / png / bmp · ≤ 10MB</small>
        </div>
        <div class="constraint-item">
          <el-icon><VideoCamera /></el-icon>
          <span>视频格式</span>
          <small>mp4 / avi / mov · ≤ 200MB</small>
        </div>
        <div class="constraint-item">
          <el-icon><Lock /></el-icon>
          <span>认证方式</span>
          <small>JWT Bearer Token</small>
        </div>
        <div class="constraint-item">
          <el-icon><Connection /></el-icon>
          <span>数据源</span>
          <small>Mock · 后端就绪后切换</small>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive } from 'vue'
import { mockSystemHealth } from '@/utils/mockData'

const health = mockSystemHealth
const thresholds = reactive({ plate: 0.72, gesture: 0.70, failureRate: 0.30 })
</script>

<style scoped>
.settings-page { display: flex; flex-direction: column; gap: 16px; }

.page-top h1 {
  font-size: 24px;
  font-weight: 800;
  color: var(--text-primary);
  letter-spacing: -0.3px;
}

.page-top p {
  margin-top: 4px;
  font-size: 13px;
  color: var(--text-muted);
}

.settings-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.card-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 16px;
}

/* 服务状态 */
.service-list { display: flex; flex-direction: column; gap: 10px; }

.service-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  background: rgba(255,255,255,0.02);
  border-radius: var(--radius-sm);
}

.service-row > div:first-child {
  display: flex;
  align-items: center;
  gap: 10px;
}

.service-row strong { color: var(--text-primary); font-size: 14px; }

.service-right { text-align: right; }
.service-value { font-size: 13px; font-weight: 700; color: var(--success-color); }
.service-right small { display: block; font-size: 11px; color: var(--text-muted); margin-top: 2px; }

/* 阈值 */
.threshold-list { display: flex; flex-direction: column; gap: 18px; }
.threshold-list label span {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 6px;
}

.slider-row { display: flex; align-items: center; gap: 14px; }
.slider-row .el-slider { flex: 1; }
.slider-row strong { font-size: 16px; color: var(--primary-color); min-width: 44px; text-align: right; }

/* 约束 */
.constraint-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.constraint-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 20px 14px;
  background: rgba(255,255,255,0.02);
  border: 1px solid var(--border-card);
  border-radius: var(--radius-md);
  text-align: center;
}

.constraint-item .el-icon { font-size: 24px; color: var(--primary-color); }
.constraint-item span { font-size: 13px; font-weight: 700; color: var(--text-primary); }
.constraint-item small { font-size: 11px; color: var(--text-muted); }
</style>
