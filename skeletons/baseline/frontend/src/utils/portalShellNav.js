/**
 * 门户壳导航摆法（§3 + 真实产品）。
 *
 * 菜单集合/顺序 = 开题 schemaMenus。
 * 顶栏只放业务主路径；账户类进头像账户短页（文案跟 accountFace，禁笼统「我的」当功能篓）；
 * 交易 marketplace 次要进右侧栏。
 * 不做顶栏「更多」垃圾桶（对标站与 Ant 顶栏均无此模式）。
 */

import { APP_DELIVERED } from '../appDelivered.js'

/** 顶栏业务链软上限（Ant 顶栏约 2～7；§3 约四五）。超出仅 marketplace 收进右侧栏 */
export const PRIMARY_MAX = 5
export const RAIL_OUTSIDE_MAX = 5
/** 首次无本机偏好时外侧只钉这么多，其余进「更多」，避免编辑弹层与外侧同表 */
export const RAIL_OUTSIDE_DEFAULT = 3
export const RAIL_STORAGE_KEY = 'gf_shop_side_rail'

/** 右侧栏短签（禁「我的收藏/我的评价」都截成「我的」） */
export const RAIL_SHORT_LABEL = {
  favorites: '收藏',
  order_reviews: '评价',
  addresses: '收货',
  guestbook: '留言',
  dm: '客服',
  browse_history: '足迹',
  coupons: '优惠',
  points_ledger: '积分',
  points_rules: '规则',
  blind_draws: '盲盒',
  my_consigns: '寄卖',
  my_buybacks: '回收',
  my_digital: '卡密',
  balance_mine: '余额',
  balance_ledger_mine: '流水',
}

/**
 * 侧栏二字签：优先键表；去掉「我的」前缀再截，避免重名。
 * @param {string} label
 * @param {string} [key]
 */
export function railShortLabel(label, key = '') {
  const mapped = RAIL_SHORT_LABEL[String(key || '')]
  if (mapped) return mapped
  let s = String(label || '').trim()
  if (s.startsWith('我的')) s = s.slice(2)
  if (!s) s = String(label || '').trim()
  return s.length <= 2 ? s : s.slice(0, 2)
}

const CHROME_ALWAYS = new Set(['messages', 'profile', 'home', 'ai_assistant'])

/**
 * 账户·个人向（开题挂了才出）：进账户短页 / 市集右侧栏。
 * 头像下拉只留「账户短页入口 / 资料 / 退出」，禁止把本集合平铺成长下拉。
 * 借阅单、工单、排片、试卷等业务链不进此集合。
 */
export const ACCOUNT_KEYS = new Set([
  'favorites',
  'addresses',
  'browse_history',
  'dm',
  'guestbook',
  'order_reviews',
  'coupons',
  'points_ledger',
  'points_rules',
  'blind_draws',
  'my_consigns',
  'my_buybacks',
  'my_digital',
  'balance_mine',
  'balance_ledger_mine',
  'doc_mine',
  'my_archive',
  'tb_account',
  'e_sign_mine',
  'patient_profile',
  'parking_pass',
  'reserve_blacklist_appeal',
])

/** 「我的」短页分组（只摆已挂入口；空组不渲染） */
export const ACCOUNT_HUB_GROUPS = [
  {
    id: 'daily',
    title: '常用',
    keys: ['favorites', 'addresses', 'browse_history', 'dm', 'guestbook', 'order_reviews'],
  },
  {
    id: 'assets',
    title: '资产与优惠',
    keys: [
      'coupons',
      'points_ledger',
      'points_rules',
      'blind_draws',
      'balance_mine',
      'balance_ledger_mine',
      'my_consigns',
      'my_buybacks',
      'my_digital',
    ],
  },
  {
    id: 'other',
    title: '其他',
    keys: [
      'doc_mine',
      'my_archive',
      'tb_account',
      'e_sign_mine',
      'patient_profile',
      'parking_pass',
      'reserve_blacklist_appeal',
    ],
  },
]

/**
 * 从开题菜单抽出账户向入口（保持相对顺序），供「我的」短页。
 * @param {Array<{ key: string, to?: string, label?: string }>} menuItems
 */
export function collectAccountHubItems(menuItems) {
  const list = Array.isArray(menuItems) ? menuItems.filter((m) => m && m.key && m.to) : []
  return list.filter((m) => ACCOUNT_KEYS.has(m.key))
}

/**
 * @param {Array<{ key: string, to?: string, label?: string }>} hubItems
 * @returns {Array<{ id: string, title: string, items: typeof hubItems }>}
 */
export function groupAccountHubItems(hubItems) {
  const list = Array.isArray(hubItems) ? hubItems.filter(Boolean) : []
  const byKey = new Map(list.map((it) => [it.key, it]))
  const used = new Set()
  const groups = []
  for (const g of ACCOUNT_HUB_GROUPS) {
    const items = []
    for (const k of g.keys) {
      const hit = byKey.get(k)
      if (hit && !used.has(k)) {
        items.push(hit)
        used.add(k)
      }
    }
    if (items.length) groups.push({ id: g.id, title: g.title, items })
  }
  const rest = list.filter((it) => !used.has(it.key))
  if (rest.length) {
    const other = groups.find((g) => g.id === 'other')
    if (other) other.items.push(...rest)
    else groups.push({ id: 'other', title: '其他', items: rest })
  }
  return groups
}

export function domainGroupFromDelivered(delivered = APP_DELIVERED) {
  const g = String(delivered?.domainGroup || '').trim()
  if (g) return g
  // 旧包兜底：只认构图键，禁止 DOM-* 业务分支
  const trade = String(delivered?.tradeSurfaceStyle || '').trim()
  if (trade === 'shelfgrid' || trade === 'menuboard' || trade === 'showtime') return 'trade'
  return 'fallback'
}

/** @returns {'marketplace'|'storefront'} */
export function shellNavStyleFromDelivered(delivered = APP_DELIVERED) {
  const s = String(delivered?.shellNavStyle || '').trim().toLowerCase()
  if (s === 'marketplace' || s === 'storefront') return s
  return 'storefront'
}

/**
 * 个人中心 /「我的」脸：按域组+软皮换构图（从头到脚像另一系统）。
 * 功能入口仍只跟开题 schemaMenus / profileFields，本键不增删能力。
 */
export function accountFaceFromDelivered(delivered = APP_DELIVERED) {
  const group = domainGroupFromDelivered(delivered)
  const style = shellNavStyleFromDelivered(delivered)
  const trade = String(delivered?.tradeSurfaceStyle || '').trim()
  if (group === 'trade') {
    if (style === 'marketplace') return 'stall'
    if (trade === 'showtime') return 'showcard'
    return 'member'
  }
  const map = {
    borrow: 'reader',
    content: 'desk',
    ticket: 'service',
    approve: 'inbox',
    reserve: 'booking',
    apply: 'event',
    follow: 'crm',
    interact: 'record',
  }
  return map[group] || 'plain'
}

/** 脸对应的短文案（标题/导语）；须学生可见口语，禁工厂腔 */
export function accountFaceCopy(face) {
  const f = String(face || 'plain')
  const table = {
    stall: { title: '我的账户', lead: '收藏、地址和优惠相关入口都在这里。' },
    member: { title: '会员中心', lead: '收藏、优惠和资料入口都在这里。' },
    showcard: { title: '我的观影', lead: '资料与安全设置；订票相关入口也在下面。' },
    reader: { title: '借阅证', lead: '资料与借阅相关入口都在这里。' },
    desk: { title: '我的书桌', lead: '收藏和文稿入口在下面。' },
    service: { title: '服务台', lead: '联系方式、安全设置与工单相关入口都在这里。' },
    inbox: { title: '办公设置', lead: '资料、安全与待办相关入口都在这里。' },
    booking: { title: '预约设置', lead: '资料与预约相关入口都在这里。' },
    event: { title: '活动设置', lead: '报名资料与活动相关入口都在这里。' },
    crm: { title: '我的档案', lead: '联系人资料与相关入口都在这里。' },
    record: { title: '学习档案', lead: '资料与试卷错题相关入口都在这里。' },
    plain: { title: '账户中心', lead: '资料与账户相关入口都在这里。' },
  }
  return table[f] || table.plain
}

/**
 * 顶栏/头像入口文案：与账户短页标题一致，禁止笼统「我的」冒充整站功能篓。
 * @returns {string}
 */
export function accountChromeLabel(face) {
  return accountFaceCopy(face).title
}

/** 进 /profile 的统一叫法（顶栏下拉、账户短页链、资料页标题同词） */
export const PROFILE_ENTRY_LABEL = '个人资料'

export function profilePageCopy() {
  return {
    title: PROFILE_ENTRY_LABEL,
    lead: '改昵称、头像和安全设置。',
  }
}

export function shellModeFromDelivered(delivered = APP_DELIVERED) {
  const trade = String(delivered?.tradeSurfaceStyle || '').trim()
  if (trade === 'shelfgrid') return 'shop'
  if (trade === 'menuboard') return 'food'
  if (trade === 'showtime') return 'cinema'
  return domainGroupFromDelivered(delivered)
}

export function cartUsesChromeBadge(modeOrGroup, navStyle = 'storefront', delivered = APP_DELIVERED) {
  const group = domainGroupFromDelivered(delivered)
  if (group !== 'trade' && modeOrGroup !== 'shop' && modeOrGroup !== 'food') return false
  const trade = String(delivered?.tradeSurfaceStyle || '').trim()
  if (trade === 'showtime' || modeOrGroup === 'cinema') return false
  if (trade === 'menuboard' || modeOrGroup === 'food') return true
  const style = navStyle === 'marketplace' || navStyle === 'storefront'
    ? navStyle
    : shellNavStyleFromDelivered(delivered)
  return style !== 'marketplace'
}

/**
 * @param {Array<{ key: string, to?: string, label?: string }>} menuItems
 * @returns {{ primary: typeof menuItems, account: typeof menuItems, sideRail: typeof menuItems }}
 */
export function classifyPortalMenus(
  menuItems,
  _mode = 'generic',
  navStyle = 'storefront',
  delivered = APP_DELIVERED,
) {
  const raw = Array.isArray(menuItems) ? menuItems.filter((m) => m && m.key && m.to) : []
  if (!raw.length) return { primary: [], account: [], sideRail: [] }

  const style = navStyle === 'marketplace' || navStyle === 'storefront'
    ? navStyle
    : shellNavStyleFromDelivered(delivered)
  const group = domainGroupFromDelivered(delivered)
  const cartBadge = cartUsesChromeBadge(_mode, style, delivered)

  const chromeSkip = new Set(CHROME_ALWAYS)
  if (cartBadge) chromeSkip.add('cart')

  const list = raw.filter((m) => !chromeSkip.has(m.key))
  const business = []
  const accountish = []
  for (const m of list) {
    if (ACCOUNT_KEYS.has(m.key)) accountish.push(m)
    else business.push(m)
  }

  const useRail = style === 'marketplace' && group === 'trade'

  if (useRail) {
    // 市集：顶栏短业务链；账户类 + 超额业务进右侧栏（对标淘宝式工具条，不是「更多」）
    return {
      primary: business.slice(0, PRIMARY_MAX),
      account: [],
      sideRail: [...accountish, ...business.slice(PRIMARY_MAX)],
    }
  }

  // 店面/其它组：业务全在顶栏（毕设开题通常 ≤5；多也不造「更多」）；账户进头像
  return {
    primary: business,
    account: accountish,
    sideRail: [],
  }
}

export function loadRailPreference() {
  try {
    const raw = localStorage.getItem(RAIL_STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (!parsed || typeof parsed !== 'object') return null
    return {
      order: Array.isArray(parsed.order) ? parsed.order.map(String) : [],
      outside: Array.isArray(parsed.outside) ? parsed.outside.map(String) : [],
    }
  } catch {
    return null
  }
}

export function saveRailPreference(pref) {
  try {
    localStorage.setItem(
      RAIL_STORAGE_KEY,
      JSON.stringify({
        order: Array.isArray(pref?.order) ? pref.order.map(String) : [],
        outside: Array.isArray(pref?.outside) ? pref.outside.map(String) : [],
      }),
    )
  } catch {
    /* ignore */
  }
}

export function arrangeSideRail(items, pref = null) {
  const list = Array.isArray(items) ? items.filter(Boolean) : []
  if (!list.length) return { outside: [], more: [], order: [], outsideKeys: [] }

  const byKey = new Map(list.map((it) => [it.key, it]))
  const ordered = []
  const seen = new Set()
  for (const k of pref?.order || []) {
    const hit = byKey.get(k)
    if (hit && !seen.has(k)) {
      ordered.push(hit)
      seen.add(k)
    }
  }
  for (const it of list) {
    if (!seen.has(it.key)) ordered.push(it)
  }

  // 已保存过 outside（含「只勾 2 个」）→ 严格按勾选，禁止再自动补满
  const hasOutsidePref = Array.isArray(pref?.outside)
  let outsideKeys
  if (hasOutsidePref) {
    outsideKeys = pref.outside.filter((k) => byKey.has(k)).slice(0, RAIL_OUTSIDE_MAX)
  } else {
    // 未满铺：默认外侧 3，其余进更多（对齐手磨 Dock 内外分层）
    const n = Math.min(RAIL_OUTSIDE_DEFAULT, RAIL_OUTSIDE_MAX, ordered.length)
    outsideKeys = ordered.slice(0, n).map((it) => it.key)
  }

  const outsideSet = new Set(outsideKeys)
  return {
    // 外侧顺序跟勾选顺序（编辑里上下移），不是整表 filter 打乱
    outside: outsideKeys.map((k) => byKey.get(k)).filter(Boolean),
    more: ordered.filter((it) => !outsideSet.has(it.key)),
    order: ordered.map((it) => it.key),
    outsideKeys,
  }
}
