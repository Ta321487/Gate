/**
 * 详情阶段机——毕设顺序：材料 → 匹配 → 生成 → 论文材料 → 答辩 PPT → 质检交付。
 * 预览 / 日志为轨旁链，不占主步序号。
 */

import { readinessIsDownloadable } from './deliveryReadiness.js'

/** 主路径阶段（预览/日志见详情旁链） */
export const DELIVERY_STAGE_DEFS = [
  { key: 'materials', label: '材料', tab: 'materials' },
  { key: 'match', label: '匹配', tab: 'match' },
  { key: 'generate', label: '生成', tab: 'generate' },
  { key: 'thesis', label: '论文材料', tab: 'thesis' },
  { key: 'ppt', label: '答辩 PPT', tab: 'ppt' },
  { key: 'delivery', label: '质检交付', tab: 'artifacts' },
]

/** @param {object|null|undefined} p */
export function hasProjectMaterials(p) {
  if (!p) return false
  return !!(p.source_path || p.source_filename || p.workspace_path || p.id)
}

/** @param {object|null|undefined} p */
export function hasBakedWorkspace(p) {
  if (!p) return false
  const st = String(p.status || '')
  return !!(p.workspace_path && ['generated', 'running', 'failed'].includes(st))
}

/**
 * 生成成功默认进「论文材料」（毕设：先对照实包写论文，再答辩 PPT / 质检交付）。
 * @param {string} status
 */
export function defaultTabForStatus(status) {
  switch (status) {
    case 'needs_confirm':
      return 'match'
    case 'ready':
    case 'generating':
      return 'generate'
    case 'failed':
    case 'generated':
    case 'running':
      return 'thesis'
    default:
      return 'match'
  }
}

/**
 * 进入论文材料时默认二级页：论文材料卡。
 * @param {object|null|undefined} _p
 */
export function defaultDeliveryArtifactView(_p) {
  return 'thesis'
}

/**
 * @param {object|null|undefined} p
 * @param {string} tabName
 * @returns {{ ok: boolean, reason: string }}
 */
export function canEnterDetailTab(p, tabName) {
  const name = String(tabName || '')
  if (name === 'match' || name === 'tools' || name === 'materials') {
    return { ok: true, reason: '' }
  }
  if (name === 'generate') {
    if (p?.match_confirmed) return { ok: true, reason: '' }
    return { ok: false, reason: '待匹配确认' }
  }
  if (name === 'artifacts' || name === 'runtime' || name === 'thesis' || name === 'ppt') {
    if (hasBakedWorkspace(p)) return { ok: true, reason: '' }
    if (String(p?.status || '') === 'generating') {
      return {
        ok: false,
        reason:
          name === 'thesis'
            ? '生成进行中 · 完成后进入论文材料'
            : name === 'ppt'
              ? '生成进行中 · 完成后进入答辩 PPT'
              : '生成进行中 · 完成后进入质检交付',
      }
    }
    if (!p?.match_confirmed) {
      return { ok: false, reason: '待匹配并生成' }
    }
    return {
      ok: false,
      reason:
        name === 'thesis'
          ? '待生成工程 · 论文材料'
          : name === 'ppt'
            ? '待生成工程 · 答辩 PPT'
            : '待生成工程 · 质检交付或预览',
    }
  }
  return { ok: true, reason: '' }
}

/**
 * @param {object|null|undefined} p
 * @param {string} activeTab 当前一级 Tab
 * @returns {Array<{
 *   key: string,
 *   label: string,
 *   tab: string|null,
 *   state: 'done'|'current'|'todo'|'locked',
 *   lockReason: string,
 * }>}
 */
export function buildDeliveryStages(p, activeTab = '') {
  const tab = String(activeTab || '')
  const matched = !!p?.match_confirmed
  const generating = String(p?.status || '') === 'generating'
  const baked = hasBakedWorkspace(p)
  const materialsOk = hasProjectMaterials(p)

  /** @type {Record<string, 'done'|'current'|'todo'|'locked'>} */
  const states = {}
  /** @type {Record<string, string>} */
  const locks = {}

  states.materials = materialsOk ? 'done' : 'todo'

  const lockPostBake = (reason) => {
    states.thesis = 'locked'
    locks.thesis = reason
    states.ppt = 'locked'
    locks.ppt = reason
    states.delivery = 'locked'
    locks.delivery = reason
  }

  const resetPostBakeTodo = () => {
    states.thesis = 'todo'
    states.ppt = 'todo'
    states.delivery = 'todo'
  }

  if (!matched) {
    states.match = 'current'
    states.generate = 'locked'
    locks.generate = '待匹配确认'
    lockPostBake('待匹配并生成')
  } else if (generating) {
    states.match = 'done'
    states.generate = 'current'
    lockPostBake('生成进行中 · 完成后可继续')
  } else if (baked) {
    states.match = 'done'
    states.generate = 'done'
    const onDelivery = tab === 'artifacts'
    const onThesis = tab === 'thesis'
    const onPpt = tab === 'ppt'
    const onMatch = tab === 'match'
    const onGenerate = tab === 'generate'
    const onMaterials = tab === 'materials'
    resetPostBakeTodo()
    if (onThesis) states.thesis = 'current'
    else if (onPpt) states.ppt = 'current'
    else if (onDelivery) states.delivery = 'current'
    if (onGenerate) {
      states.generate = 'current'
      resetPostBakeTodo()
    }
    if (onMatch) {
      states.match = 'current'
      states.generate = 'done'
      resetPostBakeTodo()
    }
    if (onMaterials) {
      states.materials = 'current'
      resetPostBakeTodo()
    }
    // 预览/日志等旁链：主战场标在论文材料（毕设写材料阶段）
    if (!onDelivery && !onThesis && !onPpt && !onGenerate && !onMatch && !onMaterials) {
      states.thesis = 'current'
    }
  } else {
    // 已匹配、未出包（ready）
    states.match = 'done'
    states.generate =
      tab === 'generate' || tab === 'match'
        ? tab === 'generate'
          ? 'current'
          : 'todo'
        : 'current'
    if (tab === 'match') {
      states.match = 'current'
      states.generate = 'todo'
    }
    lockPostBake('待生成工程')
  }

  return DELIVERY_STAGE_DEFS.map((d) => ({
    key: d.key,
    label: d.label,
    tab: d.tab,
    state: states[d.key] || 'todo',
    lockReason: locks[d.key] || '',
  }))
}

/** 供测试/文档：可下载时就绪条主操作已是下载 */
export function deliveryPrimaryIsDownload(p) {
  return readinessIsDownloadable(p)
}
