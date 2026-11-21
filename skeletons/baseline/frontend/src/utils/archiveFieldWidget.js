/**
 * 档案字段 → 表单控件。禁止一律文本框：看 type，再看标签语义。
 *
 * 返回值：switch | select | datetime | date | time | number | money | url | textarea | richtext | text | hidden
 *
 * 标签规则见 fieldWidgetRules.js。
 */
import { isArchiveMoneyField } from './domainSchema.js'
import { FIELD_WIDGET_RULES } from './fieldWidgetRules.js'

function ruleHits(rule, typ, key, label) {
  const ft = String(rule.fieldType || '').trim()
  if (ft && ft !== typ) return false
  const keys = Array.isArray(rule.keys) ? rule.keys : []
  if (keys.length) return keys.includes(key)
  const exact = Array.isArray(rule.labelIsAny) ? rule.labelIsAny : []
  if (exact.length) return exact.includes(label)
  const words = Array.isArray(rule.labelHasAny) ? rule.labelHasAny : []
  if (words.length) return words.some((w) => w && label.includes(String(w)))
  return false
}

function matchHint(typ, key, label, onlyWidgets) {
  const list = Array.isArray(FIELD_WIDGET_RULES) ? FIELD_WIDGET_RULES : []
  for (const rule of list) {
    const widget = String(rule.widget || '')
    if (onlyWidgets && !onlyWidgets.has(widget)) continue
    if (ruleHits(rule, typ, key, label)) return widget
  }
  return null
}

/**
 * @param {object} field schema field
 * @param {{ stockAsToggle?: boolean, bodyField?: string }} [ctx]
 */
export function archiveFieldWidget(field, ctx = {}) {
  if (!field || !field.key) return 'text'
  const type = String(field.type || 'string')
  const key = String(field.key)
  const label = String(field.label || '')

  if (type === 'hidden') return 'hidden'
  if (key === 'stock' && ctx.stockAsToggle) return 'switch'
  if (type === 'boolean' || type === 'switch') return 'switch'
  if (type === 'number' && matchHint(type, key, label, new Set(['switch'])) === 'switch') {
    return 'switch'
  }
  if (type === 'select') return 'select'
  if (type === 'datetime') return 'datetime'
  if (type === 'date') return 'date'
  if (type === 'time') return 'time'
  if (type === 'url') return 'url'
  if (type === 'textarea') return 'textarea'
  if (type === 'richtext' || (ctx.bodyField && key === ctx.bodyField)) return 'richtext'
  if (type === 'number') return isArchiveMoneyField(field) ? 'money' : 'number'
  if (type === 'string') {
    const hit = matchHint(type, key, label)
    if (hit) return hit
  }
  return 'text'
}

/** 开关态：兼容 1/0、true/false、"是" */
export function archiveSwitchOn(value) {
  if (value === true || value === 1 || value === '1') return true
  if (value === false || value === 0 || value === '0' || value == null || value === '') return false
  const s = String(value).trim()
  if (s === '是' || s === 'true' || s === 'yes') return true
  if (s === '否' || s === 'false' || s === 'no') return false
  return Number(s) > 0
}

export function archiveSwitchValue(on, { asNumber = true } = {}) {
  if (asNumber) return on ? 1 : 0
  return !!on
}
