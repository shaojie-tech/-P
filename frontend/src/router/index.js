import { createRouter, createWebHashHistory, createWebHistory } from 'vue-router'
import { isNativeApp } from '../api/server'
import { useAuthStore } from '../stores/auth'

const routes = [
  { path: '/login', name: 'login', component: () => import('../views/LoginView.vue'), meta: { public: true } },
  { path: '/', name: 'chat', component: () => import('../views/ChatView.vue') },
  { path: '/voice', name: 'voice', component: () => import('../views/VoiceView.vue') },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  // 安卓 APK（Capacitor WebView）用 hash 路由：本地资产服务对深层路径的
  // history 回退不可靠；Web 版保持 history 路由不变
  history: isNativeApp() ? createWebHashHistory() : createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.user && auth.token) {
    await auth.fetchMe()
  }
  if (!to.meta.public && !auth.isLoggedIn) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.name === 'login' && auth.isLoggedIn) {
    return { path: '/' }
  }
  return true
})

export default router
