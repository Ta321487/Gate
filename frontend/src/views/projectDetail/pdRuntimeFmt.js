/** 运行态展示纯函数（无副作用）。 */

/**
 * 运行页 LongOpWait 文案：按 side+action 区分；无操作记录时用前后端过渡态推断。
 * @param {{ side?: string, action?: string, beStatus?: string, feStatus?: string }} opts
 * @returns {{ title: string, phases: {key:string,label:string}[], hint: string }}
 */
export function resolveRuntimeWaitCopy(opts = {}) {
  const side = String(opts.side || '')
  const action = String(opts.action || '')
  const be = String(opts.beStatus || '')
  const fe = String(opts.feStatus || '')
  const key = _runtimeWaitOpKey(side, action) || _runtimeWaitInferKey(be, fe)
  return RUNTIME_WAIT_COPY[key] || RUNTIME_WAIT_COPY.mixed
}

const RUNTIME_WAIT_COPY = {
  'all:start': {
    title: '正在启动前后端…',
    phases: [
      { key: 'req', label: '已提交启动请求' },
      { key: 'boot', label: '正在拉起后端与前端进程' },
      { key: 'ready', label: '等待前后端可访问' },
    ],
    hint: '前后端启动中，状态会自动刷新；可停在本页，勿重复点启动。',
  },
  'all:stop': {
    title: '正在停止前后端…',
    phases: [
      { key: 'req', label: '已提交停止请求' },
      { key: 'boot', label: '正在停止后端与前端进程' },
      { key: 'ready', label: '等待前后端完全停止' },
    ],
    hint: '前后端停止中，状态会自动刷新；可停在本页，勿重复点停止。',
  },
  'all:restart': {
    title: '正在重启前后端…',
    phases: [
      { key: 'req', label: '已提交重启请求' },
      { key: 'boot', label: '先停再起后端与前端' },
      { key: 'ready', label: '等待前后端再次可访问' },
    ],
    hint: '前后端重启中，状态会自动刷新；可停在本页，勿重复点重启。',
  },
  'backend:start': {
    title: '正在启动后端…',
    phases: [
      { key: 'req', label: '已提交后端启动请求' },
      { key: 'boot', label: '正在拉起后端进程' },
      { key: 'ready', label: '等待后端可访问' },
    ],
    hint: '后端启动中，状态会自动刷新；可停在本页，勿重复点启动。',
  },
  'backend:stop': {
    title: '正在停止后端…',
    phases: [
      { key: 'req', label: '已提交后端停止请求' },
      { key: 'boot', label: '正在停止后端进程' },
      { key: 'ready', label: '等待后端完全停止' },
    ],
    hint: '后端停止中，状态会自动刷新；可停在本页，勿重复点停止。',
  },
  'frontend:start': {
    title: '正在启动前端…',
    phases: [
      { key: 'req', label: '已提交前端启动请求' },
      { key: 'boot', label: '正在拉起前端进程' },
      { key: 'ready', label: '等待前端可访问' },
    ],
    hint: '前端启动中，状态会自动刷新；可停在本页，勿重复点启动。',
  },
  'frontend:stop': {
    title: '正在停止前端…',
    phases: [
      { key: 'req', label: '已提交前端停止请求' },
      { key: 'boot', label: '正在停止前端进程' },
      { key: 'ready', label: '等待前端完全停止' },
    ],
    hint: '前端停止中，状态会自动刷新；可停在本页，勿重复点停止。',
  },
  mixed: {
    title: '运行态切换中…',
    phases: [
      { key: 'req', label: '已提交运行态切换请求' },
      { key: 'boot', label: '正在切换前后端进程' },
      { key: 'ready', label: '等待运行态稳定' },
    ],
    hint: '运行态切换中，状态会自动刷新；可停在本页，勿重复点击。',
  },
}

function _runtimeWaitOpKey(side, action) {
  if (!side || !action) return ''
  if (side === 'all' && (action === 'start' || action === 'stop' || action === 'restart')) {
    return `all:${action}`
  }
  if ((side === 'backend' || side === 'frontend') && (action === 'start' || action === 'stop')) {
    return `${side}:${action}`
  }
  return ''
}

function _runtimeWaitInferKey(be, fe) {
  const beStart = be === 'starting'
  const beStop = be === 'stopping'
  const feStart = fe === 'starting'
  const feStop = fe === 'stopping'
  if (beStart && feStart) return 'all:start'
  if (beStop && feStop) return 'all:stop'
  if (beStart && !feStart && !feStop) return 'backend:start'
  if (beStop && !feStart && !feStop) return 'backend:stop'
  if (feStart && !beStart && !beStop) return 'frontend:start'
  if (feStop && !beStart && !beStop) return 'frontend:stop'
  if (beStart || beStop || feStart || feStop) return 'mixed'
  return ''
}

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
  if (st === 'stopping') return '正在停止…'
  // 编译/启动失败后进程常已退出；若仍当 stopped 藏日志，工作台只剩「—」
  if (st === 'stopped') {
    if (tail && _runtimeLogLooksFailed(tail)) return _tailLines(tail, 24)
    return '—'
  }
  const startingHint =
    '编译启动中，日志可能短暂无新输出；就绪后会自动变为「正常」，无需刷新页面。'
  if (!tail || /^(后端|前端)?(启动|停止)中/.test(String(tail).trim())) {
    return st === 'starting' ? startingHint : '—'
  }
  const keep = st === 'error' ? 24 : st === 'starting' ? 20 : 8
  const body = _tailLines(tail, keep)
  if (st === 'starting') return `${body}\n\n（${startingHint}）`
  return body
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
