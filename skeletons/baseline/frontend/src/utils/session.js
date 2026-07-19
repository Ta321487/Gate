/** 会话：localStorage 只是壳，真登录态在服务端 HttpSession。 */

import axios from 'axios'
import { FACTORY_DELIVERED } from '../factoryDelivered.js'
import { adminLoginPath, isSplitEntry } from './authEntry.js'
import { schemaLabels } from './domainSchema.js'

let kicking = false
/** @type {boolean|null} null=未探测 */
let sessionCache = null
let sessionProbe = null

export function clearAuthStorage() {
  localStorage.removeItem('token')
  localStorage.removeItem('role')
  localStorage.removeItem('username')
  localStorage.removeItem('nickname')
  localStorage.removeItem('avatarUrl')
  localStorage.removeItem('profileEditable')
  localStorage.removeItem('superAdmin')
  sessionCache = null
}

/** 业务码 40100 = 未登录 / 会话失效（验证码错误 40101 不踢） */
export function isUnauthorizedPayload(body) {
  if (!body || typeof body !== 'object') return false
  const code = Number(body.code)
  if (code === 40100) return true
  return code !== 40101 && String(body.message || '') === '未登录'
}

export function loginPathForRole(role) {
  if (role === 'admin' && isSplitEntry()) return adminLoginPath()
  return '/login'
}

export function isLoggedIn() {
  return !!localStorage.getItem('token')
}

export function isGuestBrowseEnabled() {
  return !!FACTORY_DELIVERED?.portalGuestBrowse
}

export function guestTeaserLimit() {
  const n = Number(FACTORY_DELIVERED?.guestTeaserLimit)
  return Number.isFinite(n) && n > 0 ? n : 3
}

export function guestLoginCta() {
  const fromDelivered = (FACTORY_DELIVERED?.guestLoginCta || '').trim()
  if (fromDelivered) return fromDelivered
  const fromLabels = (schemaLabels()?.guestLoginCta || '').trim()
  return fromLabels || '登录查看更多'
}

/** 游客可进的门户路径（不含管理端） */
export function isPortalPublicPath(path) {
  if (!path) return false
  if (path === '/home' || path === '/' || path === '/archive' || path === '/notices' || path === '/slots') {
    return true
  }
  if (path.startsWith('/notices/')) return true
  return false
}

/**
 * 未登录则跳登录并带 redirect；已登录返回 true。
 * @param {import('vue-router').Router} router
 * @param {string} [redirect]
 */
export function requireLogin(router, redirect) {
  if (isLoggedIn()) return true
  const redir = redirect || router.currentRoute?.value?.fullPath || '/'
  router.push({ path: '/login', query: { redirect: redir } })
  return false
}

/** 不经业务拦截器探测会话，避免循环依赖 */
export async function probeSession() {
  if (!localStorage.getItem('token')) {
    sessionCache = false
    return false
  }
  if (sessionCache === true) return true
  if (sessionProbe) return sessionProbe
  sessionProbe = axios
    .get('/api/auth/me', { withCredentials: true, timeout: 8000 })
    .then((res) => {
      const body = res.data
      const ok = body && Number(body.code) === 0 && !isUnauthorizedPayload(body)
      sessionCache = ok
      if (!ok) clearAuthStorage()
      return ok
    })
    .catch(() => {
      sessionCache = false
      clearAuthStorage()
      return false
    })
    .finally(() => {
      sessionProbe = null
    })
  return sessionProbe
}

export function markSessionOk() {
  sessionCache = true
}

/**
 * 清本地态并跳登录页。可重复调用，只跳一次。
 * @param {import('vue-router').Router} router
 * @param {string} [message]
 */
export function kickToLogin(router, message) {
  if (kicking) return
  kicking = true
  const role = localStorage.getItem('role')
  clearAuthStorage()
  const path = loginPathForRole(role)
  const go = () => {
    const cur = router.currentRoute?.value?.path
    if (cur === path || cur === '/login' || cur === '/admin/login' || cur === '/register') {
      kicking = false
      return
    }
    router.replace(path).finally(() => {
      kicking = false
    })
  }
  if (message) {
    import('element-plus')
      .then(({ ElMessage }) => {
        ElMessage.error(message)
        go()
      })
      .catch(go)
  } else {
    go()
  }
}
