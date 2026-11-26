/**
 * 资产台共用：待补数字约定（console-product-surface §3.5 R2）。
 * - 未点「检查待补」：显示 —（未知），禁止假 0
 * - 检查后：0 = 已扫且无洞；n = 仍有 n 条
 * 切「待补」页签只换视图，不自动扫。
 */
export function gapStatDisplay(scanned, count) {
  if (!scanned) return '—'
  const n = Number(count)
  return Number.isFinite(n) ? String(n) : '0'
}
