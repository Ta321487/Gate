/** 本地日历日 YYYY-MM-DD（避免 toISOString 的 UTC 错日） */
export function todayStr(d = new Date()) {
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}
