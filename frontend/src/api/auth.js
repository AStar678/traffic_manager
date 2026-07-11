import request from './request'

export function login(username, password) {
  return request.post('/auth/login', { username, password }, { showError: false })
}

export function register(data) {
  return request.post('/auth/register', data, { showError: false })
}

export function sendCode(phone) {
  return request.post('/auth/send-code', { phone }, { showError: false })
}

export function loginByCode(phone, code) {
  return request.post('/auth/login/code', { phone, code }, { showError: false })
}

export function resetPassword(data) {
  return request.post('/auth/reset-password', data, { showError: false })
}

export function checkPhone(phone) {
  return request.get('/auth/check-phone', { params: { phone }, showError: false })
}
