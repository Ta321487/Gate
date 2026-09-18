/** 门户顶栏 / 管理侧栏：项多时的呈现切分（不改菜单集合）。 */

export const PORTAL_NAV_INLINE_MAX = 6
export const PORTAL_NAV_INLINE_KEEP = 5
export const ADMIN_ASIDE_DENSE_AT = 9

/**
 * 登录后顶栏：≤6 全直出；>6 前 5 直出，其余进「更多」。顺序不变。
 * @param {Array<{to?: string, label?: string}>} items
 */
export function splitPortalNav(items) {
  const list = Array.isArray(items) ? items.filter(Boolean) : []
  if (list.length <= PORTAL_NAV_INLINE_MAX) {
    return { primary: list.slice(), more: [] }
  }
  return {
    primary: list.slice(0, PORTAL_NAV_INLINE_KEEP),
    more: list.slice(PORTAL_NAV_INLINE_KEEP),
  }
}

/** 当前路由是否落在该菜单路径（含子路径；根路径只精确匹配）。 */
export function navItemActive(path, to) {
  const p = String(path || '')
  const t = String(to || '')
  if (!p || !t) return false
  if (p === t) return true
  if (t !== '/' && (p.startsWith(`${t}/`) || p.startsWith(`${t}?`))) return true
  return false
}

/** 管理侧栏可见项（含个人资料）≥9 时略收密度。 */
export function adminAsideDense(visibleCount) {
  const n = Number(visibleCount)
  return Number.isFinite(n) && n >= ADMIN_ASIDE_DENSE_AT
}
