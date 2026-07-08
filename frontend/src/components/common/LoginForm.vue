<template>
  <el-form class="login-form" @submit.prevent>
    <el-tabs v-model="mode" stretch>
      <el-tab-pane label="账号密码" name="password" />
      <el-tab-pane label="验证码登录" name="code" />
    </el-tabs>

    <template v-if="mode === 'password'">
      <el-form-item>
        <el-input v-model="form.username" size="large" placeholder="用户名：admin">
          <template #prefix><el-icon><User /></el-icon></template>
        </el-input>
      </el-form-item>
      <el-form-item>
        <el-input v-model="form.password" size="large" type="password" placeholder="密码：任意输入" show-password>
          <template #prefix><el-icon><Lock /></el-icon></template>
        </el-input>
      </el-form-item>
    </template>

    <template v-else>
      <el-form-item>
        <el-input v-model="form.target" size="large" placeholder="手机号或邮箱">
          <template #prefix><el-icon><Message /></el-icon></template>
        </el-input>
      </el-form-item>
      <el-form-item>
        <el-input v-model="form.code" size="large" maxlength="6" placeholder="6 位验证码">
          <template #append>
            <el-button :disabled="countdown > 0" @click="sendCode">
              {{ countdown > 0 ? `${countdown}s` : '发送验证码' }}
            </el-button>
          </template>
        </el-input>
      </el-form-item>
    </template>

    <el-button type="primary" size="large" class="login-button" @click="submit">
      登录系统
    </el-button>
    <p>演示阶段使用 Mock 登录，真实 JWT 接口完成后可无缝替换。</p>
  </el-form>
</template>

<script setup>
import { reactive, ref, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'

const emit = defineEmits(['login'])
const mode = ref('password')
const countdown = ref(0)
let timer

const form = reactive({
  username: 'admin',
  password: 'visiondrive',
  target: '',
  code: ''
})

function sendCode() {
  if (!form.target) {
    ElMessage.warning('请先输入手机号或邮箱')
    return
  }
  countdown.value = 60
  ElMessage.success('验证码已发送：483921')
  timer = window.setInterval(() => {
    countdown.value -= 1
    if (countdown.value <= 0) {
      window.clearInterval(timer)
    }
  }, 1000)
}

function submit() {
  if (mode.value === 'code' && form.code && form.code !== '483921') {
    ElMessage.error('演示验证码为 483921')
    return
  }
  emit('login', { ...form, mode: mode.value })
}

onBeforeUnmount(() => {
  if (timer) window.clearInterval(timer)
})
</script>

<style scoped>
.login-form {
  width: 100%;
}

.login-button {
  width: 100%;
  margin-top: 6px;
}

p {
  margin-top: 14px;
  color: var(--text-muted);
  font-size: 13px;
  line-height: 1.6;
}
</style>
