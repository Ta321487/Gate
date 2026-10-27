/**
 * 任务日志按次切段：认 RUN start/end 锚点；旧日志用「preview stopped」作起点。
 * 分隔符与 backend jobs.format_run_* 一致（U+00B7 MIDDLE DOT）。
 */

const MARK_DOT = '\u00b7'
const MARK_SEP = `\\s*${MARK_DOT}\\s*`

const TS_RE = /^\[(\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]\s*/
const RUN_START_RE = /======== RUN start/
const RUN_END_RE = new RegExp(`======== RUN end${MARK_SEP}([A-Z_]+)`)
const LEGACY_START = `preview stopped ${MARK_DOT} 生成前已停旧进程`

const OUTCOME_ZH = {
  SUCCESS: '成功',
  FAIL: '失败',
  GATE_FAIL: '门禁失败',
  CANCELLED: '已取消',
  RUNNING: '进行中',
  UNKNOWN: '未完结',
}

function lineTs(line) {
  const m = TS_RE.exec(line || '')
  return m ? m[1] : ''
}

function detectOutcome(body) {
  const text = body || ''
  const end = [...text.matchAll(new RegExp(RUN_END_RE.source, 'g'))]
  if (end.length) {
    const last = end[end.length - 1]
    return String(last[1] || 'UNKNOWN').toUpperCase()
  }
  if (new RegExp(`SUCCESS${MARK_SEP}zip unlocked`).test(text)) return 'SUCCESS'
  if (new RegExp(`GATE FAIL${MARK_SEP}`).test(text)) return 'GATE_FAIL'
  if (/\bERROR\b/.test(text)) return 'FAIL'
  if (/CANCELLED|已取消/.test(text)) return 'CANCELLED'
  return 'RUNNING'
}

function isRunStartLine(line) {
  return RUN_START_RE.test(line) || (line || '').includes(LEGACY_START)
}

/**
 * @param {string} raw
 * @returns {{ index: number, startedAt: string, outcome: string, outcomeLabel: string, label: string, body: string }[]}
 */
export function parseJobRuns(raw) {
  const text = String(raw || '')
  if (!text.trim()) return []

  const lines = text.split('\n')
  /** @type {{ start: number, startedAt: string }[]} */
  const cuts = []
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    if (!line || !isRunStartLine(line)) continue
    // legacy：同一 RUN 内可能先有 RUN start 再有 preview stopped，勿重复切
    if (line.includes(LEGACY_START) && cuts.length) {
      const prev = cuts[cuts.length - 1]
      const chunk = lines.slice(prev.start, i).join('\n')
      if (RUN_START_RE.test(chunk) && !RUN_END_RE.test(chunk)) continue
    }
    cuts.push({ start: i, startedAt: lineTs(line) })
  }

  if (!cuts.length) {
    const body = text.replace(/\s+$/, '')
    const outcome = detectOutcome(body)
    const startedAt = lineTs(lines.find((l) => l && l.trim()) || '')
    return [
      {
        index: 0,
        startedAt,
        outcome,
        outcomeLabel: OUTCOME_ZH[outcome] || outcome,
        label: `全部记录${startedAt ? ` ${MARK_DOT} ${startedAt}` : ''} ${MARK_DOT} ${OUTCOME_ZH[outcome] || outcome}`,
        body,
      },
    ]
  }

  // 锚点前的残页并入第一次
  if (cuts[0].start > 0) {
    const head = lines.slice(0, cuts[0].start).join('\n').trim()
    if (head) cuts[0].start = 0
  }

  return cuts.map((cut, idx) => {
    const end = idx + 1 < cuts.length ? cuts[idx + 1].start : lines.length
    const body = lines.slice(cut.start, end).join('\n').replace(/\s+$/, '')
    const outcome = detectOutcome(body)
    const n = idx + 1
    const when = cut.startedAt || lineTs(body.split('\n')[0] || '')
    const outcomeLabel = OUTCOME_ZH[outcome] || outcome
    return {
      index: idx,
      startedAt: when,
      outcome,
      outcomeLabel,
      label: `第 ${n} 次${when ? ` ${MARK_DOT} ${when}` : ''} ${MARK_DOT} ${outcomeLabel}`,
      body,
    }
  })
}

export function filterLogText(text, q) {
  const raw = text || ''
  const needle = (q || '').trim().toLowerCase()
  if (!needle) return raw || '（无日志）'
  const hit = raw.split('\n').filter((l) => l.toLowerCase().includes(needle)).join('\n')
  return hit || '（无匹配）'
}

export function logLineClass(line) {
  const s = line || ''
  if (
    new RegExp(`GATE FAIL|======== RUN end${MARK_SEP}(FAIL|GATE_FAIL)|^\\[[^\\]]+\\] ERROR\\b`).test(
      s,
    )
  ) {
    return 'log-line-err'
  }
  if (new RegExp(`SUCCESS${MARK_SEP}zip unlocked|======== RUN end${MARK_SEP}SUCCESS`).test(s)) {
    return 'log-line-ok'
  }
  if (/======== RUN (start|end)/.test(s)) return 'log-line-mark'
  return ''
}

export { OUTCOME_ZH, MARK_DOT }
