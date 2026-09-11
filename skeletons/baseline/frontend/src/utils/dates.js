/** 本地日历日 YYYY-MM-DD（避免 toISOString 的 UTC 错日） */
export function todayStr(d = new Date()) {
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

/** 宽松解析后端时间戳为毫秒；失败返回 null */
export function parseDateMs(raw) {
  if (raw == null || raw === '') return null
  if (typeof raw === 'number' && Number.isFinite(raw)) return raw
  const s = String(raw).trim().replace('T', ' ').replace(/-/g, '/')
  const t = Date.parse(s)
  return Number.isFinite(t) ? t : null
}

/**
 * 相对时间文案（演示沉浸用）。
 * @param {string|number|Date|null|undefined} raw
 * @param {number} [nowMs]
 */
export function formatRelative(raw, nowMs = Date.now()) {
  const t = raw instanceof Date ? raw.getTime() : parseDateMs(raw)
  if (t == null) return '—'
  const diff = Math.floor((nowMs - t) / 1000)
  if (diff < 0) {
    const ahead = -diff
    if (ahead < 60) return '即将'
    if (ahead < 3600) return `${Math.floor(ahead / 60)} 分钟后`
    if (ahead < 86400) return `${Math.floor(ahead / 3600)} 小时后`
    return `${Math.floor(ahead / 86400)} 天后`
  }
  if (diff < 45) return '刚刚'
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`
  if (diff < 86400 * 7) return `${Math.floor(diff / 86400)} 天前`
  const d = new Date(t)
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

/** 秒 → mm:ss / hh:mm:ss */
export function formatMmSs(totalSec) {
  const sec = Math.max(0, Math.floor(Number(totalSec) || 0))
  const h = Math.floor(sec / 3600)
  const m = Math.floor((sec % 3600) / 60)
  const s = sec % 60
  const p = (n) => String(n).padStart(2, '0')
  if (h > 0) return `${p(h)}:${p(m)}:${p(s)}`
  return `${p(m)}:${p(s)}`
}
