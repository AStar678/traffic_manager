<template>
  <header class="nav-bar">
    <div>
      <p class="eyebrow">车载视觉感知与人机交互 Web 系统</p>
      <h1>{{ title }}</h1>
    </div>

    <div class="nav-actions">
      <span class="metric-chip severity-info">摄像头服务输入</span>
      <span class="metric-chip severity-info">WebSocket 已连接</span>
      <el-badge :value="unreadCount" :hidden="!unreadCount">
        <el-button circle>
          <el-icon><Bell /></el-icon>
        </el-button>
      </el-badge>
      <el-dropdown>
        <button class="user-button">
          <el-icon><UserFilled /></el-icon>
          <span>{{ user?.nickname || '演示用户' }}</span>
        </button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item>角色：{{ user?.role || 'ADMIN' }}</el-dropdown-item>
            <el-dropdown-item divided @click="handleLogout">退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAlertStore } from '@/stores/alert'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const alertStore = useAlertStore()

const titleMap = {
  Dashboard: '车辆状态总览',
  LicensePlate: '道路车辆车牌识别',
  PoliceGesture: '交警手势识别',
  OwnerGesture: '车主手势控车',
  AlertDashboard: '告警智能体仪表盘',
  History: '历史识别记录',
  Settings: '系统设置'
}

const title = computed(() => titleMap[route.name] || 'VisionDrive')
const user = computed(() => authStore.user)
const unreadCount = computed(() => alertStore.unreadCount)

function handleLogout() {
  authStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.nav-bar {
  min-height: 76px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 0 26px;
  background: rgba(255, 255, 255, 0.92);
  border-bottom: 1px solid var(--border-color);
  backdrop-filter: blur(12px);
}

.eyebrow {
  color: var(--text-muted);
  font-size: 13px;
  font-weight: 700;
}

h1 {
  margin-top: 4px;
  color: #142033;
  font-size: 22px;
  font-weight: 900;
  line-height: 1.2;
}

.nav-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-button {
  height: 38px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 0 12px;
  border: 1px solid var(--border-color);
  border-radius: 999px;
  background: #fff;
  color: #233047;
  cursor: pointer;
  font-weight: 800;
}
</style>
