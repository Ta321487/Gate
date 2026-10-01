/** 运行态展示纯函数（无副作用）。 */

export function runtimeStatusLabel(st) {
  return ({
    stopped: '已停止',
    starting: '启动中',
    stopping: '停止中',
    healthy: '正常',
    error: '异常',
  })[st] || st || '已停止'
}

export function runtimeStatusPill(st) {
  return ({
    stopped: 'pill-neutral',
    starting: 'pill-amber',
    stopping: 'pill-amber',
    healthy: 'pill-green',
    error: 'pill-red',
  })[st] || 'pill-neutral'
}

export function runtimeCanStop(st) {
  return st === 'healthy' || st === 'starting' || st === 'stopping'
}

export function runtimeTransient(st) {
  return st === 'starting' || st === 'stopping'
}

/** 状态只在 pill；这里只展示真实日志，占位文案一律收成 — */
export function runtimeLogView(st, tail) {
  if (st === 'stopping') return '—'
  // 编译/启动失败后进程常已退出；若仍当 stopped 藏日志，工作台只剩「—」
  if (st === 'stopped') {
    if (tail && _runtimeLogLooksFailed(tail)) return _tailLines(tail, 24)
    return '—'
  }
  if (!tail || /^(后端|前端)?(启动|停止)中/.test(String(tail).trim())) return '—'
  return _tailLines(tail, st === 'error' ? 24 : 8)
}

export function _runtimeLogLooksFailed(tail) {
  const t = String(tail)
  return (
    /BUILD FAILURE|COMPILATION ERROR|Failed to execute goal|ERROR (?:start|ensure)|APPLICATION FAILED TO START|npm ERR!|npm install FAILED|Could not resolve/.test(
      t,
    )
  )
}

export function _tailLines(tail, keep) {
  const lines = String(tail).split(/\r?\n/).filter((l) => l.trim())
  return lines.slice(-keep).join('\n') || '—'
}

export function formatSize(n) {
  if (!n) return '—'
  if (n < 1024) return n + ' B'
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + ' KB'
  return (n / 1024 / 1024).toFixed(1) + ' MB'
}
