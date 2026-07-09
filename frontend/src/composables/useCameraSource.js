import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import {
  buildCameraSnapshotUrl,
  buildCameraStreamUrl,
  listCameraSources,
  switchCameraSource,
  warmCameraSource
} from '@/api/camera'

const DEFAULT_SYNC_INTERVAL_MS = 5000

export function useCameraSource(taskType, options = {}) {
  const cameraSources = ref([])
  const selectedCameraSourceId = ref('')
  const cameraStatus = ref('idle')
  const cameraError = ref('')
  const streamVersion = ref(Date.now())
  const isStreamReady = ref(false)
  const syncIntervalMs = options.syncIntervalMs ?? DEFAULT_SYNC_INTERVAL_MS
  let syncTimer = null
  let syncing = false
  let streamReadyTimer = null

  const selectedCameraSource = computed(() =>
    cameraSources.value.find(source => source.id === selectedCameraSourceId.value) || null
  )

  const cameraStreamUrl = computed(() => {
    if (!selectedCameraSourceId.value || !isStreamReady.value) return ''
    return buildCameraStreamUrl(selectedCameraSourceId.value, streamVersion.value)
  })

  /**
   * 切换摄像头源的完整流程：
   * 1. 通知后端切换源     → switchCameraSource
   * 2. 预热摄像头硬件     → warmCameraSource（快照触发初始化）
   * 3. 延迟等待流就绪     → setStreamReady
   * 4. 刷新 MJPEG 流 URL  → streamVersion++
   *
   * 预热步骤解决了物理摄像头切换时 2~5 秒的黑屏问题：
   * 先拉一帧快照，让摄像头完成上电→曝光→编码的全流程，
   * 再切 MJPEG 流时第一帧几乎立刻到达。
   */
  async function activateCameraSource() {
    if (!selectedCameraSourceId.value) return false

    cameraStatus.value = 'loading'
    cameraError.value = ''
    clearStreamReady()

    try {
      // Step 1: 后端切换源
      await switchCameraSource(selectedCameraSourceId.value)

      // Step 2: 预热——拉一帧快照触发硬件初始化
      const warmMs = await warmCameraSource(selectedCameraSourceId.value)
      if (warmMs >= 0) {
        console.log(`[camera] 预热完成 ${warmMs}ms`)
      }

      // Step 3: 切流 URL 并延迟标记就绪（给 MJPEG 编码器缓冲时间）
      streamVersion.value = Date.now()
      setStreamReady()

      cameraStatus.value = 'ready'
      return true
    } catch (error) {
      console.error(error)
      cameraStatus.value = 'offline'
      cameraError.value = '摄像头源切换失败'
      return false
    }
  }

  /**
   * 刷新预览——轻量版切换，仅更新流 URL 版本号。
   * 适用于摄像头源未变化、仅需要强制刷新的场景。
   */
  function refreshCameraPreview() {
    if (!selectedCameraSourceId.value) return
    clearStreamReady()
    streamVersion.value = Date.now()
    setStreamReady()
  }

  function setStreamReady() {
    clearStreamReady()
    // MJPEG 流建立连接 + 收到首帧通常需要 100~300ms
    // 给 400ms 缓冲，避免一闪而过的"等待画面"
    streamReadyTimer = setTimeout(() => {
      isStreamReady.value = true
    }, 400)
  }

  function clearStreamReady() {
    isStreamReady.value = false
    clearTimeout(streamReadyTimer)
    streamReadyTimer = null
  }

  async function loadCameraSources({ silent = false } = {}) {
    if (!silent) cameraStatus.value = 'loading'
    cameraError.value = ''
    try {
      const data = await listCameraSources()
      cameraSources.value = data.sources || []
      const nextSourceId = pickDefaultSource(cameraSources.value, taskType, data.activeSourceId)
      if (nextSourceId !== selectedCameraSourceId.value) {
        selectedCameraSourceId.value = nextSourceId
        clearStreamReady()
        streamVersion.value = Date.now()
        setStreamReady()
      }
      cameraStatus.value = cameraSources.value.length ? 'ready' : 'empty'
    } catch (error) {
      console.error(error)
      cameraStatus.value = 'offline'
      cameraError.value = '虚拟摄像头服务未连接'
    }
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
    clearStreamReady()
  })

  return {
    cameraSources,
    selectedCameraSourceId,
    selectedCameraSource,
    cameraStatus,
    cameraError,
    cameraStreamUrl,
    isStreamReady,
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
