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
        <p class="hint">演示模式 · 输入任意密码即可进入</p>

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

        <button class="login-btn" @click="handleLogin">
          进入系统
          <el-icon><ArrowRight /></el-icon>
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
            <button class="send-code-btn" :disabled="countdown > 0" @click="sendCode">
              {{ countdown > 0 ? `${countdown}s` : '获取验证码' }}
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
let timer

function sendCode() {
  if (!form.target) {
    ElMessage.warning('请先输入手机号或邮箱')
    return
  }
  countdown.value = 60
  ElMessage.success('演示验证码：483921')
  timer = setInterval(() => {
    countdown.value -= 1
    if (countdown.value <= 0) clearInterval(timer)
  }, 1000)
}

function handleLogin() {
  authStore.login(form.username || 'admin', form.password || 'visiondrive')
  ElMessage.success('欢迎使用 VisionDrive')
  router.push(route.query.redirect || '/dashboard')
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

.toggle-mode {
  margin-top: 16px;
  text-align: center;
  font-size: 13px;
  color: var(--primary-color);
  font-weight: 600;
  cursor: pointer;
  transition: color var(--duration-fast);
}

.toggle-mode:hover { color: #00e5ff; }

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
