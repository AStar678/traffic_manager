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
    const payload = response.data
    if (
      payload &&
      typeof payload === 'object' &&
      Object.prototype.hasOwnProperty.call(payload, 'code') &&
      payload.code !== 0
    ) {
      const error = new Error(payload.message || '请求失败')
      error.response = { ...response, data: payload }
      if (response.config.showError !== false) {
        ElMessage.error(error.message)
      }
      return Promise.reject(error)
    }
    return payload
  },
  error => {
    error.message = error.response?.data?.message || error.message || '请求失败'
    if (error.config?.showError !== false) {
      ElMessage.error(error.message)
    }
    return Promise.reject(error)
  }
)

export default request
