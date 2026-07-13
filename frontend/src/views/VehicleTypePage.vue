<template>
  <div class="vehicle-type-page" :class="{ embedded: props.embedded }">
    <header v-if="!props.embedded" class="vehicle-type-header">
      <div>
        <span class="section-kicker">PP-VEHICLE · GPU</span>
        <h1>车辆类型实时追踪</h1>
        <p>三路摄像头共享一份 GPU 模型，按摄像头隔离轨迹编号。</p>
      </div>
      <div class="vehicle-type-actions">
        <span class="service-state" :class="{ active: recognizing }"><i></i>{{ recognizing ? '持续识别中' : '识别已停止' }}</span>
        <button class="control-button" type="button" @click="toggleRecognition">
          <el-icon><component :is="recognizing ? 'VideoPause' : 'VideoPlay'" /></el-icon>
          {{ recognizing ? '停止识别' : '开始识别' }}
        </button>
      </div>
    </header>

    <MultiCameraRecognitionDetail
      task-type="vehicle_type"
      :result="result"
      :recognizing="recognizing"
      :preloaded-streams="props.preloadedStreams"
    />
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import MultiCameraRecognitionDetail from '@/components/common/MultiCameraRecognitionDetail.vue'
import { getInferenceData, inferenceCameras } from '@/api/inference'
import { TASK_TYPES } from '@/utils/constants'

const props = defineProps({
  embedded: { type: Boolean, default: false },
  externalResult: { type: Object, default: null },
  externalRecognizing: { type: Boolean, default: false },
  preloadedStreams: { type: Object, default: null }
})
const emit = defineEmits(['toggle-recognition'])

const localResult = ref(emptyResult())
const localRecognizing = ref(false)
const loading = ref(false)
const result = computed(() => props.externalResult || localResult.value)
const recognizing = computed(() => props.externalResult ? props.externalRecognizing : localRecognizing.value)
let timer

async function recognizeOnce({ silent = false } = {}) {
  if (loading.value || !localRecognizing.value) return
  loading.value = true
  try {
    const data = getInferenceData(await inferenceCameras(TASK_TYPES.VEHICLE_TYPE)) || {}
    localResult.value = { ...emptyResult(), ...data, detections: data.detections || [] }
  } catch (error) {
    console.error(error)
    if (!silent) ElMessage.error('车辆类型识别失败，请检查 PP-Vehicle GPU 服务')
  } finally {
    loading.value = false
  }
}

function startRecognition() {
  localRecognizing.value = true
  void recognizeOnce()
  clearInterval(timer)
  timer = window.setInterval(() => void recognizeOnce({ silent: true }), 900)
}

function stopRecognition() {
  localRecognizing.value = false
  clearInterval(timer)
  timer = undefined
}

function toggleRecognition() {
  if (props.externalResult) {
    emit('toggle-recognition')
    return
  }
  if (localRecognizing.value) stopRecognition()
  else startRecognition()
}

function emptyResult() {
  return {
    taskType: TASK_TYPES.VEHICLE_TYPE,
    latencyMs: 0,
    detections: [],
    detectionCount: 0,
    cameras: []
  }
}

onMounted(() => {
  if (!props.embedded && !props.externalResult) startRecognition()
})
onBeforeUnmount(stopRecognition)
</script>

<style scoped>
.vehicle-type-page { min-height: 100%; display: flex; flex-direction: column; gap: 14px; }
.vehicle-type-page.embedded { min-height: 620px; }
.vehicle-type-header { display: flex; align-items: center; justify-content: space-between; gap: 18px; padding: 16px 18px; border: 1px solid var(--border-card); border-radius: var(--radius-md); background: linear-gradient(100deg, rgba(0, 180, 216, .1), var(--bg-card) 45%); }
.vehicle-type-header h1 { margin: 4px 0 0; font-size: 23px; }
.vehicle-type-header p { margin-top: 5px; color: var(--text-secondary); font-size: 12px; }
.section-kicker { color: var(--primary-color); font: 800 10px/1 "SF Mono", monospace; letter-spacing: 1.2px; }
.vehicle-type-actions { display: flex; align-items: center; gap: 12px; }
.service-state { display: inline-flex; align-items: center; gap: 7px; color: var(--text-muted); font-size: 12px; font-weight: 700; }
.service-state i { width: 8px; height: 8px; border-radius: 50%; background: currentColor; }
.service-state.active { color: var(--success-color); }
.service-state.active i { box-shadow: 0 0 10px currentColor; }
.control-button { height: 40px; display: inline-flex; align-items: center; gap: 7px; padding: 0 16px; border: 1px solid var(--border-active); border-radius: 10px; background: var(--primary-soft); color: var(--primary-color); cursor: pointer; font-family: inherit; font-weight: 800; }
.control-button:hover, .control-button:focus-visible { background: rgba(0, 180, 216, .16); outline: 2px solid rgba(0, 180, 216, .28); outline-offset: 2px; }
@media (max-width: 680px) { .vehicle-type-header { align-items: flex-start; flex-direction: column; } .vehicle-type-actions { width: 100%; justify-content: space-between; } }
</style>
