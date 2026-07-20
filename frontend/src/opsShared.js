/** 运营端共享：状态文案、默认 Tab、catalog 缓存、面包屑、debounce —— 避免各页各写一份 */

import { h, ref } from 'vue'
import { api } from './api'

/** 详情页面包屑标题（App.vue 读取） */
export const detailCrumb = ref('')

/**
 * 状态徽章统一用 `.pill`（页头 / panel-hd / 表格单元格同一套）。
 * `tag` 仅作 Naive 兼容映射，新代码请用 pill。
 */
export const PROJECT_STATUS = {
  needs_confirm: { label: '待确认匹配', pill: 'pill-amber', tag: 'warning' },
  ready: { label: '待生成', pill: 'pill-teal', tag: 'info' },
  generating: { label: '生成中', pill: 'pill-teal', tag: 'info' },
  generated: { label: '已生成 · 可交付', pill: 'pill-green', tag: 'success' },
  failed: { label: '质量检查未过 · 暂不可交付', pill: 'pill-red', tag: 'error' },
  // running = 预览已拉起；文案与 generated 同族，「运行中」只出现在「运行」列
  running: { label: '已生成 · 可交付', pill: 'pill-green', tag: 'success' },
  archived: { label: '已归档', pill: 'pill-neutral', tag: 'default' },
}

/** 表格 render 用：`h('span', { class: ['pill', …] }, label)` */
export function statusPillNode(label, pillClass = 'pill-neutral') {
  return h('span', { class: ['pill', pillClass] }, label || '—')
}

export function projectStatusLabel(status, opts = {}) {
  const zipReady = opts.zipReady
  if (
    (status === 'generated' || status === 'running')
    && zipReady === false
  ) {
    return '已生成 · 质量检查未过'
  }
  return PROJECT_STATUS[status]?.label || status || '—'
}

export function projectStatusPill(status, opts = {}) {
  const zipReady = opts.zipReady
  if (
    (status === 'generated' || status === 'running')
    && zipReady === false
  ) {
    return 'pill-amber'
  }
  return PROJECT_STATUS[status]?.pill || 'pill-neutral'
}

export function projectStatusTag(status, opts = {}) {
  const zipReady = opts.zipReady
  if (
    (status === 'generated' || status === 'running')
    && zipReady === false
  ) {
    return 'warning'
  }
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
  done: { label: '已实现', type: 'success', pill: 'pill-green' },
  out_of_mvp: { label: '本期不做', type: 'default', pill: 'pill-neutral' },
  pending: { label: '未覆盖', type: 'error', pill: 'pill-red' },
}

export const JOB_STATUS = {
  queued: { label: '排队', pill: 'pill-neutral' },
  running: { label: '运行中', pill: 'pill-teal' },
  success: { label: '成功', pill: 'pill-green' },
  failed: { label: '失败', pill: 'pill-red' },
  cancelled: { label: '已取消', pill: 'pill-neutral' },
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

/**
 * 面板约定：
 * - 状态徽章一律 `.pill`（见 statusPillNode）
 * - panel-hd 刷新 / 工具栏按钮 size="small"（勿用 tiny/quaternary）
 * - size="large" 仅用于匹配确认 / 一键生成主 CTA
 * - confirm() = 是/否；n-modal dialog = 需额外字段的危险操作；n-modal card = 查看器
 */
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
