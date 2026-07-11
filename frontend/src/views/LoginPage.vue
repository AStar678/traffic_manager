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

    <!-- 右侧：登录面板 -->
    <div class="login-panel">
      <div class="login-card">
        <h2>欢迎回来</h2>
        <p class="hint">登录您的 VisionDrive 账号</p>

        <!-- Tab 切换：验证码登录 / 密码登录 -->
        <div class="login-tabs">
          <button
            :class="['tab-btn', { active: loginMode === 'code' }]"
            @click="switchMode('code')"
          >
            验证码登录
          </button>
          <button
            :class="['tab-btn', { active: loginMode === 'password' }]"
            @click="switchMode('password')"
          >
            密码登录
          </button>
          <div class="tab-indicator" :class="loginMode"></div>
        </div>

        <!-- ====== 验证码登录表单 ====== -->
        <div v-show="loginMode === 'code'" class="form-body">
          <!-- 手机号 -->
          <div class="form-group">
            <label>手机号</label>
            <div :class="['input-wrapper', { 'has-error': form.phone && !phoneOk }]">
              <el-icon><Phone /></el-icon>
              <input
                v-model="form.phone"
                type="tel"
                maxlength="11"
                placeholder="请输入手机号"
                class="auto-input"
              />
            </div>
            <p v-if="form.phone && !phoneOk" class="field-error">请输入正确的11位手机号</p>
          </div>

          <!-- 验证码 -->
          <div class="form-group">
            <label>验证码</label>
            <div class="code-row">
              <div :class="['input-wrapper code-input-wrap', { 'has-error': form.code && codeIncomplete }]">
                <el-icon><Message /></el-icon>
                <input
                  v-model="form.code"
                  type="text"
                  maxlength="6"
                  placeholder="6位验证码"
                  class="auto-input"
                  @keyup.enter="handleCodeLogin"
                />
              </div>
              <button
                class="send-code-btn"
                :disabled="!phoneOk || countdown > 0 || sending"
                @click="sendCode"
              >
                <template v-if="sending">
                  <el-icon class="is-loading"><Loading /></el-icon> 发送中
                </template>
                <template v-else-if="countdown > 0">
                  {{ countdown }}s 后重发
                </template>
                <template v-else>
                  获取验证码
                </template>
              </button>
            </div>
            <p v-if="form.code && codeIncomplete" class="field-error">验证码为6位数字</p>
          </div>

          <!-- 登录按钮 -->
          <button
            class="login-btn"
            :disabled="!canCodeLogin || loggingIn"
            @click="handleCodeLogin"
          >
            <template v-if="loggingIn">
              <el-icon class="is-loading"><Loading /></el-icon> 登录中...
            </template>
            <template v-else>
              登 录
            </template>
          </button>
        </div>

        <!-- ====== 密码登录表单 ====== -->
        <div v-show="loginMode === 'password'" class="form-body">
          <!-- 手机号 / 用户名 -->
          <div class="form-group">
            <label>手机号</label>
            <div class="input-wrapper">
              <el-icon><Phone /></el-icon>
              <input
                v-model="form.phone"
                type="tel"
                maxlength="11"
                placeholder="请输入手机号"
                class="auto-input"
              />
            </div>
            <p v-if="form.phone && !phoneOk" class="field-error">请输入正确的11位手机号</p>
          </div>

          <!-- 密码 -->
          <div class="form-group">
            <label>密码</label>
            <div class="input-wrapper">
              <el-icon><Lock /></el-icon>
              <input
                v-model="form.password"
                :type="showPwd ? 'text' : 'password'"
                placeholder="请输入密码"
                class="auto-input"
                @keyup.enter="handlePwdLogin"
              />
              <button type="button" class="pwd-toggle" @click="showPwd = !showPwd">
                <el-icon><Hide v-if="showPwd" /><View v-else /></el-icon>
              </button>
            </div>
          </div>

          <!-- 忘记密码 -->
          <div class="forgot-link">
            <span class="link-text" @click="$router.push('/forgot-password')">忘记密码？</span>
          </div>

          <!-- 登录按钮 -->
          <button
            class="login-btn"
            :disabled="!canPwdLogin || loggingIn"
            @click="handlePwdLogin"
          >
            <template v-if="loggingIn">
              <el-icon class="is-loading"><Loading /></el-icon> 登录中...
            </template>
            <template v-else>
              登 录
            </template>
          </button>
        </div>

        <!-- 底部链接 -->
        <div class="bottom-link">
          还没有账号？<span class="link-text" @click="$router.push('/register')">立即注册 →</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, computed, watch, onBeforeUnmount } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { sendCode as apiSendCode } from '@/api/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

// ---- 状态 ----
const loginMode = ref('code')           // 'code' | 'password'
const showPwd = ref(false)
const countdown = ref(0)
const sending = ref(false)
const loggingIn = ref(false)
let timer = null

const form = reactive({
  phone: '',
  code: '',
  password: ''
})

// ---- 计算校验 ----
const phoneOk = computed(() => /^1[3-9]\d{9}$/.test(form.phone))
const codeIncomplete = computed(() => form.code.length > 0 && form.code.length !== 6)
const canCodeLogin = computed(() => phoneOk.value && form.code.length === 6)
const canPwdLogin = computed(() => phoneOk.value && form.password.length > 0)

// ---- 切换模式 ----
function switchMode(mode) {
  loginMode.value = mode
  // 切换时清空对应字段，避免混淆
  if (mode === 'password') {
    form.code = ''
  } else {
    form.password = ''
  }
}

// ---- 发送验证码 ----
async function sendCode() {
  if (!phoneOk.value) {
    ElMessage.warning('请先输入正确的手机号')
    return
  }
  if (sending.value) return

  sending.value = true
  try {
    const res = await apiSendCode(form.phone)
    const data = res.data || res
    if (data?.mockCode) {
      ElMessage.success(`验证码：${data.mockCode}`)
    } else {
      const masked = form.phone.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2')
      ElMessage.success(`验证码已发送至 ${masked}`)
    }
    startCountdown(data?.retryAfter || 60)
  } catch (e) {
    const retryAfter = e?.response?.data?.data?.retryAfter
    if (retryAfter) startCountdown(retryAfter)
    const msg = e?.response?.data?.message || e?.message || '发送失败'
    ElMessage.error(msg.includes('status code 500') ? '验证码发送失败，请检查后端服务' : msg)
  } finally {
    sending.value = false
  }
}

function startCountdown(seconds = 60) {
  countdown.value = seconds
  clearInterval(timer)
  timer = setInterval(() => {
    countdown.value -= 1
    if (countdown.value <= 0) {
      clearInterval(timer)
      timer = null
    }
  }, 1000)
}

// ---- 验证码登录 ----
async function handleCodeLogin() {
  if (!canCodeLogin.value || loggingIn.value) return
  loggingIn.value = true
  try {
    await authStore.loginByCode(form.phone, form.code)
    ElMessage.success('欢迎使用 VisionDrive')
    router.push(route.query.redirect || '/dashboard')
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e?.message || '登录失败')
  } finally {
    loggingIn.value = false
  }
}

// ---- 密码登录 ----
async function handlePwdLogin() {
  if (!canPwdLogin.value || loggingIn.value) return
  loggingIn.value = true
  try {
    await authStore.login(form.phone, form.password)
    ElMessage.success('欢迎使用 VisionDrive')
    router.push(route.query.redirect || '/dashboard')
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e?.message || '登录失败')
  } finally {
    loggingIn.value = false
  }
}

onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
/* ---- 整体布局 ---- */
.login-screen {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 480px;
  height: 100vh;
  height: 100dvh;
  background: var(--bg-root);
}

/* ---- 左侧品牌区 ---- */
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

/* ---- 右侧登录面板 ---- */
.login-panel {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px;
  background: var(--bg-surface);
  border-left: 1px solid var(--border-subtle);
}
.login-card {
  width: 100%;
  max-width: 380px;
}
.login-card h2 {
  font-size: 28px;
  font-weight: 800;
  color: var(--text-primary);
  letter-spacing: -0.5px;
}
.hint {
  margin-top: 6px;
  font-size: 14px;
  color: var(--text-muted);
}

/* ---- Tab 切换 ---- */
.login-tabs {
  position: relative;
  display: flex;
  margin-top: 28px;
  background: var(--bg-card);
  border-radius: 12px;
  padding: 4px;
}
.tab-btn {
  flex: 1;
  height: 40px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  border-radius: 10px;
  position: relative;
  z-index: 1;
  transition: color var(--duration-fast);
}
.tab-btn.active {
  color: var(--text-primary);
}
.tab-indicator {
  position: absolute;
  top: 4px;
  height: 40px;
  width: calc(50% - 4px);
  background: var(--bg-surface);
  border-radius: 10px;
  border: 1px solid var(--border-card);
  transition: transform 280ms cubic-bezier(0.4, 0, 0.2, 1);
  pointer-events: none;
}
.tab-indicator.code {
  transform: translateX(0);
}
.tab-indicator.password {
  transform: translateX(100%);
}

/* ---- 表单体 ---- */
.form-body {
  margin-top: 24px;
}

/* ---- 表单组 ---- */
.form-group {
  margin-top: 18px;
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

/* ---- 输入框 ---- */
.input-wrapper {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 14px;
  background: var(--bg-card);
  border: 1px solid var(--border-card);
  border-radius: 12px;
  transition: border-color var(--duration-fast), box-shadow var(--duration-fast);
}
.input-wrapper:focus-within {
  border-color: var(--border-active);
  box-shadow: 0 0 12px var(--primary-glow);
}
.input-wrapper.has-error {
  border-color: var(--danger-color);
  box-shadow: 0 0 8px rgba(255, 61, 0, 0.15);
}
.input-wrapper .el-icon:not(.pwd-toggle .el-icon) {
  color: var(--text-muted);
  font-size: 18px;
  flex-shrink: 0;
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
.field-error {
  margin-top: 6px;
  font-size: 12px;
  color: var(--danger-color);
  line-height: 1;
}

/* ---- 密码显示/隐藏按钮 ---- */
.pwd-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  border-radius: 8px;
  transition: color var(--duration-fast);
  flex-shrink: 0;
}
.pwd-toggle:hover {
  color: var(--text-secondary);
}

/* ---- 验证码行 ---- */
.code-row {
  display: flex;
  gap: 10px;
}
.code-input-wrap {
  flex: 1;
}

/* ---- 发送验证码按钮 ---- */
.send-code-btn {
  min-width: 116px;
  height: 48px;
  padding: 0 12px;
  border: 1px solid var(--primary-color);
  border-radius: 12px;
  background: transparent;
  color: var(--primary-color);
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: all var(--duration-fast);
  white-space: nowrap;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}
.send-code-btn:hover:not(:disabled) {
  background: var(--primary-soft);
}
.send-code-btn:disabled {
  border-color: var(--border-card);
  color: var(--text-muted);
  cursor: not-allowed;
}

/* ---- 主登录按钮 ---- */
.login-btn {
  width: 100%;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 28px;
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
.login-btn:hover:not(:disabled) {
  box-shadow: 0 6px 30px rgba(0, 180, 216, 0.35);
  transform: translateY(-1px);
}
.login-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  box-shadow: none;
}

/* ---- 忘记密码 ---- */
.forgot-link {
  text-align: right;
  margin-top: 12px;
}
.forgot-link .link-text {
  font-size: 13px;
}

/* ---- 底部链接 ---- */
.bottom-link {
  margin-top: 22px;
  text-align: center;
  font-size: 13px;
  color: var(--text-muted);
}
.link-text {
  color: var(--primary-color);
  font-weight: 600;
  cursor: pointer;
  transition: color var(--duration-fast);
}
.link-text:hover {
  color: #00e5ff;
}

/* ---- 响应式 ---- */
@media (max-width: 860px) {
  .login-screen {
    grid-template-columns: 1fr;
  }
  .login-hero { display: none; }
}
</style>
