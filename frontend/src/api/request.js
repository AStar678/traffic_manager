import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
  baseURL: '/api/v1',
  timeout: 30000
})

// 请求拦截器 - 添加JWT
request.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器 - 统一错误处理
request.interceptors.response.use(
  response => {
    const body = response.data
    if (body && typeof body.code === 'number' && body.code !== 0) {
      const error = new Error(body.message || '请求失败')
      error.response = { ...response, data: body }
      return Promise.reject(error)
    }
    return body
  },
  error => {
    if (error.response?.status === 401 && !isLoginRequest(error.config?.url)) {
      localStorage.removeItem('token')
      localStorage.removeItem('refreshToken')
      localStorage.removeItem('user')
      if (window.location.pathname !== '/login') {
        const redirect = encodeURIComponent(window.location.pathname + window.location.search)
        window.location.replace(`/login?redirect=${redirect}`)
      }
    }
    ElMessage.error(error.response?.data?.message || '请求失败')
    error.__visionDriveNotified = true
    return Promise.reject(error)
  }
)

function isLoginRequest(url = '') {
  return url === '/auth/login' || url === '/auth/login/code' || url === '/auth/register'
}

export default request
