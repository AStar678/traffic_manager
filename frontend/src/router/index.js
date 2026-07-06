import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginPage.vue')
  },
  {
    path: '/',
    component: () => import('@/views/MainLayout.vue'),
    redirect: '/license-plate',
    children: [
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

export default router
