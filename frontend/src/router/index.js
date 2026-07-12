import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginPage.vue')
  },
  {
    path: '/',
    component: () => import('@/views/MainLayout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/DashboardPage.vue')
      },
      {
        path: 'license-plate',
        name: 'LicensePlate',
        component: () => import('@/views/LicensePlatePage.vue')
      },
      {
        path: 'police-gesture',
        name: 'PoliceGesture',
        component: () => import('@/views/PoliceGesturePage.vue')
      },
      {
        path: 'owner-gesture',
        name: 'OwnerGesture',
        component: () => import('@/views/OwnerGesturePage.vue')
      },
      {
        path: 'alert-dashboard',
        name: 'AlertDashboard',
        component: () => import('@/views/AlertDashboard.vue')
      },
      {
        path: 'history',
        name: 'History',
        component: () => import('@/views/HistoryPage.vue')
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@/views/SettingsPage.vue')
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async to => {
  const authStore = useAuthStore()
  await authStore.validateSession()
  if (to.path === '/login') {
    return authStore.isAuthenticated ? '/dashboard' : true
  }
  if (!authStore.isAuthenticated) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  return true
})

export default router
