import request from './request'

export function listOwnerGestures() {
  return request.get('/owner-gestures')
}

export function enrollOwnerGesture(payload) {
  return request.post('/owner-gestures/enroll', payload)
}

export function updateOwnerGesture(gestureCode, payload) {
  return request.put(`/owner-gestures/${gestureCode}`, payload)
}

export function deleteOwnerGesture(gestureCode) {
  return request.delete(`/owner-gestures/${gestureCode}`)
}

export function getOwnerGestureControlSettings() {
  return request.get('/owner-gestures/control-settings')
}

export function saveOwnerGestureControlSettings(payload) {
  return request.post('/owner-gestures/control-settings', payload)
}

export function executeOwnerGestureControl(payload) {
  return request.post('/owner-gestures/control/execute', payload)
}

export function recognizeOwnerGesture(payload) {
  return request.post('/owner-gestures/recognize', payload)
}

export function getOwnerGestureData(response) {
  return response?.data || response
}
