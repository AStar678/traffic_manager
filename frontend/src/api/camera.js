import request from './request'

export function listCameraSlots() {
  return request.get('/cameras/slots')
}

export function updateCameraSlot(slotId, payload) {
  return request.put(`/cameras/slots/${slotId}`, payload)
}

export function uploadCameraMedia(slotId, file) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post(`/cameras/slots/${slotId}/media`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 220000
  })
}

export function getCameraFrameBlob(slotId) {
  return request.get(`/cameras/slots/${slotId}/frame.jpg`, {
    params: { t: Date.now() },
    responseType: 'blob',
    timeout: 12000
  })
}

export function getCameraData(response) {
  return response?.data || response
}
