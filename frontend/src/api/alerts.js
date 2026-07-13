import request from './request'

export function getAlerts(params) {
  return request.get('/alerts', { params })
}

export function getAlertDetail(id) {
  return request.get(`/alerts/${id}`)
}

export function updateAlertStatus(id, status) {
  return request.put(`/alerts/${id}/status`, { status })
}

export function getAlertStats() {
  return request.get('/alerts/stats')
}

export function getSystemLogs(params) {
  return request.get('/alerts/system-logs', { params })
}

export function runAlertAgent() {
  return request.post('/alerts/agent/run')
}

export function injectDatabaseFailureAlert() {
  return request.post('/alerts/manual/database-failure')
}
