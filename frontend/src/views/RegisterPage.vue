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

    <!-- 右侧：注册面板 -->
    <div class="login-panel">
      <div class="login-card">
        <h2>创建账号</h2>
        <p class="hint">手机号即账号，验证后设置密码</p>

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
          <p v-if="phoneRegistered" class="field-warning">⚠ 该手机号已注册，可直接使用验证码登录</p>
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

        <!-- 设置密码 -->
        <div class="form-group">
          <label>设置密码</label>
          <div :class="['input-wrapper', { 'has-error': form.password && !pwdOk }]">
            <el-icon><Lock /></el-icon>
            <input
              v-model="form.password"
              :type="showPwd ? 'text' : 'password'"
              placeholder="至少6位，含字母和数字"
              class="auto-input"
            />
            <button type="button" class="pwd-toggle" @click="showPwd = !showPwd">
              <el-icon><Hide v-if="showPwd" /><View v-else /></el-icon>
            </button>
          </div>
          <p v-if="form.password && !pwdOk" class="field-error">至少6位，需包含字母和数字</p>
        </div>

        <!-- 确认密码 -->
        <div class="form-group">
          <label>确认密码</label>
          <div :class="['input-wrapper', { 'has-error': form.confirmPwd && !matchOk }]">
            <el-icon><Lock /></el-icon>
            <input
              v-model="form.confirmPwd"
              :type="showCfm ? 'text' : 'password'"
              placeholder="再次输入密码"
              class="auto-input"
              @keyup.enter="handleRegister"
            />
            <button type="button" class="pwd-toggle" @click="showCfm = !showCfm">
              <el-icon><Hide v-if="showCfm" /><View v-else /></el-icon>
            </button>
          </div>
          <p v-if="form.confirmPwd && !matchOk" class="field-error">两次密码不一致</p>
        </div>

        <!-- 注册按钮 -->
        <button
          class="login-btn"
          :disabled="!canRegister || submitting"
          @click="handleRegister"
        >
          <template v-if="submitting">
            <el-icon class="is-loading"><Loading /></el-icon> 注册中...
          </template>
          <template v-else>
            注 册
          </template>
        </button>

        <!-- 底部链接 -->
        <div class="bottom-link">
          已有账号？<span class="link-text" @click="$router.push('/login')">去登录 →</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, computed, watch, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { sendCode as apiSendCode, register as apiRegister, checkPhone as apiCheckPhone } from '@/api/auth'

const router = useRouter()

// ---- 状态 ----
const showPwd = ref(false)
const showCfm = ref(false)
const countdown = ref(0)
const sending = ref(false)
const submitting = ref(false)
const phoneRegistered = ref(false)
let timer = null
let checkTimer = null

// 手机号变化时延迟检测是否已注册
watch(() => form.phone, (val) => {
  phoneRegistered.value = false
  clearTimeout(checkTimer)
  if (/^1[3-9]\d{9}$/.test(val)) {
    checkTimer = setTimeout(async () => {
      try {
        const res = await apiCheckPhone(val)
        phoneRegistered.value = res?.data?.registered || false
      } catch { /* 静默失败 */ }
    }, 600)
  }
})

const form = reactive({
  phone: '',
  code: '',
  password: '',
  confirmPwd: ''
})

// ---- 计算校验 ----
const phoneOk = computed(() => /^1[3-9]\d{9}$/.test(form.phone))
const codeIncomplete = computed(() => form.code.length > 0 && form.code.length !== 6)
const pwdOk = computed(() =>
  form.password.length >= 6 &&
  /[a-zA-Z]/.test(form.password) &&
  /\d/.test(form.password)
)
const matchOk = computed(() => form.password && form.password === form.confirmPwd)
const canRegister = computed(() =>
  phoneOk.value && form.code.length === 6 && pwdOk.value && matchOk.value
)

// ---- 发送验证码 ----
async function sendCode() {
  if (!phoneOk.value) {
    ElMessage.warning('请先输入正确的手机号')
    return
  }
  sending.value = true
  try {
    const res = await apiSendCode(form.phone)
    const data = res.data || res
    if (data?.alreadyRegistered) {
      phoneRegistered.value = true
      ElMessage.warning('该手机号已注册，可直接去登录页使用验证码登录')
    }
    if (data?.mockCode) {
      ElMessage.success(`验证码：${data.mockCode}`)
    } else {
      const masked = form.phone.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2')
      ElMessage.success(`验证码已发送至 ${masked}`)
    }
    startCountdown(data?.retryAfter || 30)
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

// ---- 注册 ----
async function handleRegister() {
  if (!canRegister.value) return
  submitting.value = true
  try {
    await apiRegister({
      phone: form.phone,
      smsCode: form.code,
      password: form.password,
      username: form.phone   // 账号默认为手机号
    })
    ElMessage.success('注册成功，请登录')
    router.push('/login')
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e?.message || '注册失败')
  } finally {
    submitting.value = false
  }
}

onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
  if (checkTimer) clearTimeout(checkTimer)
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

/* ---- 右侧面板 ---- */
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
.field-warning {
  margin-top: 6px;
  font-size: 12px;
  color: var(--warning-color);
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

/* ---- 注册按钮 ---- */
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
