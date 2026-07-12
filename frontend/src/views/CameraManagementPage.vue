<template>
  <div class="camera-management-page">
    <header class="camera-page-header">
      <div>
        <span class="eyebrow">CAMERA MATRIX</span>
        <h1>三路摄像头管理</h1>
        <p>三个槽位同时采集，车牌与交警识别会并发处理所有已开启摄像头。</p>
      </div>
      <div class="file-transport-badge">
        <el-icon><FolderOpened /></el-icon>
        <div><strong>文件帧直读</strong><span>无 WebRTC / 无跨服务图像传输</span></div>
      </div>
    </header>

    <section class="camera-slot-grid">
      <article v-for="form in forms" :key="form.slotId" class="camera-slot-card" :class="{ off: form.sourceType === 'OFF' }">
        <div class="slot-heading">
          <span class="slot-number">CAM {{ form.slotId }}</span>
          <span class="slot-status" :class="slotStatus(form.slotId)">
            <i></i>{{ statusLabel(form.slotId) }}
          </span>
        </div>

        <div class="slot-preview">
          <img v-if="cameraPreviewUrls[form.slotId]" :src="cameraPreviewUrls[form.slotId]" :alt="`摄像头 ${form.slotId} 预览`">
          <div v-else class="slot-preview-empty">
            <el-icon :size="36"><VideoCamera /></el-icon>
            <span>{{ form.sourceType === 'OFF' ? '该路已关闭' : '等待文件帧' }}</span>
          </div>
          <span class="slot-source-label">{{ typeLabel(form.sourceType) }}</span>
        </div>

        <div class="slot-form">
          <label>
            <span>输入类型</span>
            <select v-model="form.sourceType">
              <option v-for="option in typeOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
            </select>
          </label>

          <label>
            <span>摄像头名称</span>
            <input v-model.trim="form.name" type="text" :placeholder="`摄像头 ${form.slotId}`">
          </label>

          <label v-if="form.sourceType === 'SANDBOX'">
            <span>沙盘机位</span>
            <select v-model="form.path">
              <option v-for="preset in sandboxPresets" :key="preset.id" :value="preset.id">{{ preset.name }}</option>
            </select>
          </label>

          <label v-if="form.sourceType === 'RTSP'">
            <span>真实视频流</span>
            <input v-model.trim="form.path" type="url" placeholder="rtsp:// 或 http://">
          </label>

          <label v-if="form.sourceType === 'DEVICE'">
            <span>设备索引</span>
            <input v-model.number="form.deviceIndex" type="number" min="0" max="12">
          </label>

          <label v-if="['IMAGE', 'VIDEO'].includes(form.sourceType)" class="upload-field">
            <span>{{ form.sourceType === 'IMAGE' ? '图片文件' : '视频文件' }}</span>
            <input type="file" :accept="form.sourceType === 'IMAGE' ? 'image/*' : 'video/*'" @change="event => uploadMedia(form, event)">
            <small>{{ form.path ? fileName(form.path) : '尚未上传' }}</small>
          </label>
        </div>

        <div class="slot-actions">
          <button class="save-slot-button" type="button" :disabled="saving[form.slotId]" @click="saveSlot(form)">
            {{ saving[form.slotId] ? '保存中' : '应用配置' }}
          </button>
          <button class="refresh-slot-button" type="button" :disabled="form.sourceType === 'OFF'" @click="refreshCameraSlotPreview(form.slotId)">
            <el-icon><Refresh /></el-icon>
          </button>
        </div>
      </article>
    </section>
  </div>
</template>

<script setup>
import { onMounted, reactive, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getCameraData, updateCameraSlot, uploadCameraMedia } from '@/api/camera'
import { useCameraSource } from '@/composables/useCameraSource'

const typeOptions = [
  { value: 'SANDBOX', label: '沙盘摄像头' },
  { value: 'RTSP', label: '真实视频流' },
  { value: 'IMAGE', label: '图片' },
  { value: 'VIDEO', label: '视频' },
  { value: 'DEVICE', label: '本机设备' },
  { value: 'OFF', label: '关闭' }
]

const forms = reactive([1, 2, 3].map(slotId => ({ slotId, name: '', sourceType: 'OFF', path: '', deviceIndex: 0 })))
const saving = reactive({ 1: false, 2: false, 3: false })
const {
  cameraSlots,
  sandboxPresets,
  cameraPreviewUrls,
  loadCameraSlots,
  refreshCameraSlotPreview
} = useCameraSource()

let initialStateHydrated = false

watch(cameraSlots, slots => {
  if (!initialStateHydrated && slots.length) {
    hydrateForms(slots)
    initialStateHydrated = true
  }
}, { immediate: true })

onMounted(async () => {
  await loadCameraSlots()
  hydrateForms()
  initialStateHydrated = true
})

function hydrateForms(slots = cameraSlots.value) {
  slots.forEach(slot => {
    const form = forms.find(item => item.slotId === slot.slotId)
    if (!form) return
    Object.assign(form, {
      name: slot.name || '',
      sourceType: slot.sourceType || 'OFF',
      path: slot.path || '',
      deviceIndex: slot.deviceIndex || 0
    })
  })
}

async function saveSlot(form) {
  saving[form.slotId] = true
  try {
    const data = getCameraData(await updateCameraSlot(form.slotId, {
      sourceType: form.sourceType,
      name: form.name,
      path: form.path,
      deviceIndex: form.deviceIndex
    }))
    applySlot(data)
    await loadCameraSlots({ silent: true })
    hydrateForms()
    await refreshCameraSlotPreview(form.slotId)
    ElMessage.success(`摄像头 ${form.slotId} 配置已生效`)
  } catch (error) {
    if (!error.__visionDriveNotified) ElMessage.error(error.message || '摄像头配置失败')
  } finally {
    saving[form.slotId] = false
  }
}

async function uploadMedia(form, event) {
  const file = event.target.files?.[0]
  if (!file) return
  saving[form.slotId] = true
  try {
    const data = getCameraData(await uploadCameraMedia(form.slotId, file))
    applySlot(data)
    await loadCameraSlots({ silent: true })
    hydrateForms()
    await refreshCameraSlotPreview(form.slotId)
    ElMessage.success(`摄像头 ${form.slotId} 媒体已加载`)
  } catch (error) {
    if (!error.__visionDriveNotified) ElMessage.error(error.message || '媒体上传失败')
  } finally {
    saving[form.slotId] = false
    event.target.value = ''
  }
}

function applySlot(slot) {
  if (!slot?.slotId) return
  const index = cameraSlots.value.findIndex(item => item.slotId === slot.slotId)
  if (index >= 0) cameraSlots.value[index] = slot
}

function slotStatus(slotId) {
  return cameraSlots.value.find(slot => slot.slotId === slotId)?.status || 'off'
}

function statusLabel(slotId) {
  const status = slotStatus(slotId)
  return { ready: '已就绪', error: '异常', off: '已关闭' }[status] || '连接中'
}

function typeLabel(value) {
  return typeOptions.find(option => option.value === value)?.label || value
}

function fileName(path = '') {
  return path.split(/[\\/]/).pop()
}
</script>

<style scoped>
.camera-management-page { display: flex; flex-direction: column; gap: 18px; min-height: 100%; }
.camera-page-header { display: flex; align-items: center; justify-content: space-between; gap: 20px; padding: 18px 20px; border: 1px solid var(--border-card); border-radius: var(--radius-md); background: linear-gradient(100deg, rgba(0,180,216,.1), var(--bg-card) 42%); }
.eyebrow { color: var(--primary-color); font: 800 10px/1 "SF Mono", monospace; letter-spacing: 1.5px; }
.camera-page-header h1 { margin-top: 5px; font-size: 24px; }
.camera-page-header p { margin-top: 5px; color: var(--text-secondary); font-size: 12px; }
.file-transport-badge { min-width: 250px; display: flex; align-items: center; gap: 11px; padding: 10px 14px; border: 1px solid rgba(0,230,118,.22); border-radius: 11px; background: rgba(0,230,118,.06); color: var(--success-color); }
.file-transport-badge strong, .file-transport-badge span { display: block; }
.file-transport-badge strong { font-size: 12px; }
.file-transport-badge span { margin-top: 2px; color: var(--text-muted); font-size: 9px; }
.camera-slot-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }
.camera-slot-card { min-width: 0; display: flex; flex-direction: column; gap: 13px; padding: 14px; border: 1px solid var(--border-card); border-radius: var(--radius-md); background: var(--bg-card); }
.camera-slot-card.off { opacity: .72; }
.slot-heading { display: flex; align-items: center; justify-content: space-between; }
.slot-number { color: var(--text-primary); font: 800 13px/1 "SF Mono", monospace; letter-spacing: 1px; }
.slot-status { display: inline-flex; align-items: center; gap: 6px; color: var(--text-secondary); font-size: 10px; font-weight: 700; }
.slot-status i { width: 7px; height: 7px; border-radius: 50%; background: var(--text-muted); }
.slot-status.ready { color: var(--success-color); } .slot-status.ready i { background: var(--success-color); box-shadow: 0 0 8px rgba(0,230,118,.5); }
.slot-status.error { color: var(--danger-color); } .slot-status.error i { background: var(--danger-color); }
.slot-preview { position: relative; aspect-ratio: 16/9; overflow: hidden; border-radius: 11px; background: #070b12; }
.slot-preview img { width: 100%; height: 100%; display: block; object-fit: cover; }
.slot-preview-empty { height: 100%; display: grid; place-content: center; justify-items: center; gap: 8px; color: var(--text-muted); font-size: 11px; }
.slot-source-label { position: absolute; left: 9px; bottom: 9px; padding: 4px 8px; border-radius: 6px; background: rgba(8,12,20,.76); color: var(--text-secondary); font-size: 9px; font-weight: 800; }
.slot-form { display: flex; flex-direction: column; gap: 10px; }
.slot-form label { display: flex; flex-direction: column; gap: 5px; }
.slot-form label > span { color: var(--text-muted); font-size: 10px; font-weight: 700; }
.slot-form input, .slot-form select { width: 100%; min-height: 39px; padding: 0 10px; border: 1px solid var(--border-card); border-radius: 9px; outline: none; background: rgba(255,255,255,.025); color: var(--text-primary); font-size: 12px; }
.slot-form input:focus, .slot-form select:focus { border-color: var(--border-active); }
.upload-field input { padding: 7px; }
.upload-field small { overflow: hidden; color: var(--text-secondary); font-size: 9px; text-overflow: ellipsis; white-space: nowrap; }
.slot-actions { display: grid; grid-template-columns: 1fr 42px; gap: 8px; margin-top: auto; }
.save-slot-button, .refresh-slot-button { min-height: 40px; border: 1px solid rgba(0,180,216,.3); border-radius: 9px; background: rgba(0,180,216,.09); color: var(--primary-color); font-size: 11px; font-weight: 800; cursor: pointer; }
.refresh-slot-button { display: grid; place-items: center; border-color: var(--border-card); background: rgba(255,255,255,.03); color: var(--text-secondary); }
button:disabled { cursor: not-allowed; opacity: .5; }
@media (max-width: 1050px) { .camera-slot-grid { grid-template-columns: 1fr; } }
@media (max-width: 680px) { .camera-page-header { align-items: flex-start; flex-direction: column; } .file-transport-badge { width: 100%; min-width: 0; } }
</style>
