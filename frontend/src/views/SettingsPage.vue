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
            <span>告警失败率阈值</span>
            <div class="slider-row">
              <el-slider v-model="thresholds.failureRate" :min="0" :max="1" :step="0.01" />
              <strong>{{ Math.round(thresholds.failureRate * 100) }}%</strong>
            </div>
          </label>
        </div>
      </div>
    </div>

    <div class="card voice-settings-card">
      <div class="voice-setting-row">
        <span class="voice-setting-icon" aria-hidden="true">
          <el-icon><Microphone /></el-icon>
        </span>
        <div class="voice-setting-copy">
          <h3 class="card-title">语音提示</h3>
          <p>播报交警指令与用户手势的执行结果。</p>
        </div>
        <div class="voice-setting-control">
          <span>{{ speechAnnouncementsEnabled ? '已开启' : '已关闭' }}</span>
          <el-switch
            v-model="speechAnnouncementsEnabled"
            class="voice-switch"
            aria-label="语音提示"
            @change="updateSpeechAnnouncements"
          />
        </div>
      </div>
    </div>

    <div class="card gesture-settings-card">
      <div class="gesture-settings-head">
        <div>
          <h3 class="card-title">DINOv2 视频手势</h3>
          <p>仅识别用户录入的视频原型，不使用系统预设手势。</p>
        </div>
        <span class="fixed-algorithm">DINOv2-S + TCN</span>
      </div>

      <div class="gesture-config-grid" :class="{ loading: gestureConfigLoading }">
        <label>
          <span>原型匹配阈值</span>
          <div class="slider-row">
            <el-slider v-model="gestureConfig.dinov2MatchThreshold" :min="0.3" :max="0.99" :step="0.01" />
            <strong>{{ Math.round(gestureConfig.dinov2MatchThreshold * 100) }}%</strong>
          </div>
          <small>阈值越高越严格，可减少误触发。</small>
        </label>

        <label>
          <span>视频采样间隔</span>
          <div class="slider-row">
            <el-slider v-model="gestureConfig.dinov2FrameIntervalMs" :min="80" :max="500" :step="10" />
            <strong>{{ gestureConfig.dinov2FrameIntervalMs }} ms</strong>
          </div>
          <small>较短间隔更流畅，但会增加端到端推理压力。</small>
        </label>

        <label>
          <span>默认触发持续时间</span>
          <div class="slider-row">
            <el-slider v-model="gestureConfig.defaultHoldMs" :min="300" :max="3000" :step="100" />
            <strong>{{ (gestureConfig.defaultHoldMs / 1000).toFixed(1) }} s</strong>
          </div>
          <small>手势需稳定匹配达到该时长后才触发控制。</small>
        </label>

        <label>
          <span>重复触发冷却时间</span>
          <div class="slider-row">
            <el-slider v-model="gestureConfig.triggerCooldownMs" :min="300" :max="5000" :step="100" />
            <strong>{{ (gestureConfig.triggerCooldownMs / 1000).toFixed(1) }} s</strong>
          </div>
          <small>限制同一手势连续触发车辆功能的频率。</small>
        </label>
      </div>

      <div class="gesture-settings-footer">
        <span>每个视频原型固定采样 {{ gestureConfig.sampleTarget }} 帧</span>
        <el-button type="primary" :loading="gestureConfigSaving" @click="saveGestureConfig">保存手势设置</el-button>
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
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getOwnerGestureConfig, getOwnerGestureData, updateOwnerGestureConfig } from '@/api/ownerGestures'
import { mockSystemHealth } from '@/utils/mockData'
import {
  areSpeechAnnouncementsEnabled,
  setSpeechAnnouncementsEnabled
} from '@/utils/speechAnnouncements'

const health = mockSystemHealth
const thresholds = reactive({ plate: 0.72, failureRate: 0.30 })
const gestureConfig = reactive({
  dinov2MatchThreshold: 0.95,
  dinov2FrameIntervalMs: 150,
  defaultHoldMs: 1200,
  triggerCooldownMs: 1500,
  sampleTarget: 12
})
const gestureConfigLoading = ref(false)
const gestureConfigSaving = ref(false)
const speechAnnouncementsEnabled = ref(areSpeechAnnouncementsEnabled())

onMounted(loadGestureConfig)

function updateSpeechAnnouncements(enabled) {
  setSpeechAnnouncementsEnabled(enabled)
  ElMessage.success(enabled ? '语音提示已开启' : '语音提示已关闭')
}

async function loadGestureConfig() {
  gestureConfigLoading.value = true
  try {
    const data = getOwnerGestureData(await getOwnerGestureConfig())
    Object.assign(gestureConfig, data?.config || {})
  } catch (error) {
    console.error(error)
  } finally {
    gestureConfigLoading.value = false
  }
}

async function saveGestureConfig() {
  gestureConfigSaving.value = true
  try {
    const payload = {
      dinov2MatchThreshold: gestureConfig.dinov2MatchThreshold,
      dinov2FrameIntervalMs: gestureConfig.dinov2FrameIntervalMs,
      defaultHoldMs: gestureConfig.defaultHoldMs,
      triggerCooldownMs: gestureConfig.triggerCooldownMs
    }
    const data = getOwnerGestureData(await updateOwnerGestureConfig(payload))
    Object.assign(gestureConfig, data?.config || {})
    ElMessage.success('DINOv2 手势设置已保存')
  } catch (error) {
    console.error(error)
  } finally {
    gestureConfigSaving.value = false
  }
}
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

.voice-settings-card { padding-block: 18px; }
.voice-setting-row {
  display: grid;
  grid-template-columns: 44px minmax(0, 1fr) auto;
  align-items: center;
  gap: 14px;
}
.voice-setting-icon {
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  border: 1px solid var(--border-active);
  border-radius: 12px;
  color: var(--primary-color);
  background: var(--primary-soft);
}
.voice-setting-icon .el-icon { font-size: 21px; }
.voice-setting-copy { min-width: 0; }
.voice-setting-copy .card-title { margin-bottom: 5px; }
.voice-setting-copy p {
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.5;
}
.voice-setting-control {
  display: flex;
  align-items: center;
  gap: 12px;
}
.voice-setting-control > span {
  min-width: 42px;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 700;
  text-align: right;
}
:deep(.voice-switch) {
  --el-switch-on-color: var(--primary-color);
  --el-switch-off-color: rgba(255, 255, 255, 0.18);
}

.gesture-settings-card { display: flex; flex-direction: column; gap: 18px; }
.gesture-settings-head,
.gesture-settings-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.gesture-settings-head .card-title { margin-bottom: 6px; }
.gesture-settings-head p,
.gesture-settings-footer span,
.gesture-config-grid small {
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.5;
}
.fixed-algorithm {
  flex: 0 0 auto;
  border: 1px solid var(--border-active);
  border-radius: 999px;
  padding: 7px 12px;
  color: var(--primary-color);
  background: var(--primary-soft);
  font-size: 12px;
  font-weight: 800;
}
.gesture-config-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px 24px;
  transition: opacity var(--duration-fast) var(--ease-out);
}
.gesture-config-grid.loading { opacity: 0.55; pointer-events: none; }
.gesture-config-grid label { min-width: 0; }
.gesture-config-grid label > span {
  display: block;
  margin-bottom: 6px;
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 700;
}
.gesture-config-grid .slider-row strong { min-width: 72px; }
.gesture-settings-footer {
  border-top: 1px solid var(--border-subtle);
  padding-top: 16px;
}

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

@media (max-width: 760px) {
  .settings-grid,
  .gesture-config-grid,
  .constraint-grid {
    grid-template-columns: 1fr;
  }

  .gesture-settings-head,
  .gesture-settings-footer {
    align-items: flex-start;
    flex-direction: column;
  }

  .gesture-settings-footer .el-button { width: 100%; }

  .voice-setting-row { grid-template-columns: minmax(0, 1fr) auto; }
  .voice-setting-icon { display: none; }
  .voice-setting-control { gap: 8px; }
}
</style>
