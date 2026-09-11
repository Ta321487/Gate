/**
 * 状态 → 色点 tone（CSS class 后缀），单据/订单/候补等共用，禁止各页复制映射表。
 * tone: pending | progress | ok | danger | muted | warn
 */

const TICKET_TONE = {
  pending: 'pending',
  pending_mid: 'progress',
  pending_final: 'progress',
  waitlisted: 'warn',
  held: 'warn',
  hold_ready: 'ok',
  approved: 'ok',
  rejected: 'danger',
  cancelled: 'muted',
  returned: 'muted',
  overdue: 'danger',
  completed: 'ok',
}

const ORDER_TONE = {
  pending: 'pending',
  confirmed: 'progress',
  shipped: 'progress',
  in_transit: 'progress',
  signed: 'progress',
  completed: 'ok',
  cancelled: 'muted',
}

/** Element Plus tag type 与 tone 对齐的薄映射（已有 el-tag 处可复用） */
const TONE_TO_TAG = {
  pending: 'warning',
  progress: 'info',
  warn: 'warning',
  ok: 'success',
  danger: 'danger',
  muted: 'info',
}

export function ticketTone(status) {
  return TICKET_TONE[status] || 'muted'
}

export function orderTone(status) {
  return ORDER_TONE[status] || 'muted'
}

export function toneToTagType(tone) {
  return TONE_TO_TAG[tone] || 'info'
}

export function ticketTagType(status) {
  return toneToTagType(ticketTone(status))
}

/**
 * 时段余量：可约 / 紧张 / 满
 * @returns {'ok'|'warn'|'full'}
 */
export function slotFillTone(remain, capacity) {
  const r = Number(remain)
  const c = Number(capacity)
  if (!Number.isFinite(r) || r <= 0) return 'full'
  if (Number.isFinite(c) && c > 0 && r / c <= 0.25) return 'warn'
  if (Number.isFinite(c) && c > 0 && r <= 2) return 'warn'
  return 'ok'
}

/**
 * 订单进度步（待付→完成）；返回 { key, label, state: 'done'|'current'|'todo' }[]
 */
export function orderProgressSteps(status, opts = {}) {
  const marketplace = !!opts.marketplace
  const steps = marketplace
    ? [
        { key: 'pending', label: '待付款' },
        { key: 'confirmed', label: '待发货' },
        { key: 'shipped', label: '已发货' },
        { key: 'completed', label: '完成' },
      ]
    : [
        { key: 'pending', label: '待确认' },
        { key: 'confirmed', label: '已确认' },
        { key: 'completed', label: '完成' },
      ]
  const st = String(status || '')
  if (st === 'cancelled') {
    return steps.map((s) => ({ ...s, state: 'todo' }))
  }
  const orderKeys = steps.map((s) => s.key)
  let idx = orderKeys.indexOf(st)
  if (st === 'shipped' || st === 'in_transit' || st === 'signed') {
    idx = orderKeys.indexOf('shipped')
    if (idx < 0) idx = orderKeys.indexOf('confirmed')
  }
  if (idx < 0 && st === 'completed') idx = steps.length - 1
  if (idx < 0) idx = 0
  return steps.map((s, i) => ({
    ...s,
    state: i < idx ? 'done' : i === idx ? 'current' : 'todo',
  }))
}

/** 站内信 refType → 小图标字符（演示用，非 emoji 商店） */
export function messageKindMark(refType) {
  const t = String(refType || '')
  if (t === 'ticket') return '审'
  if (t === 'order') return '订'
  if (t === 'reservation') return '约'
  if (t === 'exam') return '考'
  return '通'
}

/** 多级审批简易 steps（初/复/终） */
export function multiApproveSteps(status) {
  const steps = [
    { key: 'pending', label: '初审' },
    { key: 'pending_mid', label: '复审' },
    { key: 'pending_final', label: '终审' },
    { key: 'approved', label: '通过' },
  ]
  const st = String(status || '')
  if (st === 'rejected' || st === 'cancelled') {
    return steps.map((s) => ({ ...s, state: 'todo' }))
  }
  const order = ['pending', 'pending_mid', 'pending_final', 'approved']
  let idx = order.indexOf(st)
  if (st === 'returned' || st === 'completed' || st === 'overdue') idx = 3
  if (idx < 0) idx = 0
  return steps.map((s, i) => ({
    ...s,
    state: i < idx ? 'done' : i === idx ? 'current' : 'todo',
  }))
}

/** 会员等级色条 tone */
export function memberTierTone(tierOrLabel) {
  const s = String(tierOrLabel || '').toLowerCase()
  if (/金|gold|vip3|diamond|钻/.test(s)) return 'ok'
  if (/银|silver|vip2/.test(s)) return 'progress'
  if (/铜|bronze|vip1/.test(s)) return 'warn'
  return 'muted'
}

/** 进销存 moveType → tone */
export function stockMoveTone(moveType) {
  const t = String(moveType || '')
  if (t === 'in' || t === 'count_gain') return 'ok'
  if (t === 'out' || t === 'scrap' || t === 'count_loss') return 'danger'
  if (t === 'count') return 'progress'
  return 'muted'
}

/** 审计动作粗分色 */
export function auditActionTone(action) {
  const a = String(action || '').toLowerCase()
  if (/delete|remove|reject|ban|mute/.test(a)) return 'danger'
  if (/create|add|insert|approve|pass/.test(a)) return 'ok'
  if (/update|edit|patch|assign/.test(a)) return 'progress'
  return 'muted'
}

/** 进度节点图标字（接单/完工等） */
export function progressNodeMark(status) {
  const s = String(status || '')
  if (s === 'pending' || s === 'created' || s === 'submitted') return '接'
  if (s === 'approved' || s === 'accepted' || s === 'assigned') return '受'
  if (s === 'returned' || s === 'completed' || s === 'done' || s === 'finished') return '完'
  if (s === 'rejected' || s === 'cancelled') return '驳'
  if (s === 'overdue') return '催'
  return '记'
}

/** 文件 URL / 名 → 类型字标 */
export function fileTypeMark(urlOrName) {
  const s = String(urlOrName || '').split('?')[0].toLowerCase()
  const m = s.match(/\.([a-z0-9]{1,5})$/)
  const ext = m ? m[1] : ''
  if (['pdf'].includes(ext)) return 'PDF'
  if (['doc', 'docx'].includes(ext)) return 'DOC'
  if (['xls', 'xlsx', 'csv'].includes(ext)) return '表'
  if (['ppt', 'pptx'].includes(ext)) return 'PPT'
  if (['png', 'jpg', 'jpeg', 'gif', 'webp'].includes(ext)) return '图'
  if (['zip', 'rar', '7z'].includes(ext)) return '包'
  if (['mp4', 'avi', 'mov'].includes(ext)) return '视'
  if (['mp3', 'wav'].includes(ext)) return '音'
  return ext ? ext.slice(0, 3).toUpperCase() : '件'
}

/** BookSuggest / 通用审批状态 → el-tag type */
export function suggestStatusTagType(status) {
  return toneToTagType(
    ({ pending: 'pending', approved: 'ok', rejected: 'danger' }[status] || 'muted'),
  )
}
