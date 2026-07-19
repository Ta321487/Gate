/**
 * 读取工厂注入的 Domain Schema（文案 / 菜单 / 能力）。
 * 业务页应优先用这里的标签，避免写死领域词。
 */
import { FACTORY_DELIVERED } from '../factoryDelivered.js'

export function getDelivered() {
  return FACTORY_DELIVERED || {}
}

export function getDomain() {
  return getDelivered().domain || 'DOM-GENERIC'
}

export function getDomainLabel() {
  return getDelivered().domainLabel || '通用'
}

export function getSchema() {
  return getDelivered().schema || {}
}

export function schemaLabels() {
  return getSchema().labels || {}
}

/** 领域主数据菜单 key（总管专属） */
export const MASTER_MENU_KEYS = new Set([
  'archive',
  'category',
  'lookup_site',
  'lookup_type',
])

/** 总管配置类菜单（含用户/公告） */
export const SUPER_ONLY_FALLBACK_KEYS = new Set([
  ...MASTER_MENU_KEYS,
  'users',
  'content',
])

export function schemaMenus(side = 'admin') {
  const menus = getSchema().menus || {}
  return menus[side] || []
}

export function isSuperOnlyMenu(item) {
  if (!item) return false
  if (item.superOnly === true) return true
  if (item.superOnly === false) return false
  return SUPER_ONLY_FALLBACK_KEYS.has(item.key)
}

export function superOnlyAdminPaths() {
  const map = {
    users: '/admin/users',
    content: '/admin/notices',
    lookup_site: '/admin/sites',
    lookup_type: '/admin/types',
    archive: '/admin/archive',
    category: '/admin/categories',
  }
  const paths = new Set()
  for (const m of schemaMenus('admin')) {
    if (isSuperOnlyMenu(m) && map[m.key]) paths.add(map[m.key])
  }
  if (!paths.size) {
    ;['/admin/users', '/admin/notices', '/admin/sites', '/admin/types'].forEach((p) => paths.add(p))
  }
  return paths
}

export function menuLabel(side, key, fallback = '') {
  const item = schemaMenus(side).find((m) => m.key === key)
  return (item && item.label) || fallback
}

export function ticketCopy() {
  return (getSchema().entities || {}).ticket || {}
}

export function archiveCopy() {
  return (getSchema().entities || {}).archive || {}
}

export function acceptLevel() {
  return getDelivered().accept || getSchema().accept || 'reject'
}

/** 领域用户资料字段（含公共底座） */
export function profileFields() {
  const list = getSchema().profileFields
  return Array.isArray(list) ? list : []
}

export function profileFieldsOnRegister() {
  return profileFields().filter((f) => f && f.onRegister)
}

/** 管理端表格优先展示的扩展列（跳过公共底座） */
export function profileAdminColumns(limit = 2) {
  const skip = new Set(['realName', 'phone', 'email', 'gender'])
  return profileFields()
    .filter((f) => f && f.storage !== 'phone' && !skip.has(f.key))
    .slice(0, limit)
}

export function emptyProfileExtras(fields = profileFields()) {
  const o = {}
  for (const f of fields) {
    if (!f?.key || f.storage === 'phone') continue
    o[f.key] = ''
  }
  return o
}
