<template>
  <aside class="side-menu">
    <div class="brand">
      <div class="brand-mark">VD</div>
      <div>
        <strong>VisionDrive</strong>
        <span>智视驾交互系统</span>
      </div>
    </div>

    <nav class="menu-list">
      <RouterLink
        v-for="item in menuItems"
        :key="item.path"
        :to="item.path"
        class="menu-item"
      >
        <el-icon><component :is="item.icon" /></el-icon>
        <span>{{ item.label }}</span>
      </RouterLink>
    </nav>

    <div class="side-status">
      <span class="pulse"></span>
      <div>
        <strong>模型服务正常</strong>
        <p>Mock 演示数据已启用</p>
      </div>
    </div>
  </aside>
</template>

<script setup>
const menuItems = [
  { path: '/license-plate', label: '车牌识别', icon: 'Camera' },
  { path: '/police-gesture', label: '交警手势识别', icon: 'Aim' },
  { path: '/owner-gesture', label: '车主手势控车', icon: 'Operation' },
  { path: '/alert-dashboard', label: '告警仪表盘', icon: 'Bell' },
  { path: '/history', label: '历史记录', icon: 'Document' },
  { path: '/dashboard', label: '车辆状态总览', icon: 'DataBoard' },
  { path: '/settings', label: '系统设置', icon: 'Setting' }
]
</script>

<style scoped>
.side-menu {
  position: sticky;
  top: 0;
  height: 100vh;
  width: 260px;
  flex: 0 0 260px;
  display: flex;
  flex-direction: column;
  padding: 22px 16px;
  background: #0f2744;
  color: #d9e6f8;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 8px 24px;
}

.brand-mark {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: #1a73e8;
  color: #fff;
  font-weight: 900;
}

.brand strong {
  display: block;
  color: #fff;
  font-size: 21px;
  line-height: 1.2;
}

.brand span {
  display: block;
  margin-top: 4px;
  color: #9fb3cd;
  font-size: 12px;
}

.menu-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 46px;
  padding: 0 14px;
  border-radius: 8px;
  color: #c8d6e8;
  font-size: 15px;
  font-weight: 700;
  transition: background 0.2s, color 0.2s, transform 0.2s;
}

.menu-item:hover,
.menu-item.router-link-active {
  background: #1a73e8;
  color: #fff;
  transform: translateX(2px);
}

.side-status {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: auto;
  padding: 14px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.08);
}

.side-status strong {
  display: block;
  color: #fff;
  font-size: 13px;
}

.side-status p {
  margin-top: 2px;
  color: #9fb3cd;
  font-size: 12px;
}

.pulse {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #34a853;
  box-shadow: 0 0 0 6px rgba(52, 168, 83, 0.16);
}
</style>
