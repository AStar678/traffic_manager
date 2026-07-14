<template>
  <div class="login-screen">
    <!-- 左侧：品牌视觉 -->
    <div class="login-hero">
      <div class="hero-bg"></div>
      <div class="hero-content">
        <div class="brand-mark-lg">VD</div>
        <h1>VisionDrive</h1>
        <p class="subtitle">智视驾 · 车载视觉感知与交互系统</p>
        <div class="hero-features">
          <span>车牌识别</span>
          <span>交警手势</span>
          <span>手势控车</span>
          <span>AI告警</span>
        </div>
      </div>
    </div>

    <!-- 右侧：登录 -->
    <div class="login-panel">
      <div class="login-card">
        <h2>{{ modeTitle }}</h2>
        <p class="hint">{{ modeHint }}</p>
        <p class="security-note">
          <el-icon><Lock /></el-icon>
          认证信息使用 RSA-OAEP + AES-256-GCM 加密传输
        </p>

        <div class="mode-tabs" role="tablist" aria-label="认证方式">
          <button
            v-for="item in modeOptions"
            :key="item.value"
            type="button"
            role="tab"
            :aria-selected="authMode === item.value"
            :class="{ active: authMode === item.value }"
            @click="authMode = item.value"
          >
            {{ item.label }}
          </button>
        </div>

        <template v-if="authMode === 'password'">
          <div class="form-group">
            <label for="login-username">用户名</label>
            <div class="input-wrapper">
              <el-icon><User /></el-icon>
              <input
                id="login-username"
                v-model.trim="loginForm.username"
                type="text"
                autocomplete="username"
                placeholder="请输入用户名"
                class="auto-input"
              />
            </div>
          </div>

          <div class="form-group">
            <label for="login-password">密码</label>
            <div class="input-wrapper">
              <el-icon><Lock /></el-icon>
              <input
                id="login-password"
                v-model="loginForm.password"
                type="password"
                autocomplete="current-password"
                placeholder="请输入密码"
                class="auto-input"
                @keyup.enter="handleSubmit"
              />
            </div>
          </div>
        </template>

        <div v-else-if="authMode === 'code'" class="code-section">
          <div class="form-group">
            <label for="login-phone">手机号</label>
            <div class="input-wrapper">
              <el-icon><Message /></el-icon>
              <input
                id="login-phone"
                v-model.trim="loginForm.phone"
                type="tel"
                inputmode="numeric"
                autocomplete="tel"
                maxlength="11"
                placeholder="请输入11位手机号"
                class="auto-input"
              />
            </div>
          </div>
          <div class="form-group">
            <label for="login-code">短信验证码</label>
            <div class="code-row">
              <div class="input-wrapper code-input-wrapper">
                <input
                  id="login-code"
                  v-model.trim="loginForm.code"
                  type="text"
                  inputmode="numeric"
                  autocomplete="one-time-code"
                  maxlength="6"
                  placeholder="请输入6位验证码"
                  class="auto-input"
                  @keyup.enter="handleSubmit"
                />
              </div>
              <button
                type="button"
                class="send-code-btn"
                :disabled="countdowns.LOGIN > 0 || sending.LOGIN"
                @click="sendCode('LOGIN')"
              >
                {{ codeButtonText('LOGIN') }}
              </button>
            </div>
          </div>
        </div>

        <div v-else class="register-form">
          <div class="form-group">
            <label for="register-username">用户名</label>
            <div class="input-wrapper">
              <el-icon><User /></el-icon>
              <input
                id="register-username"
                v-model.trim="registerForm.username"
                type="text"
                autocomplete="username"
                maxlength="32"
                placeholder="3-32位字母、数字或下划线"
                class="auto-input"
              />
            </div>
          </div>

          <div class="form-group">
            <label for="register-email">邮箱</label>
            <div class="input-wrapper">
              <el-icon><Message /></el-icon>
              <input
                id="register-email"
                v-model.trim="registerForm.email"
                type="email"
                autocomplete="email"
                maxlength="254"
                placeholder="用于账号联系与找回"
                class="auto-input"
              />
            </div>
          </div>

          <div class="form-group">
            <label for="register-password">密码</label>
            <div class="input-wrapper">
              <el-icon><Lock /></el-icon>
              <input
                id="register-password"
                v-model="registerForm.password"
                type="password"
                autocomplete="new-password"
                maxlength="72"
                placeholder="至少8位"
                class="auto-input"
              />
            </div>
          </div>

          <div class="form-group">
            <label for="register-confirm-password">确认密码</label>
            <div class="input-wrapper">
              <el-icon><Lock /></el-icon>
              <input
                id="register-confirm-password"
                v-model="registerForm.confirmPassword"
                type="password"
                autocomplete="new-password"
                maxlength="72"
                placeholder="再次输入密码"
                class="auto-input"
              />
            </div>
          </div>

          <div class="form-group">
            <label for="register-phone">绑定手机号</label>
            <div class="input-wrapper">
              <el-icon><Message /></el-icon>
              <input
                id="register-phone"
                v-model.trim="registerForm.phone"
                type="tel"
                inputmode="numeric"
                autocomplete="tel"
                maxlength="11"
                placeholder="请输入11位手机号"
                class="auto-input"
              />
            </div>
          </div>

          <div class="form-group">
            <label for="register-code">注册验证码</label>
            <div class="code-row">
              <div class="input-wrapper code-input-wrapper">
                <input
                  id="register-code"
                  v-model.trim="registerForm.code"
                  type="text"
                  inputmode="numeric"
                  autocomplete="one-time-code"
                  maxlength="6"
                  placeholder="请输入6位验证码"
                  class="auto-input"
                  @keyup.enter="handleSubmit"
                />
              </div>
              <button
                type="button"
                class="send-code-btn"
                :disabled="countdowns.REGISTER > 0 || sending.REGISTER"
                @click="sendCode('REGISTER')"
              >
                {{ codeButtonText('REGISTER') }}
              </button>
            </div>
          </div>
        </div>

        <button type="button" class="login-btn" :disabled="loading" @click="handleSubmit">
          {{ loading ? loadingText : submitText }}
          <el-icon v-if="!loading"><ArrowRight /></el-icon>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref, onBeforeUnmount } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { sendCode as apiSendCode } from '@/api/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const loginForm = reactive({
  username: '',
  password: '',
  phone: '',
  code: ''
})
const registerForm = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
  phone: '',
  code: ''
})
const authMode = ref('password')
const modeOptions = [
  { value: 'password', label: '账号登录' },
  { value: 'code', label: '验证码登录' },
  { value: 'register', label: '注册' }
]
const countdowns = reactive({ LOGIN: 0, REGISTER: 0 })
const sending = reactive({ LOGIN: false, REGISTER: false })
const loading = ref(false)
const timers = { LOGIN: null, REGISTER: null }

const modeTitle = computed(() => authMode.value === 'register' ? '创建账号' : '登录系统')
const modeHint = computed(() => ({
  password: '使用账号密码登录',
  code: '仅限已注册并绑定手机号的用户',
  register: '短信验证手机号后创建账号'
}[authMode.value]))
const submitText = computed(() => ({
  password: '进入系统',
  code: '验证码登录',
  register: '验证并注册'
}[authMode.value]))
const loadingText = computed(() => authMode.value === 'register' ? '注册中...' : '登录中...')

async function sendCode(purpose) {
  const phone = purpose === 'REGISTER' ? registerForm.phone : loginForm.phone
  if (!isPhone(phone)) {
    ElMessage.warning('请输入正确的11位手机号')
    return
  }
  sending[purpose] = true
  try {
    const response = await apiSendCode(phone, purpose)
    const data = response.data || {}
    startCountdown(purpose, data.retryAfter || 60)
    ElMessage.success(data.mockCode ? `开发验证码：${data.mockCode}` : '验证码已发送，请查收短信')
  } catch (error) {
    const body = error.response?.data
    if (body?.data?.retryAfter) startCountdown(purpose, body.data.retryAfter)
    if (!error.__visionDriveNotified) ElMessage.error(body?.message || error.message || '验证码发送失败')
  } finally {
    sending[purpose] = false
  }
}

function startCountdown(purpose, seconds) {
  countdowns[purpose] = Number(seconds) || 60
  clearInterval(timers[purpose])
  timers[purpose] = setInterval(() => {
    countdowns[purpose] -= 1
    if (countdowns[purpose] <= 0) clearInterval(timers[purpose])
  }, 1000)
}

function codeButtonText(purpose) {
  if (sending[purpose]) return '发送中'
  return countdowns[purpose] > 0 ? `${countdowns[purpose]}s` : '获取验证码'
}

async function handleSubmit() {
  if (!validateCurrentForm()) return

  loading.value = true
  try {
    if (authMode.value === 'code') {
      await authStore.loginByCode(loginForm.phone, loginForm.code)
    } else if (authMode.value === 'register') {
      await authStore.registerAccount({
        username: registerForm.username,
        email: registerForm.email,
        password: registerForm.password,
        phone: registerForm.phone,
        code: registerForm.code
      })
    } else {
      await authStore.login(loginForm.username, loginForm.password)
    }
    ElMessage.success(authMode.value === 'register' ? '注册成功，已自动登录' : '登录成功')
    await router.push(route.query.redirect || '/dashboard')
  } catch (error) {
    if (!error.__visionDriveNotified) {
      ElMessage.error(error.response?.data?.message || error.message || (authMode.value === 'register' ? '注册失败' : '登录失败'))
    }
  } finally {
    loginForm.password = ''
    registerForm.password = ''
    registerForm.confirmPassword = ''
    loading.value = false
  }
}

function validateCurrentForm() {
  if (authMode.value === 'password') {
    if (loginForm.username && loginForm.password) return true
    ElMessage.warning('请输入用户名和密码')
    return
  }
  if (authMode.value === 'code') {
    if (!isPhone(loginForm.phone)) {
      ElMessage.warning('请输入正确的11位手机号')
      return false
    }
    if (!isCode(loginForm.code)) {
      ElMessage.warning('验证码必须为6位数字')
      return false
    }
    return true
  }

  if (!/^[A-Za-z0-9_]{3,32}$/.test(registerForm.username)) {
    ElMessage.warning('用户名必须为3-32位字母、数字或下划线')
    return false
  }
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(registerForm.email)) {
    ElMessage.warning('请输入正确的邮箱地址')
    return false
  }
  if (registerForm.password.length < 8 || registerForm.password.length > 72) {
    ElMessage.warning('密码长度必须为8到72位')
    return false
  }
  if (registerForm.password !== registerForm.confirmPassword) {
    ElMessage.warning('两次输入的密码不一致')
    return false
  }
  if (!isPhone(registerForm.phone)) {
    ElMessage.warning('请输入正确的11位手机号')
    return false
  }
  if (!isCode(registerForm.code)) {
    ElMessage.warning('验证码必须为6位数字')
    return false
  }
  return true
}

function isPhone(phone) { return /^1[3-9]\d{9}$/.test(phone) }
function isCode(code) { return /^\d{6}$/.test(code) }

onBeforeUnmount(() => {
  Object.values(timers).forEach(timer => clearInterval(timer))
})
</script>

<style scoped>
.login-screen {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 480px;
  height: 100vh;
  height: 100dvh;
  background: var(--bg-root);
}

/* 左侧品牌区 */
.login-hero {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.hero-bg {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse at 30% 50%, rgba(0, 180, 216, 0.08) 0%, transparent 60%),
    radial-gradient(ellipse at 70% 30%, rgba(0, 100, 180, 0.06) 0%, transparent 50%),
    var(--bg-root);
}

.hero-bg::after {
  content: '';
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px);
  background-size: 60px 60px;
}

.hero-content {
  position: relative;
  text-align: center;
  z-index: 1;
}

.brand-mark-lg {
  width: 80px;
  height: 80px;
  display: grid;
  place-items: center;
  margin: 0 auto 24px;
  background: linear-gradient(135deg, var(--primary-color), #0096c7);
  border-radius: 20px;
  color: #080c14;
  font-size: 30px;
  font-weight: 900;
  box-shadow: 0 0 40px var(--primary-glow);
}

.login-hero h1 {
  font-size: 42px;
  font-weight: 800;
  color: var(--text-primary);
  letter-spacing: -1px;
}

.subtitle {
  margin-top: 10px;
  font-size: 16px;
  color: var(--text-secondary);
}

.hero-features {
  display: flex;
  gap: 12px;
  justify-content: center;
  margin-top: 28px;
  flex-wrap: wrap;
}

.hero-features span {
  padding: 7px 16px;
  background: rgba(255,255,255,0.05);
  border: 1px solid var(--border-card);
  border-radius: 999px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
}

/* 右侧登录面板 */
.login-panel {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px;
  background: var(--bg-surface);
  border-left: 1px solid var(--border-subtle);
  overflow-y: auto;
}

.login-card {
  width: 100%;
  max-width: 380px;
  margin: auto 0;
  padding: 24px 0;
}

.login-card h2 {
  font-size: 28px;
  font-weight: 800;
  color: var(--text-primary);
  letter-spacing: -0.5px;
}

.security-note {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 8px 0 18px;
  color: var(--status-success);
  font-size: 12px;
  line-height: 1.5;
}

.hint {
  margin-top: 8px;
  font-size: 13px;
  color: var(--text-muted);
}

.mode-tabs {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 4px;
  margin-top: 22px;
  padding: 4px;
  background: var(--bg-card);
  border: 1px solid var(--border-card);
  border-radius: 12px;
}

.mode-tabs button {
  height: 36px;
  padding: 0 8px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: color var(--duration-fast), background var(--duration-fast), box-shadow var(--duration-fast);
}

.mode-tabs button:hover {
  color: var(--text-primary);
}

.mode-tabs button.active {
  background: var(--primary-soft);
  color: var(--primary-color);
  box-shadow: inset 0 0 0 1px var(--border-active);
}

.mode-tabs button:focus-visible {
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
}

.form-group {
  margin-top: 22px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-size: 12px;
  font-weight: 700;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.input-wrapper {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 14px;
  background: var(--bg-card);
  border: 1px solid var(--border-card);
  border-radius: 12px;
  transition: border-color var(--duration-fast);
}

.input-wrapper:focus-within {
  border-color: var(--border-active);
  box-shadow: 0 0 12px var(--primary-glow);
}

.input-wrapper .el-icon {
  color: var(--text-muted);
  font-size: 18px;
}

.auto-input {
  flex: 1;
  height: 46px;
  border: none;
  background: transparent;
  color: var(--text-primary);
  font-size: 15px;
  outline: none;
}

.auto-input::placeholder {
  color: var(--text-muted);
}

.login-btn {
  width: 100%;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 24px;
  border: none;
  border-radius: 12px;
  background: linear-gradient(135deg, var(--primary-color), #0096c7);
  color: #080c14;
  font-size: 16px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 4px 20px var(--primary-glow);
  transition: all var(--duration-fast);
}

.login-btn:hover {
  box-shadow: 0 6px 30px rgba(0, 180, 216, 0.35);
  transform: translateY(-1px);
}

.login-btn:disabled {
  opacity: 0.6;
  cursor: wait;
  transform: none;
}

.code-section {
  margin-top: 4px;
}

.register-form .form-group {
  margin-top: 14px;
}

.code-row {
  display: flex;
  gap: 10px;
}

.code-input-wrapper {
  flex: 1;
  min-width: 0;
}

.send-code-btn {
  min-width: 110px;
  padding: 0 14px;
  border: 1px solid var(--primary-color);
  border-radius: 12px;
  background: transparent;
  color: var(--primary-color);
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: all var(--duration-fast);
  white-space: nowrap;
}

.send-code-btn:hover:not(:disabled) {
  background: var(--primary-soft);
}

.send-code-btn:disabled {
  border-color: var(--border-card);
  color: var(--text-muted);
  cursor: not-allowed;
}

.send-code-btn:focus-visible,
.login-btn:focus-visible {
  outline: 2px solid #00e5ff;
  outline-offset: 3px;
}

@media (max-width: 860px) {
  .login-screen {
    grid-template-columns: 1fr;
  }
  .login-hero { display: none; }
  .login-panel {
    align-items: flex-start;
    padding: 24px;
    border-left: none;
  }
  .login-card {
    max-width: 420px;
    margin: 0 auto;
    padding: 16px 0 32px;
  }
}

@media (max-width: 420px) {
  .login-panel { padding: 18px; }
  .send-code-btn {
    min-width: 102px;
    padding: 0 10px;
  }
}
</style>
