import { defineStore } from 'pinia'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    refreshToken: localStorage.getItem('refreshToken') || '',
    user: JSON.parse(localStorage.getItem('user') || 'null')
  }),
  getters: {
    isAuthenticated: state => Boolean(state.token),
    isAdmin: state => state.user?.role === 'ADMIN'
  },
  actions: {
    login(username, password) {
      const user = {
        id: 1,
        username: username || 'demo_admin',
        nickname: '演示管理员',
        role: 'ADMIN',
        email: 'admin@visiondrive.local'
      }

      this.token = `mock_access_${Date.now()}`
      this.refreshToken = `mock_refresh_${Date.now()}`
      this.user = user

      localStorage.setItem('token', this.token)
      localStorage.setItem('refreshToken', this.refreshToken)
      localStorage.setItem('user', JSON.stringify(user))

      return Promise.resolve({ token: this.token, user })
    },
    logout() {
      this.token = ''
      this.refreshToken = ''
      this.user = null
      localStorage.removeItem('token')
      localStorage.removeItem('refreshToken')
      localStorage.removeItem('user')
    }
  }
})
