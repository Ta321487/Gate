/** 运营端共享：状态文案、默认 Tab、catalog 缓存、面包屑、debounce —— 避免各页各写一份 */

import { ref } from 'vue'
import { api } from './api'

/** 详情页面包屑标题（App.vue 读取） */
export const detailCrumb = ref('')

export const PROJECT_STATUS = {
  needs_confirm: { label: '待确认匹配', pill: 'pill-amber', tag: 'warning' },
  ready: { label: '待生成', pill: 'pill-teal', tag: 'info' },
  generating: { label: '生成中', pill: 'pill-teal', tag: 'info' },
  generated: { label: '已生成 · 可交付', pill: 'pill-green', tag: 'success' },
  failed: { label: '门禁未过 · 禁止交付', pill: 'pill-red', tag: 'error' },
  running: { label: '运行中', pill: 'pill-green', tag: 'success' },
  archived: { label: '已归档', pill: 'pill-neutral', tag: 'default' },
}

export function projectStatusLabel(status) {
  return PROJECT_STATUS[status]?.label || status || '—'
}

export function projectStatusPill(status) {
  return PROJECT_STATUS[status]?.pill || 'pill-neutral'
}

export function projectStatusTag(status) {
  return PROJECT_STATUS[status]?.tag || 'default'
}

/** 进入详情时默认 Tab（与 pane name 对齐） */
export function defaultTabForStatus(status) {
  switch (status) {
    case 'needs_confirm':
      return 'match'
    case 'ready':
    case 'generating':
      return 'generate'
    case 'failed':
      return 'artifacts'
    case 'generated':
    case 'running':
      return 'runtime'
    default:
      return 'match'
  }
}

export const CHECKLIST_RESULT = {
  done: { label: '已实现', type: 'success' },
  out_of_mvp: { label: '砍项', type: 'default' },
  pending: { label: '未覆盖', type: 'error' },
}

export const LOG_SIDES = [
  { id: 'job', label: '任务' },
  { id: 'backend', label: '后端' },
  { id: 'frontend', label: '前端' },
  { id: 'deepseek', label: 'DeepSeek' },
]

let _catalogPromise = null

/** 全页共用一份 catalog，避免轮询/多页重复拉取 */
export function getCatalog() {
  if (!_catalogPromise) {
    _catalogPromise = api.catalog().catch((err) => {
      _catalogPromise = null
      throw err
    })
  }
  return _catalogPromise
}

export function catalogLabel(list, id) {
  const hit = (list || []).find((x) => x.id === id)
  return hit?.label || id || '—'
}

export function formatArchDom(catalog, archetype, domain) {
  if (!archetype && !domain) return '—'
  const a = catalogLabel(catalog?.archetypes, archetype)
  const d = catalogLabel(catalog?.domains, domain)
  return `${a} · ${d}`
}

/** 面板标题栏刷新按钮约定：panel-hd 右侧 · size="small"（勿用 tiny/quaternary） */
export const PANEL_REFRESH = { size: 'small' }

/** 默认本月 00:00 → 现在，供 datetimerange */
export function monthRangeMs(now = Date.now()) {
  const end = new Date(now)
  const start = new Date(end.getFullYear(), end.getMonth(), 1, 0, 0, 0, 0)
  return [start.getTime(), end.getTime()]
}

function toLocalIso(ms) {
  const d = new Date(ms)
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`
}

/** 本地时间 ISO，避免 toISOString 变 UTC 导致筛选偏移 */
export function rangeToParams(range) {
  if (!range || range.length !== 2 || range[0] == null || range[1] == null) return {}
  return {
    date_from: toLocalIso(range[0]),
    date_to: toLocalIso(range[1]),
  }
}

export const dateRangeShortcuts = {
  本月: () => monthRangeMs(),
  近7天: () => {
    const end = Date.now()
    return [end - 7 * 86400000, end]
  },
  近30天: () => {
    const end = Date.now()
    return [end - 30 * 86400000, end]
  },
}

export function debounce(fn, ms = 300) {
  let t = null
  const wrapped = (...args) => {
    clearTimeout(t)
    t = setTimeout(() => fn(...args), ms)
  }
  wrapped.cancel = () => clearTimeout(t)
  return wrapped
}
