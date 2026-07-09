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

export function buildCameraStreamUrl(sourceId, version = Date.now()) {
  const params = new URLSearchParams({ sourceId, fps: '8', t: String(version) })
  return `${CAMERA_BASE_URL}/api/v1/cameras/stream.mjpg?${params.toString()}`
}

export function buildCameraSnapshotUrl(sourceId) {
  const params = new URLSearchParams({ sourceId, t: String(Date.now()) })
  return `${CAMERA_BASE_URL}/api/v1/cameras/snapshot.jpg?${params.toString()}`
}
