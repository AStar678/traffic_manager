<template>
  <div class="auto-layout">
    <!-- 顶部状态栏（极简，仅显示时间和关键状态） -->
    <header class="top-bar">
      <div class="top-left">
        <span class="time-display">{{ currentTime }}</span>
        <span class="divider-dot">·</span>
        <span class="network-badge">
          <span class="status-dot online"></span>
          5G
        </span>
      </div>
      <div class="top-center">
        <span class="brand-wordmark">VisionDrive</span>
      </div>
      <div class="top-right">
        <span class="alert-indicator" v-if="alertCount > 0" @click="$router.push('/alert-dashboard')">
          <el-icon><Bell /></el-icon>
          <span class="alert-badge">{{ alertCount }}</span>
        </span>
        <span class="temp-outside">🌡 31°</span>
        <button class="user-avatar" @click="showUserMenu = !showUserMenu">
          {{ userInitial }}
        </button>
        <div v-if="showUserMenu" class="user-dropdown" @click="handleLogout">
          退出登录
        </div>
      </div>
    </header>

    <!-- 主内容区（全屏沉浸） -->
    <main class="view-container">
      <router-view v-slot="{ Component }">
        <transition name="car-fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <!-- 底部Dock导航栏（车机风格） -->
    <nav class="bottom-dock">
      <router-link
        v-for="item in dockItems"
        :key="item.path"
        :to="item.path"
        class="dock-item"
        :class="{ active: isActive(item.path) }"
      >
        <el-icon :size="22"><component :is="item.icon" /></el-icon>
        <span>{{ item.label }}</span>
      </router-link>
    </nav>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAlertStore } from '@/stores/alert'
import { useVehicleStore } from '@/stores/vehicle'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const alertStore = useAlertStore()
const vehicleStore = useVehicleStore()

alertStore.fetchAlerts()

const showUserMenu = ref(false)
let timeTimer = null
const timeNow = ref(new Date())

const currentTime = computed(() => {
  return timeNow.value.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
})

const userInitial = computed(() => {
  return (authStore.user?.nickname || 'U').charAt(0).toUpperCase()
})

const alertCount = computed(() => alertStore.unreadCount)

const dockItems = [
  { path: '/dashboard', label: '驾驶', icon: 'Monitor' },
  { path: '/alert-dashboard', label: '告警', icon: 'Bell' },
  { path: '/history', label: '记录', icon: 'Document' },
  { path: '/cameras', label: '摄像头', icon: 'VideoCamera' },
  { path: '/music', label: '音乐', icon: 'Headset' },
  { path: '/settings', label: '设置', icon: 'Setting' },
]

function isActive(path) {
  return route.path === path || (path === '/dashboard' && route.path === '/')
}

function handleLogout() {
  authStore.logout()
  router.push('/login')
}

onMounted(() => {
  vehicleStore.loadCurrent()
  alertStore.connectWebSocket()
  timeTimer = setInterval(() => { timeNow.value = new Date() }, 1000)
})

onBeforeUnmount(() => {
  clearInterval(timeTimer)
  alertStore.disconnectWebSocket()
})
</script>

<style scoped>
.auto-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
  height: 100dvh;
  background: var(--bg-root);
  overflow: hidden;
}

/* ===== 顶部状态栏 ===== */
.top-bar {
  height: 48px;
  min-height: 48px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: rgba(8, 12, 20, 0.92);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--border-subtle);
  z-index: 100;
}

.top-left,
.top-right {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 160px;
}

.top-right { justify-content: flex-end; }

.top-center {
  flex: 1;
  text-align: center;
}

.time-display {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: 0.5px;
}

.divider-dot {
  color: var(--text-muted);
}

.network-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-weight: 700;
  color: var(--success-color);
}

.brand-wordmark {
  font-size: 18px;
  font-weight: 800;
  letter-spacing: 1px;
  background: linear-gradient(135deg, var(--primary-color), #00e5ff);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.alert-indicator {
  position: relative;
  cursor: pointer;
  color: var(--text-secondary);
  transition: color var(--duration-fast);
}
.alert-indicator:hover { color: var(--warning-color); }

.alert-badge {
  position: absolute;
  top: -6px;
  right: -8px;
  min-width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--danger-color);
  color: #fff;
  font-size: 11px;
  font-weight: 800;
  border-radius: 999px;
}

.temp-outside {
  font-size: 13px;
  color: var(--text-secondary);
}

.user-avatar {
  width: 32px;
  height: 32px;
  border: 1.5px solid var(--border-card);
  border-radius: 50%;
  background: var(--primary-color);
  color: #080c14;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
  transition: border-color var(--duration-fast);
}
.user-avatar:hover { border-color: var(--primary-color); }

.user-dropdown {
  position: absolute;
  top: 44px;
  right: 24px;
  padding: 10px 18px;
  background: var(--bg-card);
  border: 1px solid var(--border-card);
  border-radius: 10px;
  font-size: 13px;
  color: var(--text-primary);
  cursor: pointer;
  box-shadow: var(--shadow-elevated);
  z-index: 200;
}
.user-dropdown:hover { color: var(--danger-color); }

/* ===== 主视图容器 ===== */
.view-container {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 20px 24px 16px;
  /* 底部留出dock高度 */
  padding-bottom: 12px;
}

/* ===== 视图切换动画 ===== */
.car-fade-enter-active,
.car-fade-leave-active {
  transition: opacity 220ms var(--ease-out), transform 220ms var(--ease-out);
}
.car-fade-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.car-fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

/* ===== 底部Dock导航 ===== */
.bottom-dock {
  height: 72px;
  min-height: 72px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 0 24px;
  background: rgba(15, 21, 34, 0.94);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-top: 1px solid var(--border-subtle);
  z-index: 100;
}

.dock-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  min-width: 72px;
  height: 54px;
  padding: 6px 14px;
  border-radius: 16px;
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.3px;
  transition: all var(--duration-fast) var(--ease-out);
  cursor: pointer;
}

.dock-item:hover {
  color: var(--text-secondary);
  background: rgba(255, 255, 255, 0.04);
}

.dock-item.active {
  color: var(--primary-color);
  background: var(--primary-soft);
}

.dock-item.active .el-icon {
  filter: drop-shadow(0 0 6px var(--primary-glow));
}
</style>
