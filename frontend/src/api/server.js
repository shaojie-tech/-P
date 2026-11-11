// 服务器地址适配层（Web / 安卓 APK 双形态共用）：
// - Web 版：后端同源托管（或 Vite 开发代理），base 为空 → 全部走相对路径，行为不变；
// - APK 版：Capacitor WebView 的 origin 是 https://localhost，与后端不同源，
//   必须使用绝对地址。默认取构建期 VITE_SERVER_BASE，可在登录页运行时覆盖
//   （存 localStorage），方便局域网调试与换服务器后免重装。
const OVERRIDE_KEY = 'xiaop_server'
const BUILD_BASE = (import.meta.env.VITE_SERVER_BASE || '').replace(/\/+$/, '')

/** 是否运行在原生 App 壳内（Capacitor） */
export function isNativeApp() {
  const c = window.Capacitor
  return !!(c && c.isNativePlatform && c.isNativePlatform())
}

/** 当前生效的服务器基地址；空字符串 = 同源相对路径 */
export function getServerBase() {
  const saved = (localStorage.getItem(OVERRIDE_KEY) || '').trim().replace(/\/+$/, '')
  if (saved) return saved
  return BUILD_BASE
}

export function setServerBase(url) {
  const v = (url || '').trim().replace(/\/+$/, '')
  if (v) localStorage.setItem(OVERRIDE_KEY, v)
  else localStorage.removeItem(OVERRIDE_KEY)
}

/** 拼接 REST/SSE 接口地址 */
export function apiUrl(path) {
  return getServerBase() + path
}

/** 由服务器地址派生 WebSocket 地址（http→ws / https→wss） */
export function wsUrl(path) {
  const base = getServerBase()
  if (!base) {
    const proto = window.location.protocol === 'https:' ? 'wss://' : 'ws://'
    return proto + window.location.host + path
  }
  return base.replace(/^http/, 'ws') + path
}

/**
 * 401 统一跳转登录页（axios 拦截器与 SSE fetch 共用）。
 * 原生 App 用 hash 路由（当前路由在 location.hash 里），Web 用 history 路由。
 */
export function redirectToLogin() {
  const native = isNativeApp()
  const current = native
    ? window.location.hash.replace(/^#/, '') || '/'
    : window.location.pathname + window.location.search
  if (current.startsWith('/login')) return
  const redirect = encodeURIComponent(current)
  if (native) {
    window.location.hash = `#/login?redirect=${redirect}`
  } else {
    window.location.href = `/login?redirect=${redirect}`
  }
}
