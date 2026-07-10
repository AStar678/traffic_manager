import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  buildCameraFrameUrl,
  buildCameraSnapshotUrl,
  buildCameraStreamUrl,
  createCameraWebRtcAnswer,
  getCameraFrameInfo,
  listCameraSources,
  switchCameraSource
} from '@/api/camera'

const DEFAULT_SYNC_INTERVAL_MS = 2000
const PREVIEW_LOAD_TIMEOUT_MS = 4000
const ICE_GATHERING_TIMEOUT_MS = 2500
const DEFAULT_WEBRTC_FPS = 15

const cameraSources = ref([])
const selectedCameraSourceId = ref('')
const cameraStatus = ref('idle')
const cameraError = ref('')
const cameraPreviewUrl = ref('')
const previewStatus = ref('idle')
const cameraVideoRef = ref(null)
const cameraVideoReady = ref(false)
const cameraTransport = ref('webrtc')
const streamVersion = ref(Date.now())
let syncing = false
let rtcPeer = null
let remoteStream = null
let connectGeneration = 0
let lastPreviewFrame = null
let persistentVideoElement = null

const selectedCameraSource = computed(() =>
  cameraSources.value.find(source => source.id === selectedCameraSourceId.value) || null
)

const cameraStreamUrl = computed(() => {
  if (!selectedCameraSourceId.value) return ''
  return buildCameraStreamUrl(selectedCameraSourceId.value, streamVersion.value)
})

const cameraDisplayUrl = computed(() => cameraPreviewUrl.value)

export function useCameraSource(taskType, options = {}) {
  const syncIntervalMs = options.syncIntervalMs ?? DEFAULT_SYNC_INTERVAL_MS
  const iceServers = options.iceServers ?? []
  const preferredFps = options.fps ?? DEFAULT_WEBRTC_FPS
  let syncTimer = null

  async function loadCameraSources({ silent = false } = {}) {
    if (!silent && !rtcPeer) cameraStatus.value = 'loading'
    cameraError.value = ''
    try {
      const data = await listCameraSources()
      cameraSources.value = data.sources || []
      const nextSourceId = pickDefaultSource(cameraSources.value, taskType, data.activeSourceId)
      const sourceChanged = nextSourceId !== selectedCameraSourceId.value
      if (sourceChanged) {
        selectedCameraSourceId.value = nextSourceId
        streamVersion.value = Date.now()
        if (!rtcPeer) {
          resetCameraPreview()
        }
      }
      cameraStatus.value = cameraSources.value.length ? 'ready' : 'empty'
      if (selectedCameraSourceId.value && !rtcPeer) {
        await connectWebRtcStream()
      } else if (rtcPeer) {
        previewStatus.value = 'ready'
        cameraVideoReady.value = Boolean(remoteStream)
        await attachVideoStream()
      }
    } catch (error) {
      console.error(error)
      cameraStatus.value = 'offline'
      cameraError.value = '虚拟摄像头服务未连接'
      stopWebRtcStream()
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
      if (rtcPeer) {
        previewStatus.value = 'ready'
        cameraVideoReady.value = Boolean(remoteStream)
        await attachVideoStream()
      } else {
        await connectWebRtcStream()
      }
      return true
    } catch (error) {
      console.error(error)
      cameraStatus.value = 'offline'
      cameraError.value = '摄像头源切换失败'
      stopWebRtcStream()
      return false
    }
  }

  function refreshCameraPreview() {
    streamVersion.value = Date.now()
    if (rtcPeer) {
      void attachVideoStream()
      return
    }
    void connectWebRtcStream()
  }

  async function getCameraSnapshotUrl() {
    if (!selectedCameraSourceId.value) return ''
    try {
      const frameInfo = await getCameraFrameInfo(selectedCameraSourceId.value)
      return buildCameraSnapshotUrl(selectedCameraSourceId.value, frameInfo)
    } catch (error) {
      console.error(error)
      return buildCameraSnapshotUrl(selectedCameraSourceId.value)
    }
  }

  function resetCameraPreview() {
    connectGeneration += 1
    lastPreviewFrame = null
    cameraPreviewUrl.value = ''
    previewStatus.value = selectedCameraSourceId.value ? 'loading' : 'idle'
    cameraVideoReady.value = false
    stopWebRtcStream()
  }

  function requestPreviewFrame({ force = false } = {}) {
    if (force) refreshCameraPreview()
    else if (!rtcPeer && selectedCameraSourceId.value) void connectWebRtcStream()
  }

  async function connectWebRtcStream() {
    if (!selectedCameraSourceId.value) return

    if (!window.RTCPeerConnection) {
      cameraError.value = '当前浏览器不支持 WebRTC 视频传输'
      previewStatus.value = 'error'
      await loadPreviewFrame({ force: true })
      return
    }

    const generation = ++connectGeneration
    stopWebRtcStream()
    previewStatus.value = 'loading'
    cameraVideoReady.value = false
    cameraTransport.value = 'webrtc'

    try {
      const pc = new RTCPeerConnection({ iceServers })
      rtcPeer = pc
      const incomingStream = new MediaStream()
      remoteStream = incomingStream
      pc.addTransceiver('video', { direction: 'recvonly' })

      pc.ontrack = event => {
        if (generation !== connectGeneration) return
        const stream = event.streams?.[0] || incomingStream
        if (!event.streams?.length) {
          stream.addTrack(event.track)
        }
        remoteStream = stream
        attachVideoStream()
        markCameraVideoReady()
      }

      pc.onconnectionstatechange = () => {
        if (generation !== connectGeneration) return
        if (pc.connectionState === 'connected') {
          cameraError.value = ''
          previewStatus.value = 'ready'
        }
        if (['failed', 'disconnected', 'closed'].includes(pc.connectionState)) {
          cameraVideoReady.value = false
          previewStatus.value = pc.connectionState === 'closed' ? 'idle' : 'error'
        }
      }

      const offer = await pc.createOffer()
      await pc.setLocalDescription(offer)
      await waitForIceGatheringComplete(pc)

      const answer = await createCameraWebRtcAnswer({
        sourceId: null,
        sdp: pc.localDescription.sdp,
        type: pc.localDescription.type,
        fps: preferredFps
      })

      if (generation !== connectGeneration) {
        pc.close()
        return
      }

      await pc.setRemoteDescription(new RTCSessionDescription(answer))
      await attachVideoStream()
    } catch (error) {
      console.error(error)
      if (generation !== connectGeneration) return
      cameraError.value = 'WebRTC 视频连接失败'
      previewStatus.value = 'error'
      stopWebRtcStream()
      await loadPreviewFrame({ force: true })
    }
  }

  function stopWebRtcStream() {
    if (rtcPeer) {
      rtcPeer.ontrack = null
      rtcPeer.onconnectionstatechange = null
      rtcPeer.close()
      rtcPeer = null
    }
    if (remoteStream) {
      remoteStream.getTracks().forEach(track => track.stop())
      remoteStream = null
    }
    if (cameraVideoRef.value) {
      cameraVideoRef.value.srcObject = null
    }
    if (persistentVideoElement) {
      persistentVideoElement.srcObject = null
    }
    cameraVideoReady.value = false
  }

  async function attachVideoStream() {
    await nextTick()
    const video = mountPersistentVideo(cameraVideoRef.value)
    if (!video || !remoteStream) return
    if (video.srcObject !== remoteStream) {
      video.srcObject = remoteStream
    }
    video.muted = true
    video.playsInline = true
    video.autoplay = true
    try {
      await video.play()
    } catch (error) {
      console.debug('等待用户手势后播放 WebRTC 视频', error)
    }
  }

  function markCameraVideoReady() {
    if (!remoteStream) return
    cameraError.value = ''
    cameraVideoReady.value = true
    previewStatus.value = 'ready'
  }

  function getCameraVideoElement() {
    return persistentVideoElement || cameraVideoRef.value
  }

  async function loadPreviewFrame({ force = false } = {}) {
    const sourceId = selectedCameraSourceId.value
    if (!sourceId) return

    try {
      let frameInfo = null
      try {
        frameInfo = await getCameraFrameInfo(sourceId)
      } catch (error) {
        console.error(error)
      }

      if (!force && cameraPreviewUrl.value && isSamePreviewFrame(frameInfo, lastPreviewFrame)) {
        previewStatus.value = 'ready'
        return
      }

      const nextUrl = buildCameraFrameUrl(sourceId, frameInfo)
      await preloadImage(nextUrl)
      lastPreviewFrame = frameInfo
      cameraPreviewUrl.value = nextUrl
      previewStatus.value = 'ready'
      cameraTransport.value = 'snapshot'
    } catch (error) {
      console.error(error)
      previewStatus.value = cameraPreviewUrl.value ? 'ready' : 'error'
    }
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

  watch(cameraVideoRef, () => {
    void attachVideoStream()
  })

  onMounted(() => {
    void loadCameraSources()
    void attachVideoStream()
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
    cameraPreviewUrl,
    cameraDisplayUrl,
    cameraVideoRef,
    cameraVideoReady,
    cameraTransport,
    previewStatus,
    loadCameraSources,
    syncCameraSources,
    activateCameraSource,
    refreshCameraPreview,
    requestPreviewFrame,
    markCameraVideoReady,
    getCameraVideoElement,
    getCameraSnapshotUrl
  }
}

function mountPersistentVideo(target) {
  if (!target || typeof document === 'undefined') return null

  if (!persistentVideoElement) {
    persistentVideoElement = document.createElement('video')
    persistentVideoElement.autoplay = true
    persistentVideoElement.muted = true
    persistentVideoElement.playsInline = true
    persistentVideoElement.setAttribute('playsinline', '')
  }

  const host = target.tagName === 'VIDEO' ? target.parentElement : target
  if (!host) return persistentVideoElement

  if (target.tagName === 'VIDEO' && target !== persistentVideoElement) {
    persistentVideoElement.className = target.className
    syncScopedAttributes(target, persistentVideoElement)
    applyPersistentVideoStyle(target, persistentVideoElement)
    target.style.display = 'none'
  }

  if (persistentVideoElement.parentElement !== host) {
    host.insertBefore(persistentVideoElement, target.tagName === 'VIDEO' ? target : null)
  }

  return persistentVideoElement
}

function syncScopedAttributes(source, target) {
  Array.from(target.attributes)
    .filter(attribute => attribute.name.startsWith('data-v-'))
    .forEach(attribute => target.removeAttribute(attribute.name))

  Array.from(source.attributes)
    .filter(attribute => attribute.name.startsWith('data-v-'))
    .forEach(attribute => target.setAttribute(attribute.name, ''))
}

function applyPersistentVideoStyle(source, target) {
  const isAbsoluteLayer = source.classList.contains('camera-stream')
  Object.assign(target.style, {
    width: '100%',
    height: '100%',
    display: 'block',
    objectFit: 'contain',
    background: '#070b12',
    position: isAbsoluteLayer ? 'absolute' : 'static',
    inset: isAbsoluteLayer ? '0' : 'auto',
    opacity: source.classList.contains('camera-stream') ? '0.9' : '',
  })
}

function waitForIceGatheringComplete(peerConnection) {
  if (peerConnection.iceGatheringState === 'complete') return Promise.resolve()
  return new Promise(resolve => {
    const timeout = window.setTimeout(done, ICE_GATHERING_TIMEOUT_MS)

    function done() {
      window.clearTimeout(timeout)
      peerConnection.removeEventListener('icegatheringstatechange', onStateChange)
      resolve()
    }

    function onStateChange() {
      if (peerConnection.iceGatheringState === 'complete') done()
    }

    peerConnection.addEventListener('icegatheringstatechange', onStateChange)
  })
}

function preloadImage(url) {
  return new Promise((resolve, reject) => {
    const image = new Image()
    const timeout = window.setTimeout(() => {
      image.onload = null
      image.onerror = null
      reject(new Error('视频帧加载超时'))
    }, PREVIEW_LOAD_TIMEOUT_MS)
    image.decoding = 'async'
    image.onload = () => {
      window.clearTimeout(timeout)
      resolve()
    }
    image.onerror = () => {
      window.clearTimeout(timeout)
      reject(new Error('视频帧加载失败'))
    }
    image.src = url
  })
}

function isSamePreviewFrame(nextFrame, previousFrame) {
  if (!nextFrame || !previousFrame) return false
  if (nextFrame.frameIndex !== undefined && previousFrame.frameIndex !== undefined) {
    return nextFrame.frameIndex === previousFrame.frameIndex
  }
  if (nextFrame.timestampMs !== undefined && previousFrame.timestampMs !== undefined) {
    return nextFrame.timestampMs === previousFrame.timestampMs
  }
  return false
}

function pickDefaultSource(sources, taskType, activeSourceId) {
  const globalActive = sources.find(source => source.id === activeSourceId)
  if (globalActive) return globalActive.id

  const candidates = taskType ? sources.filter(source => supportsTask(source, taskType)) : sources
  const taskSample = candidates.find(source =>
    source.sourceType !== 'device' && source.taskTypes?.includes(taskType)
  )
  if (taskSample) return taskSample.id

  return candidates[0]?.id || sources[0]?.id || ''
}

function supportsTask(source, taskType) {
  if (!taskType) return true
  return !source.taskTypes?.length || source.taskTypes.includes(taskType)
}
