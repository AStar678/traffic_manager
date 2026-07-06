import { defineStore } from 'pinia'

export const useAlertStore = defineStore('alert', {
  state: () => ({
    alerts: [],
    unreadCount: 0,
    stats: {}
  }),
  actions: {
    connectWebSocket() {
      // TODO: WebSocket连接
    },
    fetchAlerts() {
      // TODO: 获取告警列表
    }
  }
})
