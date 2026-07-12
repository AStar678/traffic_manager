import request from './request'

export function login(username, password) {
  return request.post('/auth/login', { username, password })
}

export function register(data) {
  return request.post('/auth/register', data)
}

export function sendCode(phone, purpose) {
  return request.post('/auth/send-code', { phone, purpose })
}

export function loginByCode(phone, code) {
  return request.post('/auth/login/code', { phone, code })
}

export function getCurrentUser() {
  return request.get('/auth/me')
}
