import { defineStore } from 'pinia'
import { mockAlerts, mockAlertStats } from '@/utils/mockData'
import { getAlerts, getAlertStats } from '@/api/alerts'

export const useAlertStore = defineStore('alert', {
  state: () => ({
    alerts: [],
    unreadCount: 0,
    stats: {},
    connected: false,
    socket: null
  }),
  actions: {
    connectWebSocket() {
      if (this.socket && [WebSocket.CONNECTING, WebSocket.OPEN].includes(this.socket.readyState)) {
        return
      }
      const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
      const socket = new WebSocket(`${protocol}//${location.host}/ws/alerts`)
      this.socket = socket

      socket.onopen = () => {
        this.connected = true
      }
      socket.onclose = () => {
        this.connected = false
        this.socket = null
      }
      socket.onerror = () => {
        this.connected = false
      }
      socket.onmessage = event => {
        const payload = JSON.parse(event.data)
        if (payload.type === 'alert') {
          const alert = normalizeAlert(payload)
          this.alerts = [alert, ...this.alerts.filter(item => item.id !== alert.id)]
          this.unreadCount = this.alerts.filter(item => item.status !== 'resolved').length
          this.fetchStats()
        }
      }
    },
    async fetchAlerts() {
      try {
        const [alertResponse, statsResponse] = await Promise.all([
          getAlerts(),
          getAlertStats()
        ])
        this.alerts = (alertResponse.data || []).map(normalizeAlert)
        this.stats = normalizeStats(statsResponse.data || {})
      } catch (error) {
        this.alerts = [...mockAlerts]
        this.stats = { ...mockAlertStats }
      }
      this.unreadCount = this.alerts.filter(item => item.status !== 'resolved').length
    },
    async fetchStats() {
      try {
        const response = await getAlertStats()
        this.stats = normalizeStats(response.data || {})
      } catch (error) {
        this.stats = { ...mockAlertStats }
      }
    },
    disconnectWebSocket() {
      this.socket?.close()
      this.socket = null
      this.connected = false
    }
  }
})

function normalizeAlert(raw) {
  const severity = String(raw.severity || 'info').toUpperCase()
  return {
    ...raw,
    id: raw.id || raw.alertId,
    severity,
    module: raw.module || raw.affectedModule || 'system',
    occurredAt: raw.occurredAt || raw.createdAt || raw.timestamp,
    status: raw.status || (raw.resolved ? 'resolved' : 'open'),
    suggestedActions: normalizeActions(raw.suggestedActions)
  }
}

function normalizeActions(value) {
  if (Array.isArray(value)) {
    return value
  }
  if (typeof value === 'string') {
    return value.split(/\n|；|;/).map(item => item.replace(/^\d+[.、]\s*/, '').trim()).filter(Boolean)
  }
  return []
}

function normalizeStats(raw) {
  return {
    ...raw,
    totalToday: raw.totalToday ?? raw.total ?? 0,
    critical: raw.critical ?? raw.bySeverity?.critical ?? 0,
    warning: raw.warning ?? raw.bySeverity?.warning ?? 0,
    info: raw.info ?? raw.bySeverity?.info ?? 0,
    trend: raw.trend || [],
    severity: raw.severity || [
      { name: '提示', value: raw.bySeverity?.info || 0 },
      { name: '警告', value: raw.bySeverity?.warning || 0 },
      { name: '严重', value: raw.bySeverity?.critical || 0 }
    ]
  }
}
