import { computed, onMounted, reactive, ref } from 'vue'
import { getCameraData, getCameraFrameBlob, listCameraSlots } from '@/api/camera'

const cameraSlots = ref([])
const sandboxPresets = ref([])
const sourceTypes = ref([])
const selectedCameraSlotId = ref(1)
const cameraStatus = ref('idle')
const cameraError = ref('')
const cameraPreviewUrls = reactive({})
const cameraPreviewVersions = reactive({})
const cameraVideoRef = ref(null)
const cameraVideoReady = ref(false)

let slotsLoading = false
let slotsLoadPromise = null
let previewsLoading = false
let pollingStarted = false

const activeCameraSlots = computed(() => cameraSlots.value.filter(slot => slot.sourceType !== 'OFF'))
const selectedCameraSource = computed(() =>
  cameraSlots.value.find(slot => slot.slotId === Number(selectedCameraSlotId.value)) || activeCameraSlots.value[0] || null
)
const selectedCameraSourceId = computed({
  get: () => selectedCameraSlotId.value,
  set: value => { selectedCameraSlotId.value = Number(value) || 1 }
})
const cameraDisplayUrl = computed(() => cameraPreviewUrls[selectedCameraSource.value?.slotId] || '')
const cameraPreviewUrl = cameraDisplayUrl
const cameraStreamUrl = cameraDisplayUrl
const cameraTransport = ref('file')
const previewStatus = computed(() => cameraDisplayUrl.value ? 'ready' : cameraStatus.value)

export function useCameraSource(_taskType, options = {}) {
  const syncIntervalMs = options.syncIntervalMs ?? 4000
  const previewIntervalMs = options.previewIntervalMs ?? 700

  async function loadCameraSlots({ silent = false } = {}) {
    if (slotsLoadPromise) return slotsLoadPromise
    slotsLoading = true
    slotsLoadPromise = (async () => {
      if (!silent) cameraStatus.value = 'loading'
      try {
        const data = getCameraData(await listCameraSlots()) || {}
        cameraSlots.value = data.slots || []
        sandboxPresets.value = data.sandboxPresets || []
        sourceTypes.value = data.sourceTypes || []
        if (!cameraSlots.value.some(slot => slot.slotId === Number(selectedCameraSlotId.value) && slot.sourceType !== 'OFF')) {
          selectedCameraSlotId.value = activeCameraSlots.value[0]?.slotId || 1
        }
        cameraStatus.value = cameraSlots.value.length ? 'ready' : 'empty'
        cameraError.value = ''
        await refreshAllPreviews()
      } catch (error) {
        console.error(error)
        cameraStatus.value = 'offline'
        cameraError.value = '主服务摄像头模块未连接'
      } finally {
        slotsLoading = false
      }
    })()
    try {
      return await slotsLoadPromise
    } finally {
      slotsLoadPromise = null
    }
  }

  async function refreshCameraSlotPreview(slotId) {
    const slot = cameraSlots.value.find(item => item.slotId === Number(slotId))
    if (!slot || slot.sourceType === 'OFF') {
      releasePreview(slotId)
      return
    }
    try {
      const blob = await getCameraFrameBlob(slotId)
      if (!(blob instanceof Blob)) throw new Error('camera_frame_not_blob')
      const nextUrl = URL.createObjectURL(blob)
      const previousUrl = cameraPreviewUrls[slotId]
      cameraPreviewUrls[slotId] = nextUrl
      cameraPreviewVersions[slotId] = Date.now()
      if (previousUrl) URL.revokeObjectURL(previousUrl)
      slot.status = 'ready'
      slot.error = ''
      if (Number(slotId) === Number(selectedCameraSlotId.value)) cameraError.value = ''
    } catch (error) {
      console.error(error)
      slot.status = 'error'
      slot.error = error.response?.data?.message || '取帧失败'
    }
  }

  async function refreshAllPreviews() {
    if (previewsLoading) return
    previewsLoading = true
    try {
      await Promise.allSettled(activeCameraSlots.value.map(slot => refreshCameraSlotPreview(slot.slotId)))
    } finally {
      previewsLoading = false
    }
  }

  function selectCameraSlot(slotId) {
    const slot = cameraSlots.value.find(item => item.slotId === Number(slotId))
    if (slot?.sourceType === 'OFF') return false
    selectedCameraSlotId.value = Number(slotId)
    cameraError.value = slot?.error || ''
    void refreshCameraSlotPreview(slotId)
    return true
  }

  function refreshCameraPreview() {
    return refreshAllPreviews()
  }

  function requestPreviewFrame() {
    return refreshCameraSlotPreview(selectedCameraSlotId.value)
  }

  function startPolling() {
    if (pollingStarted) return
    pollingStarted = true
    window.setInterval(() => { void refreshAllPreviews() }, previewIntervalMs)
    window.setInterval(() => { void loadCameraSlots({ silent: true }) }, syncIntervalMs)
  }

  function releasePreview(slotId) {
    const previousUrl = cameraPreviewUrls[slotId]
    if (previousUrl) URL.revokeObjectURL(previousUrl)
    delete cameraPreviewUrls[slotId]
    delete cameraPreviewVersions[slotId]
  }

  async function activateCameraSource() {
    return selectCameraSlot(selectedCameraSlotId.value)
  }

  async function getCameraSnapshotUrl() {
    const slot = selectedCameraSource.value
    return slot?.frameUrl || ''
  }

  function markCameraVideoReady() {
    cameraVideoReady.value = false
  }

  onMounted(() => {
    void loadCameraSlots()
    startPolling()
  })

  return {
    cameraSources: cameraSlots,
    cameraSlots,
    activeCameraSlots,
    sandboxPresets,
    sourceTypes,
    selectedCameraSourceId,
    selectedCameraSlotId,
    selectedCameraSource,
    cameraStatus,
    cameraError,
    cameraStreamUrl,
    cameraPreviewUrl,
    cameraDisplayUrl,
    cameraPreviewUrls,
    cameraPreviewVersions,
    cameraVideoRef,
    cameraVideoReady,
    cameraTransport,
    previewStatus,
    loadCameraSources: loadCameraSlots,
    loadCameraSlots,
    syncCameraSources: loadCameraSlots,
    activateCameraSource,
    selectCameraSlot,
    refreshCameraPreview,
    refreshAllPreviews,
    refreshCameraSlotPreview,
    requestPreviewFrame,
    markCameraVideoReady,
    getCameraVideoElement: () => null,
    getCameraSnapshotUrl
  }
}
