/**
 * 生成/运行日志拉取与过滤（挂入 useProjectDetail）。
 * 任务侧默认只看最近一次 RUN；可切历史或全文。
 */
import { computed, ref, watch } from 'vue'
import { api } from '../../api'
import { LOG_SIDES } from '../../opsShared'
import { filterLogText, parseJobRuns } from './jobLogRuns'

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
  /** 'latest' | 'all' | '0' | '1' …（run index 字符串） */
  const logRunSel = ref('latest')
  let logReqSeq = 0

  const logRuns = computed(() => {
    if (logSide.value !== 'job') return []
    return parseJobRuns(logText.value)
  })

  const logRunOptions = computed(() => {
    const runs = logRuns.value
    if (!runs.length) return []
    const opts = [
      { value: 'latest', label: `最近一次 · ${runs[runs.length - 1].outcomeLabel}` },
      { value: 'all', label: `全部（${runs.length} 次）` },
    ]
    for (let i = runs.length - 1; i >= 0; i--) {
      opts.push({ value: String(i), label: runs[i].label })
    }
    return opts
  })

  const activeLogBody = computed(() => {
    if (logSide.value !== 'job') return logText.value || ''
    const runs = logRuns.value
    if (!runs.length) return logText.value || ''
    const sel = logRunSel.value
    if (sel === 'all') {
      return runs.map((r) => r.body).join('\n\n')
    }
    if (sel === 'latest' || sel === '' || sel == null) {
      return runs[runs.length - 1].body
    }
    const idx = Number(sel)
    if (Number.isFinite(idx) && runs[idx]) return runs[idx].body
    return runs[runs.length - 1].body
  })

  const filteredLog = computed(() => filterLogText(activeLogBody.value, logFilter.value))

  const filteredLogLines = computed(() => {
    const t = filteredLog.value
    if (t === '（无日志）' || t === '（无匹配）') return [t]
    return t.split('\n')
  })

  const showLogRunPicker = computed(
    () => logSide.value === 'job' && logRuns.value.length > 1,
  )

  watch(logSide, (side) => {
    if (side === 'job') logRunSel.value = 'latest'
  })

  watch(logRuns, (runs) => {
    if (logRunSel.value === 'latest' || logRunSel.value === 'all') return
    const idx = Number(logRunSel.value)
    if (!Number.isFinite(idx) || idx < 0 || idx >= runs.length) {
      logRunSel.value = 'latest'
    }
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
    logRunSel,
    logRuns,
    logRunOptions,
    showLogRunPicker,
    loadLog,
    filteredLog,
    filteredLogLines,
    activeLogBody,
  }
}
