import { defineStore } from 'pinia'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: '',
    user: null
  }),
  actions: {
    login(username, password) {
      // TODO: 调用登录接口
    },
    logout() {
      // TODO: 清除登录状态
    }
  }
})
