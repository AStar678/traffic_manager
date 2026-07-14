import request from './request'
import { postEncryptedAuth } from './authEncryption'

export function login(username, password) {
  return postEncryptedAuth('/auth/login', { username, password })
}

export function register(data) {
  return postEncryptedAuth('/auth/register', data)
}

export function sendCode(phone, purpose) {
  return postEncryptedAuth('/auth/send-code', { phone, purpose })
}

export function loginByCode(phone, code) {
  return postEncryptedAuth('/auth/login/code', { phone, code })
}

export function getCurrentUser() {
  return request.get('/auth/me')
}
