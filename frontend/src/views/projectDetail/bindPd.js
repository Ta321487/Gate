import { inject, toRefs, unref } from 'vue'
import { PD_KEY } from './context'

/**
 * ProjectDetail provide → 供各 Tab / Modal 使用。
 * 状态仍用 toRefs（模板自动解包）；函数直接可调用，避免脚本里 `fn()` 报 not a function。
 */
export function bindPd() {
  const pd = inject(PD_KEY)
  if (!pd) throw new Error('ProjectDetail context missing')
  const refs = toRefs(pd)
  const out = {}
  for (const key of Object.keys(refs)) {
    const r = refs[key]
    if (typeof unref(r) === 'function') {
      out[key] = (...args) => unref(r)(...args)
    } else {
      out[key] = r
    }
  }
  return out
}
