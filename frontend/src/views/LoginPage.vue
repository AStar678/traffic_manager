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
        <h2>登录系统</h2>
        <p class="hint">短信验证码登录 · 首次自动注册</p>

        <div class="form-group">
          <label>用户名</label>
          <div class="input-wrapper">
            <el-icon><User /></el-icon>
            <input
              v-model="form.username"
              type="text"
              placeholder="admin"
              class="auto-input"
            />
          </div>
        </div>

        <div class="form-group">
          <label>密码</label>
          <div class="input-wrapper">
            <el-icon><Lock /></el-icon>
            <input
              v-model="form.password"
              type="password"
              placeholder="任意输入"
              class="auto-input"
              @keyup.enter="handleLogin"
            />
          </div>
        </div>

        <button class="login-btn" :disabled="loading" @click="handleLogin">
          {{ loading ? '登录中...' : '进入系统' }}
          <el-icon v-if="!loading"><ArrowRight /></el-icon>
        </button>

        <div class="toggle-mode" @click="showCodeLogin = !showCodeLogin">
          {{ showCodeLogin ? '账号密码登录' : '验证码登录' }} →
        </div>

        <!-- 验证码登录 -->
        <div v-if="showCodeLogin" class="code-section">
          <div class="form-group">
            <label>手机号 / 邮箱</label>
            <div class="input-wrapper">
              <el-icon><Message /></el-icon>
              <input v-model="form.target" type="text" placeholder="138****8000" class="auto-input" />
            </div>
          </div>
          <div class="code-row">
            <div class="input-wrapper" style="flex:1">
              <input v-model="form.code" type="text" maxlength="6" placeholder="6位验证码" class="auto-input" />
            </div>
            <button class="send-code-btn" :disabled="countdown > 0 || sending" @click="sendCode">
              {{ sending ? '发送中...' : countdown > 0 ? `${countdown}s` : '获取验证码' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, onBeforeUnmount } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { sendCode as apiSendCode } from '@/api/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const form = reactive({
  username: 'admin',
  password: 'visiondrive',
  target: '',
  code: ''
})
const showCodeLogin = ref(false)
const countdown = ref(0)
const sending = ref(false)
const loading = ref(false)
let timer = null

/** 发送短信验证码 */
async function sendCode() {
  if (!form.target) {
    ElMessage.warning('请先输入手机号')
    return
  }
  // 校验手机号格式
  if (!/^1[3-9]\d{9}$/.test(form.target)) {
    ElMessage.warning('请输入正确的手机号')
    return
  }

  sending.value = true
  try {
    const res = await apiSendCode(form.target)
    const data = res.data || res

    if (res.code === 0) {
      ElMessage.success('验证码已发送，请查收短信')
      startCountdown()
    } else if (res.code === 429 && data?.retryAfter) {
      ElMessage.warning(res.message || `请 ${data.retryAfter} 秒后再试`)
      startCountdown(data.retryAfter)
    } else {
      // 后端报错，显示真实错误信息
      ElMessage.error(res.message || '验证码发送失败，请稍后重试')
    }
  } catch {
    ElMessage.error('网络异常，请检查后端服务是否启动')
  } finally {
    sending.value = false
  }
}

function startCountdown(seconds = 60) {
  countdown.value = seconds
  clearInterval(timer)
  timer = setInterval(() => {
    countdown.value -= 1
    if (countdown.value <= 0) clearInterval(timer)
  }, 1000)
}

/** 登录 */
async function handleLogin() {
  loading.value = true
  try {
    if (showCodeLogin.value) {
      // 验证码登录
      if (!form.target || !form.code) {
        ElMessage.warning('请输入手机号和验证码')
        loading.value = false
        return
      }
      if (!/^\d{6}$/.test(form.code)) {
        ElMessage.warning('验证码为6位数字')
        loading.value = false
        return
      }
      await authStore.loginByCode(form.target, form.code)
      ElMessage.success('登录成功')
    } else {
      // 账号密码登录
      await authStore.login(form.username || 'admin', form.password || 'visiondrive')
      ElMessage.success('欢迎使用 VisionDrive')
    }
    router.push(route.query.redirect || '/dashboard')
  } catch (e) {
    const msg = e?.response?.data?.message || e?.message || '登录失败'
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}

onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
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
  background: linear-gradient(135deg, var(--primary-color), #1557b0);
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
}

.login-card {
  width: 100%;
  max-width: 360px;
}

.login-card h2 {
  font-size: 28px;
  font-weight: 800;
  color: var(--text-primary);
  letter-spacing: -0.5px;
}

.hint {
  margin-top: 8px;
  font-size: 13px;
  color: var(--text-muted);
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
  background: linear-gradient(135deg, var(--primary-color), #1557b0);
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

.toggle-mode {
  margin-top: 16px;
  text-align: center;
  font-size: 13px;
  color: var(--primary-color);
  font-weight: 600;
  cursor: pointer;
  transition: color var(--duration-fast);
}

.toggle-mode:hover { color: #4a9af5; }

.code-section {
  margin-top: 4px;
}

.code-row {
  display: flex;
  gap: 10px;
  margin-top: 22px;
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

@media (max-width: 860px) {
  .login-screen {
    grid-template-columns: 1fr;
  }
  .login-hero { display: none; }
}
</style>
