import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import {
  buildCameraSnapshotUrl,
  buildCameraStreamUrl,
  listCameraSources,
  switchCameraSource
} from '@/api/camera'

const DEFAULT_SYNC_INTERVAL_MS = 2000

export function useCameraSource(taskType, options = {}) {
  const cameraSources = ref([])
  const selectedCameraSourceId = ref('')
  const cameraStatus = ref('idle')
  const cameraError = ref('')
  const streamVersion = ref(Date.now())
  const syncIntervalMs = options.syncIntervalMs ?? DEFAULT_SYNC_INTERVAL_MS
  let syncTimer = null
  let syncing = false

  const selectedCameraSource = computed(() =>
    cameraSources.value.find(source => source.id === selectedCameraSourceId.value) || null
  )

  const cameraStreamUrl = computed(() => {
    if (!selectedCameraSourceId.value) return ''
    return buildCameraStreamUrl(selectedCameraSourceId.value, streamVersion.value)
  })

  async function loadCameraSources({ silent = false } = {}) {
    if (!silent) cameraStatus.value = 'loading'
    cameraError.value = ''
    try {
      const data = await listCameraSources()
      cameraSources.value = data.sources || []
      const nextSourceId = pickDefaultSource(cameraSources.value, taskType, data.activeSourceId)
      if (nextSourceId !== selectedCameraSourceId.value) {
        selectedCameraSourceId.value = nextSourceId
        streamVersion.value = Date.now()
      }
      cameraStatus.value = cameraSources.value.length ? 'ready' : 'empty'
    } catch (error) {
      console.error(error)
      cameraStatus.value = 'offline'
      cameraError.value = '虚拟摄像头服务未连接'
    }
  }

  async function activateCameraSource() {
    if (!selectedCameraSourceId.value) return false
    cameraStatus.value = 'loading'
    cameraError.value = ''
    try {
      await switchCameraSource(selectedCameraSourceId.value)
      streamVersion.value = Date.now()
      cameraStatus.value = 'ready'
      return true
    } catch (error) {
      console.error(error)
      cameraStatus.value = 'offline'
      cameraError.value = '摄像头源切换失败'
      return false
    }
  }

  function refreshCameraPreview() {
    streamVersion.value = Date.now()
  }

  function getCameraSnapshotUrl() {
    if (!selectedCameraSourceId.value) return ''
    return buildCameraSnapshotUrl(selectedCameraSourceId.value)
  }

  async function syncCameraSources() {
    if (syncing) return
    syncing = true
    try {
      await loadCameraSources({ silent: true })
    } finally {
      syncing = false
    }
  }

  onMounted(() => {
    loadCameraSources()
    if (syncIntervalMs > 0) {
      syncTimer = setInterval(syncCameraSources, syncIntervalMs)
    }
  })

  onBeforeUnmount(() => {
    clearInterval(syncTimer)
  })

  return {
    cameraSources,
    selectedCameraSourceId,
    selectedCameraSource,
    cameraStatus,
    cameraError,
    cameraStreamUrl,
    loadCameraSources,
    syncCameraSources,
    activateCameraSource,
    refreshCameraPreview,
    getCameraSnapshotUrl
  }
}

function pickDefaultSource(sources, taskType, activeSourceId) {
  const active = sources.find(source => source.id === activeSourceId)
  if (active) return active.id

  const taskSample = sources.find(source =>
    source.sourceType !== 'device' && source.taskTypes?.includes(taskType)
  )
  if (taskSample) return taskSample.id

  return sources[0]?.id || ''
}
