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

/**
 * 门户用户菜单：在 schema 基础上补「消息」入口。
 * 不灌「首页」枢纽——默认进业务页（档案/单据），避免落地只有两张卡片。
 * 管理端原样返回。
 */
export function schemaMenus(side = 'admin') {
  const menus = getSchema().menus || {}
  const raw = menus[side] || []
  if (side !== 'user') return raw

  const list = raw.map((m) => ({ ...m }))
  const keys = new Set(list.map((m) => m.key))
  if (!keys.has('messages')) {
    const item = { key: 'messages', label: '消息' }
    const pi = list.findIndex((m) => m.key === 'profile')
    if (pi >= 0) list.splice(pi, 0, item)
    else list.push(item)
    keys.add('messages')
  }
  // 预约壳有 /slots 页时露出独立入口（目录仍保留）
  const caps = getSchema().capabilities || []
  if (caps.includes('slot_reserve') && !keys.has('slots')) {
    const item = { key: 'slots', label: '预约选时' }
    const ai = list.findIndex((m) => m.key === 'archive')
    if (ai >= 0) list.splice(ai + 1, 0, item)
    else list.splice(1, 0, item)
  }
  return list
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

/** 到期日文案：缺省用中性「到期日」，勿 fallback「应还」 */
export function ticketDueLabel(fallback = '到期日') {
  const t = ticketCopy()
  return t.dueLabel || t.dueAtLabel || fallback
}

/** 逾期费用文案：缺省「逾期费用」，图书/设备域由 schema 写「罚款」 */
export function ticketFineLabel(fallback = '逾期费用') {
  return ticketCopy().fineLabel || fallback
}

export function ticketFinePaidLabel(fallback = '费用已结清') {
  return ticketCopy().finePaidLabel || fallback
}

export function ticketCheckinLabel(fallback = '签到') {
  return ticketCopy().checkinLabel || fallback
}

export function ticketRemindVerb(fallback = '催办') {
  return ticketCopy().verbs?.remind || fallback
}

export function ticketReturnVerb(fallback = '完结') {
  return ticketCopy().verbs?.return || fallback
}

export function reservationCopy() {
  return (getSchema().entities || {}).reservation || {}
}

export function archiveCopy() {
  return (getSchema().entities || {}).archive || {}
}

/**
 * 软删文案：图书/商城等用「下架」；活动/选课等用「停用」，避免活动域还写「在架」。
 */
export function softDeleteCopy() {
  const arch = archiveCopy()
  if (arch.softDeleteOnLabel || arch.softDeleteOffLabel || arch.softDeleteVerb) {
    return {
      on: arch.softDeleteOnLabel || '启用',
      off: arch.softDeleteOffLabel || '已停用',
      verb: arch.softDeleteVerb || '停用',
      include: arch.softDeleteIncludeLabel || `含${arch.softDeleteVerb || '停用'}`,
    }
  }
  const shelf = new Set([
    'DOM-LIBRARY', 'DOM-SHOP', 'DOM-FOOD', 'DOM-MEDIA', 'DOM-MUSIC', 'DOM-BLOG', 'DOM-FORUM',
  ])
  if (shelf.has(getDomain())) {
    return { on: '在架', off: '已下架', verb: '下架', include: '含下架' }
  }
  return { on: '启用', off: '已停用', verb: '停用', include: '含停用' }
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
