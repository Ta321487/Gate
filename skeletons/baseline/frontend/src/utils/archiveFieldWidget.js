/**
 * 档案字段 → 表单控件。禁止一律文本框：看 type，再看语义兜底。
 *
 * 返回值：switch | select | datetime | number | money | url | textarea | richtext | text | hidden
 */
import { isArchiveMoneyField } from './domainSchema.js'

const BOOL_LABEL_RE = /[（(]?\s*1\s*是\s*0\s*否\s*[）)]?|是否/

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
  if (type === 'number' && BOOL_LABEL_RE.test(label)) return 'switch'
  if (type === 'select') return 'select'
  if (type === 'datetime') return 'datetime'
  if (type === 'url') return 'url'
  if (type === 'textarea') return 'textarea'
  if (type === 'richtext' || (ctx.bodyField && key === ctx.bodyField)) return 'richtext'
  if (type === 'number') return isArchiveMoneyField(field) ? 'money' : 'number'
  if (type === 'string' && /摘要|备注|说明|特征|简介|描述/.test(label)) return 'textarea'
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
