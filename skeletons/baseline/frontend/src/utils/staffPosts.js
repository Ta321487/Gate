/** 岗位：子管理(clerk) / 业务员工(worker) */

import { getSchema, superOnlyAdminPaths } from './domainSchema.js'
import { ADMIN_MENU_PATHS } from './menuRoutes.js'

const ADMIN_KEY_BY_PATH = Object.fromEntries(
  Object.entries(ADMIN_MENU_PATHS).map(([key, path]) => [path, key]),
)
ADMIN_KEY_BY_PATH['/admin/profile'] = 'profile'

/**
 * 与路由 adminGuard 同一套：子管点不到总管菜单时返回 false，避免先跳再被弹回。
 * @param {string} path
 */
export function canOpenAdminPath(path) {
  const p = String(path || '').split('?')[0]
  if (!p.startsWith('/admin')) return false
  if (localStorage.getItem('role') !== 'admin') return false
  if (localStorage.getItem('superAdmin') === 'true') return true
  if (isWorkerSession()) return false
  if (superOnlyAdminPaths().has(p)) return false
  const allowed = clerkAllowedMenuKeys(currentStaffPost())
  if (!allowed) return true
  const key = ADMIN_KEY_BY_PATH[p]
  if (!key) return false
  if (key === 'profile' || key === 'messages' || key === 'dm' || key === 'order_reviews') return true
  return allowed.has(key)
}

/** 可进才返回原 path（可带 query），否则 ''——工作台/铃铛 CTA 共用 */
export function adminNavPath(path) {
  const raw = String(path || '')
  const base = raw.split('?')[0]
  return canOpenAdminPath(base) ? raw : ''
}

export function staffPosts() {
  const posts = getSchema()?.roles?.staff_posts
  return Array.isArray(posts) ? posts : []
}

export function findStaffPost(id) {
  if (!id) return null
  return staffPosts().find((p) => p.id === id) || null
}

export function hasWorkerPosts() {
  return staffPosts().some((p) => p.kind === 'worker')
}

export function clerkPosts() {
  return staffPosts().filter((p) => p.kind === 'clerk')
}

export function workerPosts() {
  return staffPosts().filter((p) => p.kind === 'worker')
}

export function staffPostLabel(id, fallback = '') {
  const p = findStaffPost(id)
  return (p && p.label) || fallback || id || ''
}

/** 当前登录岗位（localStorage） */
export function currentStaffPost() {
  return (localStorage.getItem('staffPost') || '').trim()
}

export function currentStaffKind() {
  return (localStorage.getItem('staffKind') || '').trim()
}

export function isWorkerSession() {
  return localStorage.getItem('role') === 'admin'
    && localStorage.getItem('superAdmin') !== 'true'
    && currentStaffKind() === 'worker'
}

export function isClerkSession() {
  if (localStorage.getItem('role') !== 'admin') return false
  if (localStorage.getItem('superAdmin') === 'true') return false
  const k = currentStaffKind()
  return !k || k === 'clerk'
}

/**
 * 子管理可见 admin 菜单 key；null 表示旧账号（无岗位）→ 全部非 superOnly。
 */
export function clerkAllowedMenuKeys(staffPostId) {
  const post = findStaffPost(staffPostId)
  if (!post || post.kind !== 'clerk') return null
  const packMenus = getSchema()?.staffPackMenus || {}
  const keys = new Set()
  for (const pk of post.packs || []) {
    for (const k of packMenus[pk] || []) keys.add(k)
  }
  if (!keys.size) keys.add('dashboard')
  return keys
}

/** 员工端页面 id：tickets | orders | slots */
export function workerAllowedPages(staffPostId) {
  const post = findStaffPost(staffPostId)
  if (!post || post.kind !== 'worker') return []
  const packPages = getSchema()?.staffPackPages || {}
  const pages = new Set()
  for (const pk of post.packs || []) {
    for (const p of packPages[pk] || []) pages.add(p)
  }
  return [...pages]
}

/** 登录成功后落地路径 */
export function homePathAfterLogin(user) {
  if (!user || user.role !== 'admin') return '/'
  if (user.superAdmin) return '/admin'
  if ((user.staffKind || '') === 'worker') return '/staff'
  return '/admin'
}
