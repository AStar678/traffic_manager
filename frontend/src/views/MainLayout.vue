<template>
  <div class="auto-layout">
    <!-- 顶部状态栏：极简车机风格 -->
    <header class="top-bar">
      <div class="top-left">
        <span class="time-display">{{ currentTime }}</span>
        <span class="top-sep">|</span>
        <span class="network-badge">
          <span class="status-dot online"></span>5G
        </span>
        <span class="top-sep">|</span>
        <span class="temp">🌡 31°</span>
      </div>
      <div class="top-center">
        <span class="brand">VisionDrive</span>
      </div>
      <div class="top-right">
        <!-- 告警通知 -->
        <span class="notif-btn" @click="$router.push('/alert-dashboard')">
          <el-icon :size="18"><Bell /></el-icon>
          <span v-if="alertCount" class="badge">{{ alertCount }}</span>
        </span>
        <!-- WebSocket 状态 -->
        <span class="ws-indicator" :class="{ connected: wsConnected }">
          <span class="status-dot" :class="wsConnected ? 'online' : 'warning-dot'"></span>
        </span>
        <!-- 用户 -->
        <button class="avatar-btn" @click="showUserMenu = !showUserMenu">
          {{ userInitial }}
        </button>
        <div v-if="showUserMenu" class="user-drop" @click="handleLogout">
          <el-icon><SwitchButton /></el-icon> 退出
        </div>
      </div>
    </header>

    <!-- 主内容区 -->
    <main class="view-container">
      <router-view v-slot="{ Component }">
        <transition name="car-fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <!-- 底部Dock：车机风格导航 -->
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
        <span v-if="item.badge" class="dock-badge">{{ item.badge }}</span>
      </router-link>
    </nav>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAlertStore } from '@/stores/alert'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const alertStore = useAlertStore()

alertStore.fetchAlerts()

const showUserMenu = ref(false)
const wsConnected = ref(true)
let timeTimer = null
const timeNow = ref(new Date())

const currentTime = computed(() => {
  return timeNow.value.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
})

const userInitial = computed(() => {
  return (authStore.user?.nickname || 'U').charAt(0).toUpperCase()
})

const alertCount = computed(() => alertStore.unreadCount)

const dockItems = computed(() => [
  { path: '/dashboard',       label: '驾驶',   icon: 'Monitor',  badge: null },
  { path: '/license-plate',   label: '车牌',   icon: 'Camera',   badge: null },
  { path: '/police-gesture',  label: '交警',   icon: 'Aim',      badge: null },
  { path: '/owner-gesture',   label: '手势',   icon: 'Pointer',  badge: null },
  { path: '/alert-dashboard', label: '告警',   icon: 'Bell',     badge: alertCount.value || null },
])

function isActive(path) {
  if (path === '/dashboard' && route.path === '/') return true
  return route.path === path
}

function handleLogout() {
  authStore.logout()
  router.push('/login')
}

onMounted(() => {
  timeTimer = setInterval(() => { timeNow.value = new Date() }, 1000)
})

onBeforeUnmount(() => {
  clearInterval(timeTimer)
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

/* ===== 顶部 ===== */
.top-bar {
  height: 46px;
  min-height: 46px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 22px;
  background: rgba(10, 13, 20, 0.94);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--border-subtle);
  z-index: 100;
}

.top-left, .top-right {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 140px;
}
.top-right { justify-content: flex-end; }
.top-center { flex: 1; text-align: center; }

.time-display {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: 0.3px;
}

.top-sep {
  color: var(--border-card);
}

.network-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-weight: 700;
  color: var(--success-color);
}

.temp {
  font-size: 12px;
  color: var(--text-secondary);
}

.brand {
  font-size: 18px;
  font-weight: 800;
  letter-spacing: 1px;
  background: linear-gradient(135deg, var(--primary-color), #4a9af5);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.notif-btn {
  position: relative;
  cursor: pointer;
  color: var(--text-secondary);
  padding: 6px;
  border-radius: 8px;
  transition: all var(--duration-fast);
}
.notif-btn:hover { color: var(--warning-color); background: rgba(255,255,255,0.04); }

.badge {
  position: absolute;
  top: 0; right: 0;
  min-width: 16px; height: 16px;
  display: flex; align-items: center; justify-content: center;
  background: var(--danger-color);
  color: #fff;
  font-size: 10px; font-weight: 800;
  border-radius: 999px;
}

.ws-indicator { display: flex; align-items: center; }
.ws-indicator .status-dot { margin: 0; }

.avatar-btn {
  width: 30px; height: 30px;
  border: 1.5px solid var(--border-card);
  border-radius: 50%;
  background: var(--primary-color);
  color: #fff;
  font-size: 12px; font-weight: 800;
  cursor: pointer;
}

.user-drop {
  position: absolute;
  top: 44px; right: 22px;
  display: flex; align-items: center; gap: 6px;
  padding: 10px 16px;
  background: var(--bg-card);
  border: 1px solid var(--border-card);
  border-radius: 10px;
  font-size: 13px;
  color: var(--text-primary);
  cursor: pointer;
  box-shadow: var(--shadow-elevated);
  z-index: 200;
}
.user-drop:hover { color: var(--danger-color); }

/* ===== 主视图 ===== */
.view-container {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 16px 20px;
}

/* 视图切换动画 */
.car-fade-enter-active,
.car-fade-leave-active {
  transition: opacity 200ms var(--ease-out), transform 200ms var(--ease-out);
}
.car-fade-enter-from { opacity: 0; transform: translateY(8px); }
.car-fade-leave-to { opacity: 0; transform: translateY(-8px); }

/* ===== 底部Dock ===== */
.bottom-dock {
  height: 70px;
  min-height: 70px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 0 16px;
  background: rgba(17, 22, 32, 0.95);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-top: 1px solid var(--border-subtle);
  z-index: 100;
}

.dock-item {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  min-width: 68px;
  height: 54px;
  padding: 6px 12px;
  border-radius: 14px;
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.3px;
  transition: all var(--duration-fast) var(--ease-out);
}

.dock-item:hover {
  color: var(--text-secondary);
  background: rgba(255,255,255,0.03);
}

.dock-item.active {
  color: var(--primary-color);
  background: var(--primary-soft);
}

.dock-item.active .el-icon {
  filter: drop-shadow(0 0 6px var(--primary-glow));
}

.dock-badge {
  position: absolute;
  top: 4px; right: 8px;
  min-width: 16px; height: 16px;
  display: flex; align-items: center; justify-content: center;
  background: var(--danger-color);
  color: #fff;
  font-size: 10px; font-weight: 800;
  border-radius: 999px;
  line-height: 1;
}
</style>
