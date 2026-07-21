/**
 * 读取课题注入的 Domain Schema（文案 / 菜单 / 能力）。
 * 业务页应优先用这里的标签，避免写死领域词。
 */
import { APP_DELIVERED } from '../appDelivered.js'

export function getDelivered() {
  return APP_DELIVERED || {}
}

/** 短皮肤 id（如 library / food），非工厂 DOM 编号 */
export function getFlavor() {
  return getDelivered().flavor || 'generic'
}

/** @deprecated 兼容旧调用；等价于 getFlavor() */
export function getDomain() {
  return getFlavor()
}

export function getTraits() {
  return getDelivered().traits || {}
}

export function hasTrait(name) {
  return !!getTraits()[name]
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
  'guestbook',
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
  // 预约时段页须带资源 itemId（从目录点「选时段」进入），不单独挂顶栏入口，避免空号源+工厂口吻空态
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
    guestbook: '/admin/guestbook',
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
    ;['/admin/users', '/admin/notices', '/admin/guestbook', '/admin/sites', '/admin/types'].forEach((p) => paths.add(p))
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

/** 单据状态码 → schema.states 文案 */
export function ticketStatusLabel(status, fallback = '') {
  if (status == null || status === '') return fallback || ''
  const key = String(status)
  const states = ticketCopy().states || {}
  if (states[key]) return states[key]
  // 历史进度曾写 noshow，与 overdue（爽约）同义
  if (key === 'noshow' && states.overdue) return states.overdue
  return fallback || key
}

/**
 * 进度流水状态展示：优先 states；签到/领取/费用等用实体文案。
 */
export function ticketProgressStatusLabel(status) {
  if (status == null || status === '') return ''
  const key = String(status)
  const mapped = ticketStatusLabel(key, '')
  if (mapped && mapped !== key) return mapped
  if (key === 'checkin') return ticketCheckinLabel('签到')
  if (key === 'fine_paid') return ticketFinePaidLabel('费用已结清')
  if (key === 'pickup') return '领取登记'
  if (key === 'rated') return '评价'
  return mapped || key
}

export function reservationCopy() {
  const raw = (getSchema().entities || {}).reservation || {}
  const label = typeof raw.label === 'string' ? raw.label.trim() : ''
  // 动作名词勿带「记录」（管理端菜单才用 XX记录）；避免「取消预约记录」
  if (label.endsWith('记录') && label.length > 2) {
    return { ...raw, label: label.replace(/记录$/, '') || '预约' }
  }
  return raw
}

export function archiveCopy() {
  return (getSchema().entities || {}).archive || {}
}

/**
 * 档案字段是否按金额展示（0 / 0.00 为有效值，空串才是空）。
 * 由 schema 驱动：type=number 且（format=money / author 存单价 / 文案含元费价格）。
 */
export function isArchiveMoneyField(field) {
  const f = field || {}
  if (f.format === 'money' || f.money === true) return true
  if (f.type !== 'number') return false
  const key = String(f.key || '')
  const label = String(f.label || '')
  if (key === 'author') return true
  return /元|费|价|金额|房价|单价|挂号/.test(label)
}

/**
 * 档案标量展示：金额域 0.00 ≠ 空；其它数字 0 ≠ 空；空串/null 才用 empty。
 */
export function formatArchiveScalar(field, value, empty = '—') {
  if (value == null || value === '') return empty
  const f = field || {}
  const type = f.type || 'string'
  if (type === 'number' || isArchiveMoneyField(f)) {
    const n = Number(String(value).replace(/[¥￥,\s]/g, ''))
    if (!Number.isFinite(n)) return String(value)
    if (isArchiveMoneyField(f)) return n.toFixed(2)
    return String(n)
  }
  return String(value)
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
  if (hasTrait('shelfCopy')) {
    return { on: '在架', off: '已下架', verb: '下架', include: '含下架' }
  }
  return { on: '启用', off: '已停用', verb: '停用', include: '含停用' }
}

/** 列表/导出：优先 displayName（后端注入）/ 昵称，否则用户名 */
export function personLabel(row, fallback = '—') {
  if (!row || typeof row !== 'object') return fallback
  const name = (row.displayName || row.nickname || row.username || '').toString().trim()
  return name || fallback
}

export function acceptLevel() {
  return getDelivered().accept || getSchema().accept || 'reject'
}

/** 领域用户资料字段（含公共底座） */
export function profileFields() {
  const list = getSchema().profileFields
  return Array.isArray(list) ? list : []
}

/**
 * 资料受众：user=终端业务用户；staff=总管/子管/业务岗。
 * 领域业务字段（就诊卡、车牌等）默认仅 user。
 */
export function profileAudienceOf(account) {
  if (account && typeof account === 'object') {
    const role = String(account.role || '')
    if (account.superAdmin || account.staffPost || role === 'admin') return 'staff'
    const userId = getSchema()?.roles?.user?.id || 'user'
    if (role === userId || role === 'user' || role === 'patient') return 'user'
    if (role) return 'staff'
    return 'user'
  }
  const role = localStorage.getItem('role') || ''
  const staffPost = localStorage.getItem('staffPost') || ''
  if (role === 'admin' || staffPost) return 'staff'
  const userId = getSchema()?.roles?.user?.id || 'user'
  if (role === userId || role === 'user' || role === 'patient') return 'user'
  return role ? 'staff' : 'user'
}

/** 字段是否对某受众可见（无 forRoles=全员；含 user 仅终端用户） */
export function profileFieldAllowsAudience(f, audience = 'user') {
  if (!f) return false
  const roles = f.forRoles
  if (!Array.isArray(roles) || roles.length === 0) return true
  if (roles.includes('*')) return true
  if (audience === 'staff') {
    return roles.includes('staff') || roles.includes('admin')
  }
  return roles.includes('user') || roles.includes(audience)
}

export function profileFieldsForAudience(audience = 'user') {
  return profileFields().filter((f) => profileFieldAllowsAudience(f, audience))
}

export function profileFieldsOnRegister() {
  return profileFieldsForAudience('user').filter((f) => f && f.onRegister)
}

/** 管理端表格展示的扩展列（跳过已单独展示的姓名/手机等底座）；仅终端用户业务列 */
export function profileAdminColumns(limit = 0) {
  const skip = new Set(['realName', 'phone', 'email', 'gender'])
  const cols = profileFieldsForAudience('user').filter(
    (f) => f && f.storage !== 'phone' && !skip.has(f.key),
  )
  if (limit > 0) return cols.slice(0, limit)
  return cols
}

export function emptyProfileExtras(fields = profileFields()) {
  const o = {}
  for (const f of fields) {
    if (!f?.key || f.storage === 'phone') continue
    o[f.key] = ''
  }
  return o
}

export function hasCap(id) {
  return (getSchema().capabilities || []).includes(id)
}

/** schema.loyalty 块（bake 注入） */
export function loyaltySchema() {
  const L = getSchema().loyalty
  return L && typeof L === 'object' ? L : {}
}

export function isWalletEnabled() {
  return hasCap('wallet') || !!loyaltySchema().wallet?.enabled
}

export function isPointsEnabled() {
  return hasCap('points') || !!loyaltySchema().points?.enabled
}

export function isSpendDiscountEnabled() {
  return hasCap('spend_discount') || !!loyaltySchema().spendDiscount?.enabled
}

export function isMemberTierEnabled() {
  return hasCap('member_tier') || !!loyaltySchema().memberTiers?.enabled
}

export function isCouponEnabled() {
  return hasCap('coupon') || !!loyaltySchema().coupons?.enabled
}

export function isSearchAssistEnabled() {
  return hasCap('search_assist') || !!getSchema()?.search?.suggestEnabled
}

export function searchHotKeywords() {
  const list = getSchema()?.search?.hotKeywords
  return Array.isArray(list) ? list.filter((x) => x && String(x).trim()) : []
}

export function isGalleryEnabled() {
  return hasCap('gallery') || !!(getSchema()?.entities?.archive || {}).galleryEnabled
}

export function isBrowseHistoryEnabled() {
  return hasCap('browse_history')
}

export function anyLoyaltyEnabled() {
  return (
    isWalletEnabled() ||
    isPointsEnabled() ||
    isSpendDiscountEnabled() ||
    isMemberTierEnabled() ||
    isCouponEnabled()
  )
}
