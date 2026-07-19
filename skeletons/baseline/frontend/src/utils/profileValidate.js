/** 资料字段格式：仅手机 / 邮箱；业务号不做死规则。条件必填/可见见 isProfileField*。 */

const PHONE = /^1[3-9]\d{9}$/
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export function checkPhone(val) {
  const v = (val || '').trim()
  if (!v) return ''
  return PHONE.test(v) ? '' : '手机号格式不正确（11 位）'
}

export function checkEmail(val) {
  const v = (val || '').trim()
  if (!v) return ''
  return EMAIL.test(v) ? '' : '邮箱格式不正确'
}

/** @returns {string} 错误文案，空串表示通过 */
export function validateProfileFormats(phone, extras = {}) {
  const p = checkPhone(phone)
  if (p) return p
  const e = checkEmail(extras.email)
  if (e) return e
  return ''
}

function whenMatch(when, extras) {
  if (!when || !when.field || !Array.isArray(when.in)) return null
  const cur = String(extras?.[when.field] ?? '').trim()
  return when.in.includes(cur)
}

/** 条件必填：有 requiredWhen 时按身份等判断；否则看 required */
export function isProfileFieldRequired(f, extras = {}) {
  if (!f) return false
  const hit = whenMatch(f.requiredWhen, extras)
  if (hit === null) return !!f.required
  return hit
}

/**
 * 条件可见：未选驱动字段时隐藏条件字段，先选身份再出对应项。
 */
export function isProfileFieldVisible(f, extras = {}) {
  if (!f) return false
  const when = f.visibleWhen
  if (!when?.field || !Array.isArray(when.in)) return true
  const cur = String(extras?.[when.field] ?? '').trim()
  if (!cur) return false
  return when.in.includes(cur)
}
