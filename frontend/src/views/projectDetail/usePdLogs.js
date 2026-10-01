/**
 * 生成/运行日志拉取与过滤（挂入 useProjectDetail）。
 */
import { computed, ref } from 'vue'
import { api } from '../../api'
import { LOG_SIDES } from '../../opsShared'

/**
 * @param {object} deps
 * @param {import('vue').Ref} deps.p
 */
export function usePdLogs({ p }) {
  const logSide = ref('job')
  const logText = ref('')
  const logFilter = ref('')
  const logLoading = ref(false)
  const logSides = LOG_SIDES
  let logReqSeq = 0

  const filteredLog = computed(() => {
    const q = logFilter.value.trim().toLowerCase()
    if (!q) return logText.value || '（无日志）'
    return logText.value.split('\n').filter((l) => l.toLowerCase().includes(q)).join('\n') || '（无匹配）'
  })

  async function loadLog(side, { silent = false } = {}) {
    logSide.value = side
    const seq = ++logReqSeq
    if (!silent) logLoading.value = true
    try {
      const res = silent
        ? await api.logsPoll(p.value.id, side)
        : await api.logs(p.value.id, side)
      if (seq !== logReqSeq || logSide.value !== side) return
      logText.value = res.content || ''
    } catch {
      /* 轮询静默；手动打开日志页时仍走默认 toast */
    } finally {
      if (!silent && seq === logReqSeq) logLoading.value = false
    }
  }

  return {
    logSide,
    logText,
    logFilter,
    logLoading,
    logSides,
    logReqSeq,
    loadLog,
    filteredLog,
  }
}
