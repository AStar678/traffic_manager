<template>
  <div class="plate-page">
    <!-- 主区域：摄像头大画面 -->
    <div class="viewport-area">
      <div class="viewport">
        <img v-if="result.annotatedImageUrl" :src="result.annotatedImageUrl" alt="camera" />
        <div v-else class="viewport-placeholder">
          <el-icon :size="48"><Camera /></el-icon>
          <span>前置摄像头待机</span>
        </div>

        <!-- 检测框叠加层 -->
        <svg class="detection-overlay" viewBox="0 0 1200 720" preserveAspectRatio="none" v-if="result.detections.length">
          <g v-for="box in result.detections" :key="box.objectId">
            <rect
              :x="box.bbox.x1" :y="box.bbox.y1"
              :width="box.bbox.x2 - box.bbox.x1"
              :height="box.bbox.y2 - box.bbox.y1"
              fill="none"
              stroke="#00e676"
              stroke-width="4"
              class="detect-rect"
            />
            <rect
              :x="box.bbox.x1"
              :y="Math.max(0, box.bbox.y1 - 32)"
              :width="box.plateNumber.length * 22 + 28"
              height="28"
              rx="14"
              fill="#00e676"
            />
            <text
              :x="box.bbox.x1 + 14"
              :y="Math.max(18, box.bbox.y1 - 11)"
              fill="#080c14"
              font-size="18"
              font-weight="800"
            >{{ box.plateNumber }}</text>
          </g>
        </svg>

        <div class="scan-line-animated"></div>

        <!-- 顶部状态 -->
        <div class="viewport-top">
          <span class="chip live">● LIVE</span>
          <span class="chip">RTSP live1 桥面</span>
        </div>

        <!-- 底部检测信息 -->
        <div class="viewport-bottom" v-if="result.detections.length">
          <div class="detect-summary">
            <span>检测到 <strong>{{ result.detections.length }}</strong> 辆车</span>
            <span>耗时 {{ result.latencyMs }}ms</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 右侧操作面板 -->
    <div class="side-panel">
      <!-- 输入模式切换 -->
      <div class="card">
        <div class="mode-tabs">
          <button
            :class="{ active: inputMode === 'image' }"
            @click="inputMode = 'image'"
          >图片识别</button>
          <button
            :class="{ active: inputMode === 'video' }"
            @click="inputMode = 'video'"
          >视频/RTSP</button>
        </div>

        <!-- 上传区域 -->
        <div class="upload-zone" @click="triggerUpload">
          <input ref="fileInput" type="file" accept=".jpg,.jpeg,.png,.bmp" style="display:none" @change="onFileSelected">
          <el-icon :size="28"><UploadFilled /></el-icon>
          <span>点击或拖拽上传图片</span>
          <small>jpg / png / bmp · ≤ 10MB</small>
        </div>

        <div v-if="inputMode === 'video'" class="rtsp-select">
          <label>沙盘摄像头通道</label>
          <el-select v-model="selectedRtsp" style="width:100%">
            <el-option v-for="ch in rtspChannels" :key="ch.value" :label="ch.label" :value="ch.value" />
          </el-select>
        </div>

        <button class="action-btn primary" :disabled="loading" @click="runInference">
          <el-icon v-if="loading" class="spinner"><Loading /></el-icon>
          {{ loading ? '识别中...' : (inputMode === 'image' ? '上传并识别' : '创建识别任务') }}
        </button>
      </div>

      <!-- 识别结果 -->
      <div class="card">
        <h3 class="card-title">识别结果</h3>
        <div v-if="result.detections.length" class="result-list">
          <div v-for="item in result.detections" :key="item.objectId" class="result-item">
            <div class="plate-tag" :class="item.plateColor">
              {{ item.plateNumber }}
            </div>
            <div class="result-meta">
              <span>{{ item.plateType }}</span>
              <span>OCR {{ Math.round(item.ocrConfidence * 100) }}%</span>
            </div>
          </div>
        </div>
        <div v-else class="empty-result">
          <el-icon :size="32"><Picture /></el-icon>
          <span>暂无识别结果</span>
          <small>上传图片开始识别</small>
        </div>

        <button class="action-btn secondary" style="margin-top:14px" v-if="result.detections.length">
          保存记录
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { mockInference, rtspChannels } from '@/utils/mockData'
import { TASK_TYPES } from '@/utils/constants'

const result = ref(mockInference[TASK_TYPES.LICENSE_PLATE])
const loading = ref(false)
const inputMode = ref('image')
const selectedRtsp = ref(rtspChannels[0].value)
const fileInput = ref(null)

function triggerUpload() {
  fileInput.value?.click()
}

function onFileSelected(e) {
  const file = e.target.files?.[0]
  if (file) ElMessage.success(`已选择：${file.name}`)
}

function runInference() {
  loading.value = true
  setTimeout(() => {
    result.value = { ...mockInference[TASK_TYPES.LICENSE_PLATE], latencyMs: 386 + Math.round(Math.random() * 120) }
    loading.value = false
    ElMessage.success('识别完成')
  }, 800)
}
</script>

<style scoped>
.plate-page {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: 16px;
  height: 100%;
}

/* ---- 摄像头大画面 ---- */
.viewport-area { min-width: 0; }

.viewport {
  position: relative;
  height: 100%;
  min-height: 480px;
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: #080c14;
}

.viewport img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  opacity: 0.9;
}

.viewport-placeholder {
  height: 100%;
  min-height: 480px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--text-muted);
  background:
    linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px),
    linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px);
  background-size: 40px 40px;
}

.detection-overlay {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.detect-rect {
  animation: breathe 2s ease-in-out infinite;
}

.viewport-top {
  position: absolute;
  top: 14px;
  left: 16px;
  display: flex;
  gap: 8px;
}

.chip {
  padding: 5px 12px;
  background: rgba(0,0,0,0.6);
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  color: var(--text-secondary);
  backdrop-filter: blur(6px);
}

.chip.live {
  color: var(--danger-color);
  border-color: rgba(255,61,0,0.4);
}

.viewport-bottom {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 14px 18px;
  background: linear-gradient(transparent, rgba(0,0,0,0.7));
}

.detect-summary {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
  color: var(--text-primary);
}

.detect-summary strong {
  color: var(--success-color);
  font-size: 18px;
}

/* ---- 侧边面板 ---- */
.side-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
  overflow-y: auto;
}

.card-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 14px;
}

.mode-tabs {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
  margin-bottom: 16px;
}

.mode-tabs button {
  padding: 10px;
  border: 1px solid var(--border-card);
  border-radius: 10px;
  background: transparent;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--duration-fast);
}

.mode-tabs button.active {
  border-color: var(--primary-color);
  background: var(--primary-soft);
  color: var(--primary-color);
}

.upload-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 24px;
  border: 1px dashed rgba(255,255,255,0.10);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--duration-fast);
}

.upload-zone:hover {
  border-color: var(--border-active);
  background: rgba(255,255,255,0.02);
}

.upload-zone .el-icon { color: var(--text-muted); }
.upload-zone span { font-size: 13px; color: var(--text-secondary); font-weight: 600; }
.upload-zone small { font-size: 11px; color: var(--text-muted); }

.rtsp-select {
  margin-top: 14px;
}

.rtsp-select label {
  display: block;
  margin-bottom: 6px;
  font-size: 11px;
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
}

.action-btn {
  width: 100%;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 16px;
  border: none;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: all var(--duration-fast);
}

.action-btn.primary {
  background: linear-gradient(135deg, var(--primary-color), #0096c7);
  color: #080c14;
  box-shadow: 0 4px 18px var(--primary-glow);
}

.action-btn.primary:hover:not(:disabled) {
  box-shadow: 0 6px 26px rgba(0,180,216,0.35);
  transform: translateY(-1px);
}

.action-btn.primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.action-btn.secondary {
  background: transparent;
  border: 1px solid var(--border-card);
  color: var(--text-secondary);
}

.action-btn.secondary:hover {
  border-color: var(--border-active);
  color: var(--text-primary);
}

/* 结果列表 */
.result-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.result-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: rgba(255,255,255,0.03);
  border-radius: var(--radius-sm);
}

.plate-tag {
  min-width: 100px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 6px;
  font-size: 16px;
  font-weight: 800;
  letter-spacing: 1px;
}

.plate-tag.blue {
  background: #1a3a6b;
  color: #88c8ff;
  border: 1.5px solid rgba(100,160,255,0.4);
}

.plate-tag.green {
  background: #0a3a1a;
  color: #66e088;
  border: 1.5px solid rgba(0,230,118,0.4);
}

.result-meta span {
  display: block;
  font-size: 12px;
  color: var(--text-secondary);
}

.result-meta span + span {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 2px;
}

.empty-result {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 28px 0;
  color: var(--text-muted);
}

.empty-result span { font-size: 13px; }
.empty-result small { font-size: 11px; }

.spinner { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
