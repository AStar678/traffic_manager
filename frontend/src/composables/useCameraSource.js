import { computed, onMounted, reactive, ref, watch } from 'vue'
import { getCameraData, getCameraFrameBlob, listCameraSlots } from '@/api/camera'

const cameraSlots = ref([])
const sandboxPresets = ref([])
const sourceTypes = ref([])
const selectedCameraSlotId = ref(1)
const cameraStatus = ref('idle')
const cameraError = ref('')
const cameraPreviewUrls = reactive({})
const cameraPreviewVersions = reactive({})
const cameraWebRtcStreams = reactive({})
const cameraWebRtcStates = reactive({})
const cameraVideoRef = ref(null)
const cameraPeers = new Map()
const cameraPeerSessions = new Map()
const cameraPeerFingerprints = new Map()
const cameraReconnectTimers = new Map()
const cameraConnectTasks = new Map()
let iceConfigPromise = null
let iceConfigCache = null
const webRtcClientId = getWebRtcClientId()

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
const selectedCameraStream = computed(() => cameraWebRtcStreams[selectedCameraSource.value?.slotId] || null)
const cameraVideoReady = computed(() => Boolean(selectedCameraStream.value))
const cameraPreviewUrl = cameraDisplayUrl
const cameraStreamUrl = cameraDisplayUrl
const cameraTransport = computed(() => selectedCameraStream.value ? 'webrtc' : 'file')
const previewStatus = computed(() => cameraDisplayUrl.value ? 'ready' : cameraStatus.value)

watch([cameraVideoRef, selectedCameraStream], ([element, stream]) => {
  if (!element || element.srcObject === stream) return
  element.srcObject = stream
  if (stream) void element.play().catch(() => {})
}, { flush: 'post' })

export function useCameraSource(_taskType, options = {}) {
  const syncIntervalMs = options.syncIntervalMs ?? 4000
  const fallbackIntervalMs = options.fallbackIntervalMs ?? 3000

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
        void synchronizeWebRtcConnections()
        void refreshFallbackPreviews()
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

  async function refreshFallbackPreviews() {
    if (previewsLoading) return
    const fallbackSlots = activeCameraSlots.value.filter(slot => !cameraWebRtcStreams[slot.slotId])
    if (!fallbackSlots.length) return
    previewsLoading = true
    try {
      await Promise.allSettled(fallbackSlots.map(slot => refreshCameraSlotPreview(slot.slotId)))
    } finally {
      previewsLoading = false
    }
  }

  function selectCameraSlot(slotId) {
    const slot = cameraSlots.value.find(item => item.slotId === Number(slotId))
    if (slot?.sourceType === 'OFF') return false
    selectedCameraSlotId.value = Number(slotId)
    cameraError.value = slot?.error || ''
    attachSelectedStream()
    if (!cameraWebRtcStreams[slotId]) void refreshCameraSlotPreview(slotId)
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
    window.setInterval(() => { void refreshFallbackPreviews() }, fallbackIntervalMs)
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
    attachSelectedStream()
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
    cameraWebRtcStreams,
    cameraWebRtcStates,
    selectedCameraStream,
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

function slotFingerprint(slot) {
  return JSON.stringify([slot.sourceType, slot.path, slot.deviceIndex])
}

async function synchronizeWebRtcConnections() {
  if (typeof RTCPeerConnection === 'undefined') return
  const activeIds = new Set(activeCameraSlots.value.map(slot => Number(slot.slotId)))
  for (const slotId of cameraPeers.keys()) {
    if (!activeIds.has(Number(slotId))) closeCameraPeer(slotId)
  }
  await Promise.allSettled(activeCameraSlots.value.map(slot => connectCameraPeer(slot)))
}

function connectCameraPeer(slot) {
  const slotId = Number(slot.slotId)
  const fingerprint = slotFingerprint(slot)
  if (cameraPeers.has(slotId) && cameraPeerFingerprints.get(slotId) === fingerprint) return Promise.resolve()
  const currentTask = cameraConnectTasks.get(slotId)
  if (currentTask?.fingerprint === fingerprint) return currentTask.promise
  const promise = establishCameraPeer(slot, slotId, fingerprint).finally(() => {
    if (cameraConnectTasks.get(slotId)?.promise === promise) cameraConnectTasks.delete(slotId)
  })
  cameraConnectTasks.set(slotId, { fingerprint, promise })
  return promise
}

async function establishCameraPeer(slot, slotId, fingerprint) {
  closeCameraPeer(slotId)
  cameraWebRtcStates[slotId] = 'connecting'

  const peer = new RTCPeerConnection(await getIceConfiguration())
  cameraPeers.set(slotId, peer)
  cameraPeerFingerprints.set(slotId, fingerprint)
  peer.addTransceiver('video', { direction: 'recvonly' })

  peer.ontrack = event => {
    const stream = event.streams?.[0] || new MediaStream([event.track])
    cameraWebRtcStreams[slotId] = stream
    cameraWebRtcStates[slotId] = 'streaming'
    if (slotId === Number(selectedCameraSlotId.value)) attachSelectedStream()
  }
  peer.onconnectionstatechange = () => {
    const state = peer.connectionState
    cameraWebRtcStates[slotId] = state
    if (state === 'connected') {
      clearReconnectTimer(slotId)
      const slotState = cameraSlots.value.find(item => Number(item.slotId) === slotId)
      if (slotState) slotState.status = 'ready'
      return
    }
    if (state === 'failed' || state === 'closed') scheduleReconnect(slotId, 1500, true)
    if (state === 'disconnected') scheduleReconnect(slotId, 10000, false)
  }

  try {
    const offer = await peer.createOffer()
    await peer.setLocalDescription(offer)
    await waitForIceGathering(peer)
    const response = await fetch(`/webrtc/api/v1/webrtc/offer/${slotId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        type: peer.localDescription.type,
        sdp: peer.localDescription.sdp,
        clientId: webRtcClientId
      })
    })
    const answer = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(answer.detail || `WebRTC 信令失败 (${response.status})`)
    cameraPeerSessions.set(slotId, answer.sessionId)
    await peer.setRemoteDescription({ type: answer.type, sdp: answer.sdp })
  } catch (error) {
    console.error(`摄像头 ${slotId} WebRTC 连接失败`, error)
    cameraWebRtcStates[slotId] = 'error'
    const slotState = cameraSlots.value.find(item => Number(item.slotId) === slotId)
    if (slotState) slotState.error = error.message || 'WebRTC 连接失败'
    closeCameraPeer(slotId)
    scheduleReconnect(slotId)
  }
}

function getWebRtcClientId() {
  const key = 'visiondrive-webrtc-client-id'
  try {
    const existing = window.sessionStorage.getItem(key)
    if (existing) return existing
    const generated = window.crypto?.randomUUID?.() || `tab-${Date.now()}-${Math.random().toString(16).slice(2)}`
    window.sessionStorage.setItem(key, generated)
    return generated
  } catch {
    return `tab-${Date.now()}-${Math.random().toString(16).slice(2)}`
  }
}

async function getIceConfiguration() {
  const now = Math.floor(Date.now() / 1000)
  if (iceConfigCache && Number(iceConfigCache.expiresAt || 0) > now + 60) {
    return {
      iceServers: iceConfigCache.iceServers,
      iceTransportPolicy: iceConfigCache.iceTransportPolicy || 'all'
    }
  }
  if (!iceConfigPromise) {
    iceConfigPromise = fetch('/webrtc/api/v1/webrtc/ice-config')
      .then(async response => {
        const data = await response.json().catch(() => ({}))
        if (!response.ok) throw new Error(data.detail || `ICE 配置获取失败 (${response.status})`)
        iceConfigCache = data
        return data
      })
      .finally(() => { iceConfigPromise = null })
  }
  try {
    const config = await iceConfigPromise
    return {
      iceServers: config.iceServers || [],
      iceTransportPolicy: config.iceTransportPolicy || 'all'
    }
  } catch (error) {
    console.warn('TURN 配置不可用，回退到直连 WebRTC', error)
    const stunUrl = import.meta.env.VITE_WEBRTC_STUN_URL
    return { iceServers: stunUrl ? [{ urls: stunUrl }] : [] }
  }
}

function waitForIceGathering(peer) {
  if (peer.iceGatheringState === 'complete') return Promise.resolve()
  return new Promise(resolve => {
    const timeout = window.setTimeout(finish, 6000)
    function finish() {
      window.clearTimeout(timeout)
      peer.removeEventListener('icegatheringstatechange', onChange)
      resolve()
    }
    function onChange() {
      if (peer.iceGatheringState === 'complete') finish()
    }
    peer.addEventListener('icegatheringstatechange', onChange)
  })
}

function scheduleReconnect(slotId, delay = 1500, closeImmediately = true) {
  if (cameraReconnectTimers.has(slotId)) return
  if (closeImmediately) closeCameraPeer(slotId)
  const timer = window.setTimeout(() => {
    cameraReconnectTimers.delete(slotId)
    if (!closeImmediately) closeCameraPeer(slotId)
    const slot = cameraSlots.value.find(item => Number(item.slotId) === Number(slotId))
    if (slot?.sourceType !== 'OFF') void connectCameraPeer(slot)
  }, delay)
  cameraReconnectTimers.set(slotId, timer)
}

function clearReconnectTimer(slotId) {
  const timer = cameraReconnectTimers.get(slotId)
  if (timer) window.clearTimeout(timer)
  cameraReconnectTimers.delete(slotId)
}

function closeCameraPeer(slotId, closeRemote = true) {
  clearReconnectTimer(slotId)
  const peer = cameraPeers.get(slotId)
  if (peer) {
    peer.ontrack = null
    peer.onconnectionstatechange = null
    peer.close()
  }
  const sessionId = cameraPeerSessions.get(slotId)
  if (closeRemote && sessionId) {
    void fetch(`/webrtc/api/v1/webrtc/session/${sessionId}`, { method: 'DELETE' }).catch(() => {})
  }
  cameraPeers.delete(slotId)
  cameraPeerSessions.delete(slotId)
  cameraPeerFingerprints.delete(slotId)
  delete cameraWebRtcStreams[slotId]
}

function attachSelectedStream() {
  const element = cameraVideoRef.value
  const stream = selectedCameraStream.value
  if (!element || element.srcObject === stream) return
  element.srcObject = stream
  if (stream) void element.play().catch(() => {})
}
