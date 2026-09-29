/** ISBN-10 / ISBN-13 校验（去连字符后按标准加权）。 */

export function normalizeIsbn(raw) {
  return String(raw || '')
    .replace(/[\s-]/g, '')
    .toUpperCase()
}

export function isValidIsbn10(digits) {
  if (!/^\d{9}[\dX]$/.test(digits)) return false
  let sum = 0
  for (let i = 0; i < 9; i += 1) sum += (10 - i) * Number(digits[i])
  const check = digits[9] === 'X' ? 10 : Number(digits[9])
  sum += check
  return sum % 11 === 0
}

export function isValidIsbn13(digits) {
  if (!/^\d{13}$/.test(digits)) return false
  let sum = 0
  for (let i = 0; i < 12; i += 1) {
    sum += Number(digits[i]) * (i % 2 === 0 ? 1 : 3)
  }
  const check = (10 - (sum % 10)) % 10
  return check === Number(digits[12])
}

/** 空串视为未填（由调用方决定是否必填）；非空则须通过校验。 */
export function isValidIsbn(raw) {
  const s = normalizeIsbn(raw)
  if (!s) return true
  if (s.length === 10) return isValidIsbn10(s)
  if (s.length === 13) return isValidIsbn13(s)
  return false
}
