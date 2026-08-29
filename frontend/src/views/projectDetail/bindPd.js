import { inject, toRefs } from 'vue'
import { PD_KEY } from './context'

/** ProjectDetail provide → toRefs，供各 Tab / Modal 模板直接解包使用 */
export function bindPd() {
  const pd = inject(PD_KEY)
  if (!pd) throw new Error('ProjectDetail context missing')
  return toRefs(pd)
}
