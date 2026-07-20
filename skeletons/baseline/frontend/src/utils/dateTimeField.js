/** 档案/单据 datetime 字段：步长与 Element Plus 禁用分钟/秒 */

/** @param {number|string|null|undefined} step */
export function normalizeTimeStepMinutes(step) {
  const n = Number(step)
  if (!Number.isFinite(n) || n <= 1) return 1
  return Math.min(60, Math.max(1, Math.floor(n)))
}

/** 返回不可选的分钟列表（步长外） */
export function disabledMinutesForStep(step) {
  const s = normalizeTimeStepMinutes(step)
  if (s <= 1) return () => []
  return () => {
    const out = []
    for (let i = 0; i < 60; i += 1) {
      if (i % s !== 0) out.push(i)
    }
    return out
  }
}

/** 步长≥1 时秒固定 0，禁用 1–59 */
export function disabledSecondsForStep(step) {
  const s = normalizeTimeStepMinutes(step)
  if (s <= 1) return () => []
  return () => {
    const out = []
    for (let i = 1; i < 60; i += 1) out.push(i)
    return out
  }
}

export function dateTimePickerProps(field = {}) {
  const step = normalizeTimeStepMinutes(field.timeStepMinutes ?? field.time_step_minutes)
  const withStep = step > 1
  return {
    type: 'datetime',
    valueFormat: 'YYYY-MM-DD HH:mm:ss',
    format: withStep ? 'YYYY-MM-DD HH:mm' : 'YYYY-MM-DD HH:mm:ss',
    timeFormat: withStep ? 'HH:mm' : 'HH:mm:ss',
    placeholder: withStep ? `选日期后点上方时间（${step} 分钟一格）` : '选日期后点上方时间选时分秒',
    disabledMinutes: disabledMinutesForStep(step),
    disabledSeconds: disabledSecondsForStep(step),
  }
}
