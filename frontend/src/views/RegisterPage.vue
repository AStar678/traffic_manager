<template>
  <div class="login-screen">
    <div class="login-hero">
      <div class="hero-bg"></div>
      <div class="hero-content">
        <div class="brand-mark-lg">VD</div>
        <h1>VisionDrive</h1>
        <p class="subtitle">智视驾 · 车载视觉感知与交互系统</p>
        <div class="hero-features">
          <span>车牌识别</span><span>交警手势</span><span>手势控车</span><span>AI告警</span>
        </div>
      </div>
    </div>

    <div class="login-panel">
      <div class="login-card">
        <h2>注册账号</h2>
        <p class="hint">手机号验证后设置密码即可登录系统</p>

        <div class="form-group">
          <label>手机号</label>
          <div class="input-wrapper">
            <el-icon><Phone /></el-icon>
            <input v-model="form.phone" type="tel" maxlength="11" placeholder="请输入手机号" class="auto-input" />
          </div>
          <p v-if="form.phone && !phoneOk" style="margin-top:6px;font-size:12px;color:var(--danger-color)">请输入正确的11位手机号</p>
        </div>

        <div class="form-group">
          <label>验证码</label>
          <div class="code-row">
            <div class="input-wrapper" style="flex:1">
              <el-icon><Message /></el-icon>
              <input v-model="form.code" type="text" maxlength="6" placeholder="6位验证码" class="auto-input" />
            </div>
            <button class="send-code-btn" :disabled="countdown > 0 || sending" @click="sendCode">
              {{ sending ? '发送中' : countdown > 0 ? `${countdown}s` : '获取验证码' }}
            </button>
          </div>
        </div>

        <div class="form-group">
          <label>设置密码</label>
          <div class="input-wrapper">
            <el-icon><Lock /></el-icon>
            <input v-model="form.password" :type="showPwd ? 'text' : 'password'" placeholder="至少6位，含字母和数字" class="auto-input" />
          </div>
          <p v-if="form.password && !pwdOk" style="margin-top:6px;font-size:12px;color:var(--danger-color)">至少6位，需包含字母和数字</p>
        </div>

        <div class="form-group">
          <label>确认密码</label>
          <div class="input-wrapper">
            <el-icon><Lock /></el-icon>
            <input v-model="form.confirmPwd" :type="showCfm ? 'text' : 'password'" placeholder="再次输入密码" class="auto-input" @keyup.enter="handleRegister" />
          </div>
          <p v-if="form.confirmPwd && !matchOk" style="margin-top:6px;font-size:12px;color:var(--danger-color)">两次密码不一致</p>
        </div>

        <button class="login-btn" :disabled="submitting" @click="handleRegister">
          {{ submitting ? '注册中...' : '注 册' }}
        </button>

        <div style="margin-top:18px;text-align:center;font-size:13px;color:var(--text-muted);">
          已有账号？<span style="color:var(--primary-color);font-weight:600;cursor:pointer;" @click="$router.push('/login')">去登录 →</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, computed, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { sendCode as apiSendCode, register as apiRegister } from '@/api/auth'

const router = useRouter()
const showPwd = ref(false); const showCfm = ref(false)
const countdown = ref(0); const sending = ref(false); const submitting = ref(false)
let timer = null

const form = reactive({ phone: '', code: '', password: '', confirmPwd: '' })
const phoneOk = computed(() => /^1[3-9]\d{9}$/.test(form.phone))
const pwdOk = computed(() => form.password.length >= 6 && /[a-zA-Z]/.test(form.password) && /\d/.test(form.password))
const matchOk = computed(() => form.password && form.password === form.confirmPwd)

async function sendCode() {
  if (!phoneOk.value) return ElMessage.warning('请输入正确的11位手机号')
  sending.value = true
  try {
    const res = await apiSendCode(form.phone)
    const data = res.data || res
    if (res.code === 0) {
      ElMessage.success('验证码已发送至 ' + form.phone.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2'))
      startCountdown(data?.retryAfter || 60)
    } else if (res.code === 429) {
      ElMessage.warning(res.message || `请 ${data?.retryAfter} 秒后再试`)
      if (data?.retryAfter) startCountdown(data.retryAfter)
    } else {
      ElMessage.error(res.message || '发送失败')
    }
  } catch { ElMessage.error('网络异常，请检查后端服务') }
  finally { sending.value = false }
}

function startCountdown(s = 60) { countdown.value = s; clearInterval(timer); timer = setInterval(() => { countdown.value--; if (countdown.value <= 0) clearInterval(timer) }, 1000) }

async function handleRegister() {
  if (!phoneOk.value) return ElMessage.warning('请输入正确的11位手机号')
  if (!form.code || form.code.length !== 6) return ElMessage.warning('请输入6位验证码')
  if (!pwdOk.value) return ElMessage.warning('密码至少6位，需含字母和数字')
  if (!matchOk.value) return ElMessage.warning('两次密码不一致')
  submitting.value = true
  try {
    await apiRegister({ phone: form.phone, smsCode: form.code, password: form.password, username: form.phone })
    ElMessage.success('注册成功，请登录')
    router.push('/login')
  } catch (e) { ElMessage.error(e?.response?.data?.message || e?.message || '注册失败') }
  finally { submitting.value = false }
}
onBeforeUnmount(() => { if (timer) clearInterval(timer) })
</script>

<style scoped>
.login-screen { display: grid; grid-template-columns: minmax(0, 1fr) 480px; height: 100vh; height: 100dvh; background: var(--bg-root); }
.login-hero { position: relative; display: flex; align-items: center; justify-content: center; overflow: hidden; }
.hero-bg { position: absolute; inset: 0; background: radial-gradient(ellipse at 30% 50%, rgba(0, 180, 216, 0.08) 0%, transparent 60%), radial-gradient(ellipse at 70% 30%, rgba(0, 100, 180, 0.06) 0%, transparent 50%), var(--bg-root); }
.hero-bg::after { content: ''; position: absolute; inset: 0; background-image: linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px); background-size: 60px 60px; }
.hero-content { position: relative; text-align: center; z-index: 1; }
.brand-mark-lg { width: 80px; height: 80px; display: grid; place-items: center; margin: 0 auto 24px; background: linear-gradient(135deg, var(--primary-color), #0096c7); border-radius: 20px; color: #080c14; font-size: 30px; font-weight: 900; box-shadow: 0 0 40px var(--primary-glow); }
.login-hero h1 { font-size: 42px; font-weight: 800; color: var(--text-primary); letter-spacing: -1px; }
.subtitle { margin-top: 10px; font-size: 16px; color: var(--text-secondary); }
.hero-features { display: flex; gap: 12px; justify-content: center; margin-top: 28px; flex-wrap: wrap; }
.hero-features span { padding: 7px 16px; background: rgba(255,255,255,0.05); border: 1px solid var(--border-card); border-radius: 999px; font-size: 13px; font-weight: 600; color: var(--text-secondary); }
.login-panel { display: flex; align-items: center; justify-content: center; padding: 48px; background: var(--bg-surface); border-left: 1px solid var(--border-subtle); }
.login-card { width: 100%; max-width: 360px; }
.login-card h2 { font-size: 28px; font-weight: 800; color: var(--text-primary); letter-spacing: -0.5px; }
.hint { margin-top: 8px; font-size: 13px; color: var(--text-muted); }
.form-group { margin-top: 22px; }
.form-group label { display: block; margin-bottom: 8px; font-size: 12px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; }
.input-wrapper { display: flex; align-items: center; gap: 10px; padding: 0 14px; background: var(--bg-card); border: 1px solid var(--border-card); border-radius: 12px; transition: border-color var(--duration-fast); }
.input-wrapper:focus-within { border-color: var(--border-active); box-shadow: 0 0 12px var(--primary-glow); }
.input-wrapper .el-icon { color: var(--text-muted); font-size: 18px; }
.auto-input { flex: 1; height: 46px; border: none; background: transparent; color: var(--text-primary); font-size: 15px; outline: none; }
.auto-input::placeholder { color: var(--text-muted); }
.code-row { display: flex; gap: 10px; margin-top: 0; }
.send-code-btn { min-width: 110px; padding: 0 14px; border: 1px solid var(--primary-color); border-radius: 12px; background: transparent; color: var(--primary-color); font-size: 13px; font-weight: 700; cursor: pointer; white-space: nowrap; }
.send-code-btn:hover:not(:disabled) { background: var(--primary-soft); }
.send-code-btn:disabled { border-color: var(--border-card); color: var(--text-muted); cursor: not-allowed; }
.login-btn { width: 100%; height: 48px; display: flex; align-items: center; justify-content: center; gap: 8px; margin-top: 24px; border: none; border-radius: 12px; background: linear-gradient(135deg, var(--primary-color), #0096c7); color: #080c14; font-size: 16px; font-weight: 700; cursor: pointer; box-shadow: 0 4px 20px var(--primary-glow); transition: all var(--duration-fast); }
.login-btn:hover:not(:disabled) { box-shadow: 0 6px 30px rgba(0, 180, 216, 0.35); transform: translateY(-1px); }
.login-btn:disabled { opacity: 0.6; cursor: not-allowed; }
@media (max-width: 860px) { .login-screen { grid-template-columns: 1fr; } .login-hero { display: none; } }
</style>
