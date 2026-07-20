/**
 * 站内消息导航：铃铛 / 消息页共用，避免两处各写一份 refType 映射。
 */

/** 当前壳下的收件箱路径 */
export function messageInboxPath(pathname = '') {
  if (String(pathname).startsWith('/admin')) return '/admin/messages'
  if (String(pathname).startsWith('/staff')) return '/staff/messages'
  return '/messages'
}

/**
 * 管理端点击消息时的跳转目标。
 * @param {{ refType?: string }|null|undefined} msg
 * @param {string} pathname 当前路由 path
 * @param {{ fallback?: boolean }} [opts] fallback=true 时无匹配也回消息页（铃铛用）
 * @returns {string|null}
 */
export function messageAdminTarget(msg, pathname = '', opts = {}) {
  const path = String(pathname || '')
  if (!path.startsWith('/admin') && !path.startsWith('/staff')) return null
  const t = msg?.refType
  if (t === 'ticket') return '/admin/tickets'
  if (t === 'order') return '/admin/orders'
  if (t === 'reservation') return '/admin/reservations'
  return opts.fallback ? '/admin/messages' : null
}
