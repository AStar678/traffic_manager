<template>
  <div class="plate-page">
    <!-- 主画面：ADAS前视摄像头 -->
    <div class="viewport-area">
      <div class="viewport">
        <!-- 实时预览：iframe 嵌入 WebRTC -->
        <iframe
          v-if="isLiveMode && webRtcUrl"
          :src="webRtcUrl"
          class="stream-iframe"
          allow="camera;microphone"
        ></iframe>

        <!-- 实时预览待机 -->
        <div v-if="isLiveMode && !webRtcUrl" class="viewport-placeholder">
          <el-icon :size="48"><VideoCamera /></el-icon>
          <span>选择摄像头并启动实时预览</span>
          <small>需要先启动 mediamtx 流媒体服务器</small>
        </div>

        <!-- 非预览模式：本地摄像头 -->
        <video
          v-if="!isLiveMode"
          id="plate-cam"
          class="camera-video"
          :style="{ opacity: cameraActive ? 1 : 0 }"
          autoplay playsinline muted
        ></video>
        <!-- 降级占位 -->
        <div v-if="!isLiveMode && !cameraActive" class="viewport-placeholder">
          <el-icon :size="48"><Camera /></el-icon>
          <span>{{ cameraError || '前置摄像头待机' }}</span>
          <small>点击右侧上传图片或连接RTSP流开始检测</small>
        </div>

        <!-- 检测框叠加层（实时预览模式下隐藏，因为标注由后端绘制） -->
        <svg v-if="result.detections.length && !isLiveMode" class="detect-svg" viewBox="0 0 1200 720" preserveAspectRatio="none">
          <g v-for="box in result.detections" :key="box.objectId">
            <rect
              :x="box.bbox.x1" :y="box.bbox.y1"
              :width="box.bbox.x2 - box.bbox.x1"
              :height="box.bbox.y2 - box.bbox.y1"
              fill="none" stroke="#34a853" stroke-width="4" class="detect-rect"
            />
            <rect
              :x="box.bbox.x1"
              :y="Math.max(0, box.bbox.y1 - 30)"
              :width="(box.plateNumber || '').length * 22 + 28" height="26" rx="13" fill="#34a853"
            />
            <text
              :x="box.bbox.x1 + 14" :y="Math.max(17, box.bbox.y1 - 11)"
              fill="#0a0d14" font-size="17" font-weight="800"
            >{{ box.plateNumber }}</text>
          </g>
        </svg>

        <div class="scan-line-animated"></div>

        <!-- 顶部信息（非预览模式：模拟数据；预览模式：隐藏） -->
        <div v-if="!isLiveMode" class="viewport-top">
          <span class="badge-live">● LIVE</span>
          <span class="badge-info">RTSP {{ inputMode === 'video' ? '视频分析' : '本地摄像头' }}</span>
          <span class="badge-info">FPS 24</span>
        </div>
        <div v-if="isLiveMode && streamActive" class="viewport-top">
          <span class="badge-live">● LIVE</span>
          <span class="badge-info">{{ currentCameraLabel }}</span>
          <span class="badge-info">RTSP {{ selectedRtsp }}</span>
        </div>

        <!-- 底部检测摘要 -->
        <div v-if="result.detections.length && !isLiveMode" class="viewport-bottom">
          <div class="bottom-left">
            <span>检测到 <strong>{{ result.detections.length }}</strong> 辆车</span>
          </div>
          <div class="bottom-right">
            <span>耗时 {{ result.latencyMs }}ms</span>
            <span>端到端 ≤ 5s</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 右侧操作面板（设计文档规定：左输入+中预览+右结果） -->
    <div class="side-panel">
      <!-- 输入控制区 -->
      <div class="card">
        <div class="mode-tabs">
          <button :class="{ active: inputMode === 'image' }" @click="inputMode = 'image'">图片识别</button>
          <button :class="{ active: inputMode === 'video' }" @click="inputMode = 'video'">视频/RTSP</button>
        </div>

        <div v-if="inputMode === 'video'" class="video-sub-tabs">
          <button :class="{ active: videoSubMode === 'job' }" @click="videoSubMode = 'job'">异步分析任务</button>
          <button :class="{ active: videoSubMode === 'live' }" @click="videoSubMode = 'live'">实时预览</button>
        </div>

        <div class="upload-zone" @click="triggerUpload">
          <input ref="fileInput" type="file" accept=".jpg,.jpeg,.png,.bmp" style="display:none" @change="onFileSelected">
          <el-icon :size="26"><UploadFilled /></el-icon>
          <span>点击上传图片</span>
          <small>jpg / png / bmp · ≤ 10MB</small>
        </div>

        <!-- 视频/RTSP 模式 -->
        <div v-if="inputMode === 'video'" class="rtsp-controls">
          <label>沙盘摄像头通道</label>
          <el-select v-model="selectedRtsp" style="width:100%">
            <el-option v-for="ch in allRtspChannels" :key="ch.value" :label="ch.label" :value="ch.value" />
          </el-select>

          <!-- 异步分析任务 -->
          <template v-if="videoSubMode === 'job'">
            <button class="action-btn primary" :disabled="loading" @click="runInference">
              <el-icon v-if="loading" class="spinner"><Loading /></el-icon>
              {{ loading ? '识别中...' : '创建视频任务' }}
            </button>
            <div class="job-info" v-if="showJob">
              <span>任务 {{ videoJob.jobId }}</span>
              <el-progress :percentage="videoJob.progress" :stroke-width="6" />
              <small>已处理 {{ videoJob.processedFrames }} / {{ videoJob.totalFrames }} 帧</small>
            </div>
          </template>

          <!-- 实时预览 -->
          <template v-if="videoSubMode === 'live'">
            <button
              class="action-btn primary"
              :disabled="streamLoading"
              @click="streamActive ? stopStream() : startStream()"
            >
              <el-icon v-if="streamLoading" class="spinner"><Loading /></el-icon>
              {{ streamLoading ? '连接中...' : streamActive ? '停止预览' : '启动实时预览' }}
            </button>
            <div v-if="streamActive && webRtcUrl" class="stream-info">
              <span class="stream-live">● 实时预览中</span>
              <small>{{ webRtcUrl }}</small>
            </div>
          </template>
        </div>

        <!-- 图片模式按钮 -->
        <button v-if="inputMode === 'image'" class="action-btn primary" :disabled="loading" @click="runInference">
          <el-icon v-if="loading" class="spinner"><Loading /></el-icon>
          {{ loading ? '识别中...' : '上传并同步识别' }}
        </button>
      </div>

      <!-- 识别结果区 -->
      <div class="card">
        <h3 class="card-title">结构化识别结果</h3>
        <div v-if="result.detections.length" class="result-list">
          <div v-for="item in result.detections" :key="item.objectId" class="result-item">
            <div class="plate-tag" :class="item.plateColor">{{ item.plateNumber }}</div>
            <div class="result-meta">
              <span>{{ item.plateType }}</span>
              <span>检测 {{ Math.round(item.detectionConfidence * 100) }}% · OCR {{ Math.round(item.ocrConfidence * 100) }}%</span>
            </div>
          </div>
        </div>
        <div v-else class="empty-result">
          <el-icon :size="28"><Picture /></el-icon>
          <span>暂无识别结果</span>
          <small>上传图片后自动识别并展示</small>
        </div>

        <button class="action-btn secondary" style="margin-top:14px" v-if="result.detections.length" @click="saveRecord">
          <el-icon><FolderAdd /></el-icon> 写入历史记录
        </button>
      </div>

      <!-- 业务链路 -->
      <div class="card">
        <h3 class="card-title">业务链路</h3>
        <div class="pipeline">
          <span v-for="step in pipeline" :key="step">{{ step }}</span>
        </div>
      </div>

      <button class="back-btn" @click="$router.push('/dashboard')">
        <el-icon><ArrowLeft /></el-icon> 返回驾驶主屏
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { mockInference, mockVideoJob, rtspChannels, businessPipelines } from '@/utils/mockData'
import { TASK_TYPES } from '@/utils/constants'
import request from '@/api/request'

const result = ref(mockInference[TASK_TYPES.LICENSE_PLATE])
const loading = ref(false)
const inputMode = ref('image')
const videoSubMode = ref('job')  // job=异步任务, live=实时预览
const selectedRtsp = ref(rtspChannels[0].value)
const showJob = ref(false)
const fileInput = ref(null)
const videoJob = mockVideoJob

const isLiveMode = computed(() => inputMode.value === 'video' && videoSubMode.value === 'live')

const currentCameraLabel = computed(() => {
  const ch = allRtspChannels.find(c => c.value === selectedRtsp.value)
  return ch ? ch.label : selectedRtsp.value
})

// ===== 实时推流 =====
const streamLoading = ref(false)
const streamActive = ref(false)
const webRtcUrl = ref('')

// 完整的 12 路摄像头（用于推流模式）
const allRtspChannels = [
  { label: 'live1 桥面', value: 'live1' },
  { label: 'live2 停车场出口', value: 'live2' },
  { label: 'live3 行人检测', value: 'live3' },
  { label: 'live4 消防车识别', value: 'live4' },
  { label: 'live5 桥出口', value: 'live5' },
  { label: 'live6 桥入口', value: 'live6' },
  { label: 'live7 道路2', value: 'live7' },
  { label: 'live8 隧道(事故)', value: 'live8' },
  { label: 'live9 隧道(计数)', value: 'live9' },
  { label: 'live10 道路3', value: 'live10' },
  { label: 'live11 停车场入口', value: 'live11' },
  { label: 'live12 道路1', value: 'live12' },
]

async function startStream() {
  const cameraId = selectedRtsp.value
  streamLoading.value = true
  try {
    const res = await request.post(`/cameras/${cameraId}/stream/start`)
    const data = res.data || res
    if (res.code === 0 || data.success) {
      streamActive.value = true
      webRtcUrl.value = data.webRtcUrl
      ElMessage.success('推流已启动')
    } else {
      ElMessage.error(data.message || '启动失败')
    }
  } catch (e) {
    ElMessage.error('无法连接后端，请确认后端服务和 mediamtx 均已启动')
  } finally {
    streamLoading.value = false
  }
}

async function stopStream() {
  const cameraId = selectedRtsp.value
  try {
    await request.post(`/cameras/${cameraId}/stream/stop`)
  } catch (_) {}
  streamActive.value = false
  webRtcUrl.value = ''
  ElMessage.info('推流已停止')
}

// ===== 摄像头（用 id 定位，绕开 ref 时序） =====
const cameraActive = ref(false)
const cameraError = ref('')
let camStream = null

async function startCamera() {
  if (camStream) return
  cameraError.value = ''
  try {
    camStream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'environment' },
      audio: false,
    })
    cameraActive.value = true
    await new Promise(r => setTimeout(r, 200))
    const el = document.querySelector('#plate-cam')
    if (el) { el.srcObject = camStream; try { await el.play() } catch (_) {} }
  } catch (err) {
    console.warn('[Plate Camera]', err.name, err.message)
    if (err.name === 'NotAllowedError') cameraError.value = '摄像头权限被拒绝'
    else if (err.name === 'NotFoundError') cameraError.value = '未检测到摄像头'
    else {
      try {
        camStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false })
        cameraActive.value = true
        await new Promise(r => setTimeout(r, 200))
        const el = document.querySelector('#plate-cam')
        if (el) { el.srcObject = camStream; try { await el.play() } catch (_) {} }
        return
      } catch (_) {}
      cameraError.value = err.message
    }
  }
}

function stopCamera() {
  if (camStream) { camStream.getTracks().forEach(t => t.stop()); camStream = null }
  cameraActive.value = false
}

onMounted(async () => { await startCamera() })
onBeforeUnmount(() => { stopCamera() })

const pipeline = computed(() => inputMode.value === 'image' ? businessPipelines.image : businessPipelines.video)

function triggerUpload() { fileInput.value?.click() }

function onFileSelected(e) {
  const file = e.target.files?.[0]
  if (file) ElMessage.success(`已选择：${file.name}`)
}

function runInference() {
  loading.value = true
  if (inputMode.value === 'video') showJob.value = true
  setTimeout(() => {
    result.value = { ...mockInference[TASK_TYPES.LICENSE_PLATE], latencyMs: 350 + Math.round(Math.random() * 150) }
    loading.value = false
    ElMessage.success(inputMode.value === 'image' ? '同步识别完成' : '视频任务已创建')
  }, 800)
}

function saveRecord() {
  ElMessage.success('识别记录已保存')
}
</script>

<style scoped>
.plate-page {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 330px;
  gap: 14px;
  height: 100%;
}

/* 摄像头画面 */
.viewport-area { min-width: 0; }

.viewport {
  position: relative;
  height: 100%;
  min-height: 460px;
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: #060a10;
}

.viewport img,
.camera-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
  position: absolute;
  inset: 0;
}
.viewport img { opacity: 0.92; }
.camera-video { background: #000; }

.viewport-placeholder {
  height: 100%; min-height: 460px;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  gap: 10px;
  color: var(--text-muted);
  background:
    linear-gradient(90deg, rgba(255,255,255,0.015) 1px, transparent 1px),
    linear-gradient(rgba(255,255,255,0.015) 1px, transparent 1px);
  background-size: 40px 40px;
}

.viewport-placeholder small { font-size: 12px; opacity: 0.6; }

.detect-svg {
  position: absolute; inset: 0;
  width: 100%; height: 100%;
  pointer-events: none;
  z-index: 4;
}

.detect-rect {
  animation: breathe 2s ease-in-out infinite;
}

.viewport-top {
  position: absolute; top: 12px; left: 14px;
  display: flex; gap: 6px;
  z-index: 6;
}

.badge-live {
  padding: 4px 10px;
  background: rgba(0,0,0,0.55);
  border: 1px solid rgba(234,67,53,0.4);
  border-radius: 999px;
  font-size: 11px; font-weight: 700;
  color: var(--danger-color);
  backdrop-filter: blur(4px);
}

.badge-info {
  padding: 4px 10px;
  background: rgba(0,0,0,0.45);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 999px;
  font-size: 11px; font-weight: 600;
  color: var(--text-secondary);
  backdrop-filter: blur(4px);
}

.viewport-bottom {
  position: absolute; bottom: 0; left: 0; right: 0;
  display: flex; justify-content: space-between;
  padding: 12px 16px;
  background: linear-gradient(transparent, rgba(0,0,0,0.65));
  z-index: 6;
}

.bottom-left span { font-size: 13px; color: var(--text-primary); }
.bottom-left strong { color: var(--success-color); font-size: 17px; }
.bottom-right { display: flex; gap: 14px; font-size: 12px; color: var(--text-secondary); }

/* 侧面板 */
.side-panel { display: flex; flex-direction: column; gap: 12px; overflow-y: auto; }

.card-title {
  font-size: 11px; font-weight: 700;
  color: var(--text-secondary);
  text-transform: uppercase; letter-spacing: 0.5px;
  margin-bottom: 12px;
}

.mode-tabs { display: grid; grid-template-columns: repeat(2, 1fr); gap: 6px; margin-bottom: 10px; }

.mode-tabs button {
  padding: 9px; border: 1px solid var(--border-card);
  border-radius: 10px; background: transparent;
  color: var(--text-secondary); font-size: 12px; font-weight: 600;
  cursor: pointer; transition: all var(--duration-fast);
}
.mode-tabs button.active {
  border-color: var(--primary-color); background: var(--primary-soft); color: var(--primary-color);
}

.video-sub-tabs { display: grid; grid-template-columns: repeat(2, 1fr); gap: 4px; margin-bottom: 10px; }
.video-sub-tabs button {
  padding: 6px 8px; border: 1px solid var(--border-card);
  border-radius: 8px; background: transparent;
  color: var(--text-secondary); font-size: 11px; font-weight: 600;
  cursor: pointer; transition: all var(--duration-fast);
}
.video-sub-tabs button.active {
  border-color: var(--primary-color); color: var(--primary-color);
}

.upload-zone {
  display: flex; flex-direction: column; align-items: center; gap: 6px;
  padding: 20px; border: 1px dashed rgba(255,255,255,0.08);
  border-radius: var(--radius-md); cursor: pointer;
  transition: all var(--duration-fast);
}
.upload-zone:hover { border-color: var(--border-active); background: rgba(255,255,255,0.015); }
.upload-zone .el-icon { color: var(--text-muted); }
.upload-zone span { font-size: 13px; color: var(--text-secondary); font-weight: 600; }
.upload-zone small { font-size: 11px; color: var(--text-muted); }

.rtsp-controls { margin-top: 0; }
.rtsp-controls label { display: block; margin-bottom: 6px; font-size: 11px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; }

.job-info { margin-top: 12px; padding: 10px; background: rgba(255,255,255,0.02); border-radius: 8px; }
.job-info span { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.job-info small { display: block; margin-top: 4px; font-size: 11px; color: var(--text-muted); }

.action-btn {
  width: 100%; height: 42px;
  display: flex; align-items: center; justify-content: center; gap: 8px;
  margin-top: 14px; border: none; border-radius: 12px;
  font-size: 14px; font-weight: 700; cursor: pointer;
  transition: all var(--duration-fast);
}
.action-btn.primary { background: var(--primary-color); color: #fff; box-shadow: 0 4px 18px var(--primary-glow); }
.action-btn.primary:hover:not(:disabled) { box-shadow: 0 6px 26px rgba(26,115,232,0.35); transform: translateY(-1px); }
.action-btn.primary:disabled { opacity: 0.5; cursor: not-allowed; }
.action-btn.secondary { background: transparent; border: 1px solid var(--border-card); color: var(--text-secondary); }
.action-btn.secondary:hover { border-color: var(--border-active); color: var(--text-primary); }

/* 结果 */
.result-list { display: flex; flex-direction: column; gap: 8px; }
.result-item { display: flex; align-items: center; gap: 10px; padding: 10px; background: rgba(255,255,255,0.02); border-radius: var(--radius-sm); }

.plate-tag {
  min-width: 96px; height: 32px; display: grid; place-items: center;
  border-radius: 6px; font-size: 15px; font-weight: 800; letter-spacing: 1px;
}
.plate-tag.blue { background: #1a3a6b; color: #88c8ff; border: 1.5px solid rgba(100,160,255,0.35); }
.plate-tag.green { background: #0a3a1a; color: #66e088; border: 1.5px solid rgba(0,230,118,0.35); }

.result-meta span { display: block; font-size: 11px; color: var(--text-secondary); }
.result-meta span + span { font-size: 10px; color: var(--text-muted); margin-top: 2px; }

.empty-result { display: flex; flex-direction: column; align-items: center; gap: 6px; padding: 24px 0; color: var(--text-muted); }
.empty-result span { font-size: 13px; }
.empty-result small { font-size: 11px; }

.pipeline { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; }
.pipeline span {
  padding: 8px 6px; background: var(--primary-soft);
  border-radius: 8px; text-align: center;
  font-size: 11px; font-weight: 600; color: var(--primary-color);
}

.spinner { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.back-btn {
  display: flex; align-items: center; justify-content: center; gap: 6px;
  width: 100%; padding: 10px; margin-top: 8px;
  border: 1px solid var(--border-card); border-radius: 12px;
  background: transparent; color: var(--text-secondary);
  font-size: 13px; font-weight: 600; cursor: pointer;
}
.back-btn:hover { border-color: var(--border-active); color: var(--text-primary); }

/* 实时预览状态 */
.stream-info { margin-top: 10px; padding: 10px; background: rgba(52,168,83,0.08); border-radius: 8px; }
.stream-info small { display: block; margin-top: 4px; font-size: 11px; color: var(--text-muted); word-break: break-all; }

.stream-live { font-size: 13px; font-weight: 700; color: var(--success-color); }

.stream-iframe {
  width: 100%;
  height: 100%;
  border: none;
  position: absolute;
  inset: 0;
  z-index: 3;
}
</style>
