import request from './request'

export function listCameraSlots() {
  return request.get('/cameras/slots', { silent: true })
}

export function updateCameraSlot(slotId, payload) {
  return request.put(`/cameras/slots/${slotId}`, payload)
}

export function updateCameraWeatherSimulation(slotId, enabled) {
  return request.patch(`/cameras/slots/${slotId}/weather-simulation`, { enabled })
}

export function uploadCameraMedia(slotId, file) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post(`/cameras/slots/${slotId}/media`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 220000
  })
}

export async function getCameraFrameBlob(slotId, { taskType = null, signal } = {}) {
  const framePath = taskType
    ? `/jpeg/api/v1/jpeg/processed/${encodeURIComponent(taskType)}/${slotId}.jpg`
    : `/jpeg/api/v1/jpeg/frame/${slotId}.jpg`
  const response = await fetch(`${framePath}?t=${Date.now()}`, {
    cache: 'no-store',
    credentials: 'same-origin',
    signal
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detail || `JPEG 取帧失败 (${response.status})`)
  }
  return response.blob()
}

export function getCameraData(response) {
  return response?.data || response
}
