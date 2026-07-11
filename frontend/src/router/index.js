import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginPage.vue')
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/RegisterPage.vue')
  },
  {
    path: '/forgot-password',
    name: 'ForgotPassword',
    component: () => import('@/views/ForgotPasswordPage.vue')
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

router.beforeEach(to => {
  const authStore = useAuthStore()
  if (to.path === '/login' || to.path === '/register' || to.path === '/forgot-password') {
    return authStore.isAuthenticated ? '/dashboard' : true
  }
  if (!authStore.isAuthenticated) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  return true
})

export default router
