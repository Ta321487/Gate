/**
 * 详情属性适用性（第 3 层）。
 * 适用表留在基线（按 shopCatalogKind 查），禁止塞进学生 schema。
 * 无皮 / 无表 → 不裁剪（整池选填；买家空值不露另走 shouldShow）。
 */
import { APP_DELIVERED } from '../appDelivered.js'

/**
 * 与 backend shop_retail_niches.detail_attr_when 对齐；加皮须双边同改 + 测。
 * key → 分类名子串（命中任一才露）；未列出的属性 = always。
 */
const WHEN_BY_CATALOG = {
  retail_fitness: {
    loadCap: ['哑铃', '杠铃', '壶铃'],
    resistance: ['弹力带', '拉力'],
  },
  fitness: {
    loadCap: ['哑铃', '杠铃', '壶铃'],
    resistance: ['弹力带', '拉力'],
  },
}

function catalogKind() {
  return String(APP_DELIVERED?.shopCatalogKind || '').trim()
}

/** @returns {Record<string, string[]>|null} */
export function detailAttrWhenMap() {
  const kind = catalogKind()
  if (!kind) return null
  const table = WHEN_BY_CATALOG[kind]
  return table || null
}

/** @param {string[]} categoryNames */
export function isDetailAttrApplicable(fieldKey, categoryNames) {
  const when = detailAttrWhenMap()
  if (!when) return true
  const key = String(fieldKey || '')
  if (!key) return true
  const needles = when[key]
  if (needles == null) return true
  if (!Array.isArray(needles) || !needles.length) return true
  const names = (categoryNames || []).map((x) => String(x || '').trim()).filter(Boolean)
  if (!names.length) return true
  const blob = names.join('｜')
  return needles.some((n) => {
    const s = String(n || '').trim()
    return s && blob.includes(s)
  })
}

export function detailAttrHasValue(row, key) {
  if (!row || !key) return false
  const v = row[key]
  if (v == null || v === '') return false
  if (typeof v === 'number') return Number.isFinite(v)
  const s = String(v).trim()
  return !!s && s !== '—'
}

/** 买家脸：适用且有值才露 */
export function shouldShowDetailAttr(row, fieldKey, categoryNames) {
  if (!isDetailAttrApplicable(fieldKey, categoryNames)) return false
  return detailAttrHasValue(row, fieldKey)
}
