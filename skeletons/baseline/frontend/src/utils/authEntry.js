/** 登录入口模式：优先工厂交付，其次 .env，交付后固定 */

import { FACTORY_DELIVERED } from '../factoryDelivered.js'
import { getSchema } from './domainSchema.js'
import { clerkPosts, hasWorkerPosts, workerPosts } from './staffPosts.js'

export const AUTH_ENTRY_MODES = [
  { id: 'unified', label: '统一登录' },
  { id: 'role_pick', label: '身份选择' },
  { id: 'split_entry', label: '分端入口' },
]

export const AUTH_ROLE_WIDGETS = [
  { id: 'radio', label: '单选' },
  { id: 'select', label: '下拉' },
]

const MODE_IDS = new Set(AUTH_ENTRY_MODES.map((t) => t.id))
const WIDGET_IDS = new Set(AUTH_ROLE_WIDGETS.map((t) => t.id))

export function pickAuthEntryMode() {
  const fromFactory = (FACTORY_DELIVERED?.authEntryMode || '').trim()
  if (fromFactory && MODE_IDS.has(fromFactory)) return fromFactory
  const fromEnv = (import.meta.env.VITE_AUTH_ENTRY_MODE || '').trim()
  if (fromEnv && MODE_IDS.has(fromEnv)) return fromEnv
  return 'role_pick'
}

export function pickAuthRoleWidget() {
  const fromFactory = (FACTORY_DELIVERED?.authRoleWidget || '').trim()
  if (fromFactory && WIDGET_IDS.has(fromFactory)) return fromFactory
  const fromEnv = (import.meta.env.VITE_AUTH_ROLE_WIDGET || '').trim()
  if (fromEnv && WIDGET_IDS.has(fromEnv)) return fromEnv
  return 'radio'
}

export function isSplitEntry() {
  return pickAuthEntryMode() === 'split_entry'
}

/** 管理端退出后的登录路径 */
export function adminLoginPath() {
  return isSplitEntry() ? '/admin/login' : '/login'
}

/** 员工端退出后的登录路径 */
export function staffLoginPath() {
  return isSplitEntry() ? '/staff/login' : '/login'
}

/**
 * 当前页可选的登录身份。
 * @param {'portal'|'admin'|'staff'|'all'} side
 */
export function loginRoleOptions(side = 'portal') {
  const roles = getSchema()?.roles || {}
  const user = {
    id: 'user',
    label: roles.user?.label || '用户',
  }
  const admin = {
    id: 'admin',
    label: roles.admin?.label || '总管',
  }
  const clerks = clerkPosts().map((p) => ({ id: p.id, label: p.label, kind: 'clerk' }))
  const workers = workerPosts().map((p) => ({ id: p.id, label: p.label, kind: 'worker' }))
  // 仅当 schema 声明了 subadmin 且未配置 staff_posts 时回退（旧交付）
  const postsDeclared = Array.isArray(roles.staff_posts)
  const subFallback =
    !postsDeclared && roles.subadmin
      ? [{ id: 'subadmin', label: roles.subadmin.label || '子管', kind: 'clerk' }]
      : []
  const clerkOpts = clerks.length ? clerks : subFallback

  if (side === 'admin') return [admin, ...clerkOpts]
  if (side === 'staff') return workers
  if (side === 'portal') return [user]
  // role_pick / all
  return [user, admin, ...clerkOpts, ...workers]
}

export function showStaffLoginLink() {
  return hasWorkerPosts()
}
