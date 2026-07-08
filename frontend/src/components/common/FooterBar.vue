<template>
  <footer class="footer-bar">
    <span>VisionDrive 智视驾</span>
    <span>前端 Vue 3 + Element Plus</span>
    <span>当前数据源：Mock 演示数据</span>
  </footer>
</template>

<script setup></script>

<style scoped>
.footer-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 42px;
  padding: 0 26px;
  color: var(--text-muted);
  font-size: 12px;
  border-top: 1px solid var(--border-color);
  background: #fff;
}
</style>
