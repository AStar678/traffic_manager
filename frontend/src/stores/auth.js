import { defineStore } from 'pinia'
import { getCurrentUser, login as apiLogin, loginByCode as apiLoginByCode, register as apiRegister } from '@/api/auth'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    refreshToken: localStorage.getItem('refreshToken') || '',
    user: JSON.parse(localStorage.getItem('user') || 'null'),
    sessionChecked: false
  }),
  getters: {
    isAuthenticated: state => Boolean(state.token),
    isAdmin: state => state.user?.role === 'ADMIN'
  },
  actions: {
    async login(username, password) {
      const response = await apiLogin(username, password)
      const data = response.data || response
      this.saveAuth(data)
      return data
    },
    async loginByCode(phone, code) {
      const response = await apiLoginByCode(phone, code)
      const data = response.data || response
      this.saveAuth(data)
      return data
    },
    async registerAccount(form) {
      const response = await apiRegister(form)
      const data = response.data || response
      this.saveAuth(data)
      return data
    },
    logout() {
      this.token = ''
      this.refreshToken = ''
      this.user = null
      localStorage.removeItem('token')
      localStorage.removeItem('refreshToken')
      localStorage.removeItem('user')
      this.sessionChecked = true
    },
    async validateSession() {
      if (this.sessionChecked) return this.isAuthenticated
      if (!this.token) {
        this.sessionChecked = true
        return false
      }
      try {
        const response = await getCurrentUser()
        const data = response.data || response
        this.user = {
          id: data.userId,
          username: data.username,
          nickname: data.nickname || data.username,
          phone: data.phone,
          email: data.email,
          role: data.role || 'USER'
        }
        localStorage.setItem('user', JSON.stringify(this.user))
        this.sessionChecked = true
        return true
      } catch (error) {
        this.logout()
        return false
      }
    },
    saveAuth(data) {
      if (!data?.token) {
        throw new Error('登录响应缺少 Token')
      }
      this.token = data.token
      this.refreshToken = data.refreshToken || ''
      this.user = data.user || {
        id: data.userId,
        username: data.username,
        nickname: data.nickname || data.username,
        phone: data.phone,
        email: data.email,
        role: data.role || 'USER'
      }
      localStorage.setItem('token', this.token)
      if (this.refreshToken) localStorage.setItem('refreshToken', this.refreshToken)
      else localStorage.removeItem('refreshToken')
      localStorage.setItem('user', JSON.stringify(this.user))
      this.sessionChecked = true
    }
  }
})
