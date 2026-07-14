import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { getCameraData, getCameraFrameBlob, listCameraSlots } from '@/api/camera'

export const JPEG_TARGET_FPS = 25
export const JPEG_FRAME_INTERVAL_MS = Math.floor(1000 / JPEG_TARGET_FPS)
export const JPEG_RETRY_INTERVAL_MS = 1000
export const FRAME_SYNC_BUFFER_MS = JPEG_FRAME_INTERVAL_MS
export const PROCESSED_STREAM_DELAY_MS = 0

const cameraSlots = ref([])
const sandboxPresets = ref([])
const sourceTypes = ref([])
const selectedCameraSlotId = ref(1)
const cameraStatus = ref('idle')
const cameraError = ref('')
const cameraPreviewUrls = reactive({})
const cameraPreviewVersions = reactive({})
const cameraJpegStates = reactive({})

let slotsLoadPromise = null
let rawPollingConsumers = 0
let rawPollingSuspended = false
const rawControllers = new Map()
const rawPollingTimers = new Map()

const activeCameraSlots = computed(() => cameraSlots.value.filter(slot => slot.sourceType !== 'OFF'))
const selectedCameraSource = computed(() =>
  cameraSlots.value.find(slot => slot.slotId === Number(selectedCameraSlotId.value)) || activeCameraSlots.value[0] || null
)
const selectedCameraSourceId = computed({
  get: () => selectedCameraSlotId.value,
  set: value => { selectedCameraSlotId.value = Number(value) || 1 }
})

export function useCameraSource(taskType, options = {}) {
  const syncIntervalMs = options.syncIntervalMs ?? 4000
  const enabled = options.enabled !== false
  const processedSource = options.processed && enabled ? useProcessedCameraStreams(taskType) : null
  const previewCollection = processedSource?.cameraPreviewUrls || cameraPreviewUrls
  const stateCollection = processedSource?.cameraJpegStates || cameraJpegStates
  const cameraDisplayUrl = computed(() => previewCollection[selectedCameraSource.value?.slotId] || '')
  const cameraTransport = computed(() => options.processed ? 'processed-jpeg' : 'jpeg')
  const previewStatus = computed(() => cameraDisplayUrl.value ? 'ready' : cameraStatus.value)
  let slotSyncTimer = null

  async function loadCameraSlots({ silent = false } = {}) {
    if (slotsLoadPromise) return slotsLoadPromise
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
        cleanupInactivePreviews(previewCollection)
        syncRawPollingSlots()
        if (options.processed) void processedSource?.refreshAllPreviews()
      } catch (error) {
        console.error(error)
        cameraStatus.value = 'offline'
        cameraError.value = '主服务摄像头模块未连接'
      }
    })()
    try {
      return await slotsLoadPromise
    } finally {
      slotsLoadPromise = null
    }
  }

  function selectCameraSlot(slotId) {
    const slot = cameraSlots.value.find(item => item.slotId === Number(slotId))
    if (slot?.sourceType === 'OFF') return false
    selectedCameraSlotId.value = Number(slotId)
    cameraError.value = slot?.error || ''
    if (options.processed) void processedSource?.refreshCameraSlotPreview(slotId)
    else void refreshRawCameraSlotPreview(slotId)
    return true
  }

  function refreshCameraPreview() {
    return options.processed ? processedSource?.refreshAllPreviews() : refreshAllRawPreviews()
  }

  function requestPreviewFrame() {
    return refreshCameraSlotPreview(selectedCameraSlotId.value)
  }

  function refreshCameraSlotPreview(slotId) {
    return options.processed
      ? processedSource?.refreshCameraSlotPreview(slotId)
      : refreshRawCameraSlotPreview(slotId)
  }

  function startPolling() {
    if (!options.processed) startRawPolling()
    if (!slotSyncTimer) {
      slotSyncTimer = window.setInterval(() => { void loadCameraSlots({ silent: true }) }, syncIntervalMs)
    }
  }

  function stopPolling() {
    if (!options.processed) stopRawPolling()
    if (slotSyncTimer) window.clearInterval(slotSyncTimer)
    slotSyncTimer = null
  }

  onMounted(() => {
    if (!enabled) return
    startPolling()
    void loadCameraSlots()
  })
  onBeforeUnmount(() => {
    if (enabled) stopPolling()
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
    cameraStreamUrl: cameraDisplayUrl,
    cameraPreviewUrl: cameraDisplayUrl,
    cameraDisplayUrl,
    cameraPreviewUrls: previewCollection,
    cameraPreviewVersions,
    cameraJpegStates: stateCollection,
    cameraTransport,
    previewStatus,
    loadCameraSources: loadCameraSlots,
    loadCameraSlots,
    syncCameraSources: loadCameraSlots,
    activateCameraSource: () => selectCameraSlot(selectedCameraSlotId.value),
    selectCameraSlot,
    refreshCameraPreview,
    refreshAllPreviews: refreshCameraPreview,
    refreshCameraSlotPreview,
    requestPreviewFrame,
    suspendCameraJpegPolling,
    resumeCameraJpegPolling,
    getCameraVideoElement: () => null,
    getCameraSnapshotUrl: async () => selectedCameraSource.value?.frameUrl || ''
  }
}

async function refreshRawCameraSlotPreview(slotId) {
  return refreshJpegSlot({
    slotId,
    urls: cameraPreviewUrls,
    states: cameraJpegStates,
    controllers: rawControllers
  })
}

async function refreshAllRawPreviews() {
  const results = await Promise.allSettled(activeCameraSlots.value.map(slot => refreshRawCameraSlotPreview(slot.slotId)))
  return results.some(result => result.status === 'fulfilled' && result.value)
}

function startRawPolling() {
  rawPollingConsumers += 1
  syncRawPollingSlots()
}

function stopRawPolling() {
  rawPollingConsumers = Math.max(0, rawPollingConsumers - 1)
  if (rawPollingConsumers > 0) return
  clearPollingTimers(rawPollingTimers)
  abortControllers(rawControllers)
}

function scheduleRawSlot(slotId, delay = currentPollDelay()) {
  const active = activeCameraSlots.value.some(slot => Number(slot.slotId) === Number(slotId))
  if (rawPollingConsumers === 0 || rawPollingSuspended || !active || rawPollingTimers.has(slotId) || rawControllers.has(slotId)) return
  const timer = window.setTimeout(async () => {
    rawPollingTimers.delete(slotId)
    if (rawPollingConsumers === 0 || rawPollingSuspended) return
    const startedAt = monotonicNow()
    const succeeded = await refreshRawCameraSlotPreview(slotId)
    const elapsed = monotonicNow() - startedAt
    scheduleRawSlot(slotId, succeeded ? currentPollDelay(elapsed) : JPEG_RETRY_INTERVAL_MS)
  }, delay)
  rawPollingTimers.set(slotId, timer)
}

function syncRawPollingSlots() {
  if (rawPollingConsumers === 0 || rawPollingSuspended) return
  const activeIds = new Set(activeCameraSlots.value.map(slot => Number(slot.slotId)))
  rawPollingTimers.forEach((timer, slotId) => {
    if (activeIds.has(Number(slotId))) return
    window.clearTimeout(timer)
    rawPollingTimers.delete(slotId)
    rawControllers.get(slotId)?.abort()
    rawControllers.delete(slotId)
  })
  activeIds.forEach(slotId => scheduleRawSlot(slotId, 0))
}

export function suspendCameraJpegPolling() {
  rawPollingSuspended = true
  clearPollingTimers(rawPollingTimers)
  abortControllers(rawControllers)
}

export function resumeCameraJpegPolling() {
  if (!rawPollingSuspended) return
  rawPollingSuspended = false
  syncRawPollingSlots()
}

export function useProcessedCameraStreams(taskType) {
  return useIsolatedJpegStreams(taskType)
}

export function useDelayedCameraStreams() {
  return useIsolatedJpegStreams(null)
}

function useIsolatedJpegStreams(taskType) {
  const urls = reactive({})
  const states = reactive({})
  const controllers = new Map()
  const timers = new Map()
  let stopped = false

  async function refreshCameraSlotPreview(slotId) {
    return refreshJpegSlot({ slotId, taskType, urls, states, controllers })
  }

  async function refreshAllPreviews() {
    if (stopped) return false
    const results = await Promise.allSettled(activeCameraSlots.value.map(slot => refreshCameraSlotPreview(slot.slotId)))
    return results.some(result => result.status === 'fulfilled' && result.value)
  }

  function scheduleSlot(slotId, delay = currentPollDelay()) {
    const active = activeCameraSlots.value.some(slot => Number(slot.slotId) === Number(slotId))
    if (stopped || !active || timers.has(slotId) || controllers.has(slotId)) return
    const timer = window.setTimeout(async () => {
      timers.delete(slotId)
      if (stopped) return
      const startedAt = monotonicNow()
      const succeeded = await refreshCameraSlotPreview(slotId)
      const elapsed = monotonicNow() - startedAt
      scheduleSlot(slotId, succeeded ? currentPollDelay(elapsed) : JPEG_RETRY_INTERVAL_MS)
    }, delay)
    timers.set(slotId, timer)
  }

  function syncSlots() {
    const activeIds = new Set(activeCameraSlots.value.map(slot => Number(slot.slotId)))
    timers.forEach((timer, slotId) => {
      if (activeIds.has(Number(slotId))) return
      window.clearTimeout(timer)
      timers.delete(slotId)
      controllers.get(slotId)?.abort()
      controllers.delete(slotId)
    })
    activeIds.forEach(slotId => scheduleSlot(slotId, 0))
  }

  const stopWatchingSlots = watch(cameraSlots, () => {
    cleanupInactivePreviews(urls)
    syncSlots()
  }, { deep: true })

  onMounted(async () => {
    if (!cameraSlots.value.length) {
      try {
        const data = getCameraData(await listCameraSlots()) || {}
        cameraSlots.value = data.slots || []
        sandboxPresets.value = data.sandboxPresets || []
        sourceTypes.value = data.sourceTypes || []
      } catch (error) {
        console.error('详情页摄像头列表加载失败', error)
      }
    }
    syncSlots()
  })
  onBeforeUnmount(() => {
    stopped = true
    stopWatchingSlots()
    clearPollingTimers(timers)
    abortControllers(controllers)
    releaseAllPreviews(urls)
  })

  return {
    cameraSlots,
    activeCameraSlots,
    cameraPreviewUrls: urls,
    cameraJpegStates: states,
    processed: Boolean(taskType),
    taskType,
    delayMs: 0,
    refreshAllPreviews,
    refreshCameraSlotPreview
  }
}

async function refreshJpegSlot({ slotId, taskType = null, urls, states, controllers }) {
  const slot = cameraSlots.value.find(item => Number(item.slotId) === Number(slotId))
  if (!slot || slot.sourceType === 'OFF') {
    releasePreview(urls, slotId)
    states[slotId] = 'off'
    return false
  }

  const previousController = controllers.get(slotId)
  if (previousController) return false
  const controller = new AbortController()
  controllers.set(slotId, controller)
  if (!urls[slotId]) states[slotId] = 'loading'
  try {
    const blob = await getCameraFrameBlob(slotId, { taskType, signal: controller.signal })
    if (!(blob instanceof Blob)) throw new Error('camera_frame_not_blob')
    if (controllers.get(slotId) !== controller) return false
    replacePreviewUrl(urls, slotId, blob)
    cameraPreviewVersions[slotId] = Date.now()
    states[slotId] = 'ready'
    slot.status = 'ready'
    slot.error = ''
    if (Number(slotId) === Number(selectedCameraSlotId.value)) cameraError.value = ''
    return true
  } catch (error) {
    if (error.name === 'AbortError') return false
    states[slotId] = urls[slotId] ? 'retrying' : 'error'
    slot.error = error.message || 'JPEG 取帧失败'
    return false
  } finally {
    if (controllers.get(slotId) === controller) controllers.delete(slotId)
  }
}

function replacePreviewUrl(urls, slotId, blob) {
  const nextUrl = URL.createObjectURL(blob)
  const previousUrl = urls[slotId]
  urls[slotId] = nextUrl
  if (!previousUrl) return
  const release = () => URL.revokeObjectURL(previousUrl)
  if (typeof window.requestAnimationFrame === 'function') window.requestAnimationFrame(release)
  else window.setTimeout(release, 0)
}

function releasePreview(urls, slotId) {
  const previousUrl = urls[slotId]
  if (previousUrl) URL.revokeObjectURL(previousUrl)
  delete urls[slotId]
  delete cameraPreviewVersions[slotId]
}

function cleanupInactivePreviews(urls) {
  const activeIds = new Set(activeCameraSlots.value.map(slot => String(slot.slotId)))
  Object.keys(urls).forEach(slotId => {
    if (!activeIds.has(String(slotId))) releasePreview(urls, slotId)
  })
}

function releaseAllPreviews(urls) {
  Object.keys(urls).forEach(slotId => releasePreview(urls, slotId))
}

function abortControllers(controllers) {
  controllers.forEach(controller => controller.abort())
  controllers.clear()
}

function clearPollingTimers(timers) {
  timers.forEach(timer => window.clearTimeout(timer))
  timers.clear()
}

function currentPollDelay(elapsed = 0) {
  if (typeof document !== 'undefined' && document.hidden) return JPEG_RETRY_INTERVAL_MS
  return Math.max(0, JPEG_FRAME_INTERVAL_MS - Math.max(0, elapsed))
}

function monotonicNow() {
  return typeof performance !== 'undefined' ? performance.now() : Date.now()
}
