/** 岗位：子管理(clerk) / 业务员工(worker) */

import { getSchema } from './domainSchema.js'

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
