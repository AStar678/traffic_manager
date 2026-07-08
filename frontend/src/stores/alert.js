import { defineStore } from 'pinia'
import { mockAlerts, mockAlertStats } from '@/utils/mockData'

export const useAlertStore = defineStore('alert', {
  state: () => ({
    alerts: [],
    unreadCount: 0,
    stats: {},
    connected: false
  }),
  actions: {
    connectWebSocket() {
      this.connected = true
      if (!this.alerts.length) {
        this.alerts = [...mockAlerts]
        this.unreadCount = mockAlerts.filter(item => item.status !== 'resolved').length
      }
    },
    fetchAlerts() {
      this.alerts = [...mockAlerts]
      this.stats = { ...mockAlertStats }
      this.unreadCount = this.alerts.filter(item => item.status !== 'resolved').length
    }
  }
})
