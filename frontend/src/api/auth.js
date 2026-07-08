import request from './request'

/** 账号密码登录 */
export function login(username, password) {
  return request.post('/auth/login', { username, password })
}

/** 用户注册 */
export function register(data) {
  return request.post('/auth/register', data)
}

/** 发送短信验证码 */
export function sendCode(phone) {
  return request.post('/auth/send-code', { phone })
}

/** 验证码登录 */
export function loginByCode(phone, code) {
  return request.post('/auth/login/code', { phone, code })
}
