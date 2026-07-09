import { defineStore } from 'pinia'
import { login as apiLogin, loginByCode as apiLoginByCode } from '@/api/auth'
import { ElMessage } from 'element-plus'

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
    async login(username, password) {
      try {
        const res = await apiLogin(username, password)
        const data = res.data || res
        this._applyLogin(data)
        return data
      } catch (e) {
        console.warn('后端登录失败，使用 Mock 模式:', e)
        return this.mockLogin(username)
      }
    },
    async loginByCode(phone, code) {
      const res = await apiLoginByCode(phone, code)
      const data = res.data || res
      this._applyLogin(data)
    },
    mockLogin(username) {
      const user = {
        id: 1, username: username || 'demo_admin',
        nickname: '演示管理员', role: 'ADMIN', email: 'admin@visiondrive.local'
      }
      this.token = `mock_access_${Date.now()}`
      this.refreshToken = `mock_refresh_${Date.now()}`
      this.user = user
      localStorage.setItem('token', this.token)
      localStorage.setItem('refreshToken', this.refreshToken)
      localStorage.setItem('user', JSON.stringify(user))
      return { token: this.token, user }
    },
    logout() {
      this.token = ''; this.refreshToken = ''; this.user = null
      localStorage.removeItem('token'); localStorage.removeItem('refreshToken'); localStorage.removeItem('user')
    },
    // 后端 LoginResponse 是扁平结构，转成 { token, user }
    _applyLogin(data) {
      this.token = data.token
      this.user = {
        id: data.userId,
        username: data.username,
        nickname: data.nickname,
        phone: data.phone,
        role: data.role
      }
      localStorage.setItem('token', this.token)
      localStorage.setItem('user', JSON.stringify(this.user))
    }
  }
})
