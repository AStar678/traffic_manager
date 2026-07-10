import axios from 'axios'

const configuredBase = import.meta.env.VITE_CAMERA_URL || 'http://127.0.0.1:8010'
export const CAMERA_BASE_URL = configuredBase.replace(/\/$/, '')

const cameraRequest = axios.create({
  baseURL: `${CAMERA_BASE_URL}/api/v1`,
  timeout: 10000
})

function unwrap(response) {
  return response.data?.data || response.data
}

export async function listCameraSources() {
  return unwrap(await cameraRequest.get('/cameras/sources'))
}

export async function switchCameraSource(sourceId) {
  return unwrap(await cameraRequest.post('/cameras/source', { sourceId }))
}

export async function getCameraFrameInfo(sourceId) {
  return unwrap(await cameraRequest.get('/cameras/frame-info', { params: { sourceId } }))
}

export async function createCameraWebRtcAnswer({ sourceId, sdp, type = 'offer', fps = 15 }) {
  return unwrap(await cameraRequest.post('/cameras/webrtc/offer', {
    sourceId,
    sdp,
    type,
    fps
  }, { timeout: 15000 }))
}

export async function publishBrowserCameraWebRtc({ sourceId, sdp, type = 'offer', fps = 15 }) {
  return unwrap(await cameraRequest.post('/cameras/webrtc/publish', {
    sourceId,
    sdp,
    type,
    fps
  }, { timeout: 15000 }))
}

export function buildCameraStreamUrl(sourceId, version = Date.now()) {
  const params = new URLSearchParams({ sourceId, fps: '15', quality: '96', t: String(version) })
  return `${CAMERA_BASE_URL}/api/v1/cameras/stream.mjpg?${params.toString()}`
}

export function buildCameraFrameUrl(sourceId, frameInfo = null) {
  const params = new URLSearchParams({ sourceId, t: String(Date.now()) })
  if (frameInfo?.frameIndex !== undefined) params.set('frameIndex', String(frameInfo.frameIndex))
  if (frameInfo?.timestampMs !== undefined) params.set('captureTs', String(frameInfo.timestampMs))
  return `${CAMERA_BASE_URL}/api/v1/cameras/snapshot.jpg?${params.toString()}`
}

export function buildCameraSnapshotUrl(sourceId, frameInfo = null) {
  const params = new URLSearchParams({ sourceId, t: String(Date.now()) })
  if (frameInfo?.frameIndex !== undefined) params.set('frameIndex', String(frameInfo.frameIndex))
  if (frameInfo?.timestampMs !== undefined) params.set('captureTs', String(frameInfo.timestampMs))
  return `${CAMERA_BASE_URL}/api/v1/cameras/snapshot.png?${params.toString()}`
}
