/** 资料字段格式：仅手机 / 邮箱；业务号不做死规则。 */

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
