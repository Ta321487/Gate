/**
 * 长操作会话标记：刷新后仍能提示「可能仍在跑 / 正在对齐」。
 * 仅客户端语义，不改服务端状态机。
 */

const PREFIX = 'gf-long-op:'

/** @param {string} projectId @param {string} kind */
export function markLongOp(projectId, kind) {
  if (!projectId || !kind) return
  try {
    sessionStorage.setItem(
      `${PREFIX}${projectId}`,
      JSON.stringify({ kind, at: Date.now() }),
    )
  } catch {
    /* quota / private mode */
  }
}

/** @param {string} projectId */
export function clearLongOp(projectId) {
  if (!projectId) return
  try {
    sessionStorage.removeItem(`${PREFIX}${projectId}`)
  } catch {
    /* ignore */
  }
}

/**
 * @param {string} projectId
 * @param {number} [maxAgeMs=180000] 默认 3 分钟内视为可恢复
 * @returns {{ kind: string, at: number } | null}
 */
export function peekLongOp(projectId, maxAgeMs = 180000) {
  if (!projectId) return null
  try {
    const raw = sessionStorage.getItem(`${PREFIX}${projectId}`)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (!parsed || typeof parsed !== 'object' || !parsed.at) {
      clearLongOp(projectId)
      return null
    }
    if (Date.now() - Number(parsed.at) > maxAgeMs) {
      clearLongOp(projectId)
      return null
    }
    return { kind: String(parsed.kind || ''), at: Number(parsed.at) }
  } catch {
    return null
  }
}
