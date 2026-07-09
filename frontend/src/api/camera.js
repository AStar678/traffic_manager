import axios from 'axios'

const configuredBase = import.meta.env.VITE_CAMERA_URL || 'http://127.0.0.1:8010'
export const CAMERA_BASE_URL = configuredBase.replace(/\/$/, '')

const cameraRequest = axios.create({
  baseURL: `${CAMERA_BASE_URL}/api/v1`,
  timeout: 15000
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

/**
 * 预热摄像头：请求一帧快照，强制硬件初始化，避免流切换时黑屏等待。
 * 返回预热耗时（ms），失败不抛异常。
 */
export async function warmCameraSource(sourceId) {
  const started = performance.now()
  try {
    const url = buildCameraSnapshotUrl(sourceId)
    // 用 fetch 而非 axios，避免拦截器干扰；只需触发硬件唤醒，不关心响应体
    await fetch(url, { signal: AbortSignal.timeout(8000) })
    return Math.round(performance.now() - started)
  } catch {
    // 预热失败不阻塞流程——流连接仍会尝试
    return -1
  }
}

export function buildCameraStreamUrl(sourceId, version = Date.now()) {
  const params = new URLSearchParams({ sourceId, fps: '15', t: String(version) })
  return `${CAMERA_BASE_URL}/api/v1/cameras/stream.mjpg?${params.toString()}`
}

export function buildCameraSnapshotUrl(sourceId) {
  const params = new URLSearchParams({ sourceId, t: String(Date.now()) })
  return `${CAMERA_BASE_URL}/api/v1/cameras/snapshot.jpg?${params.toString()}`
}
