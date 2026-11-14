/**
 * pytest 调 Node：与 frontend deliveryReadiness.js 同真源。
 * stdin：JSON 项目投影数组；stdout：buildDeliveryReadiness 结果数组。
 */
import { buildDeliveryReadiness, readinessIsDownloadable } from '../../../frontend/src/deliveryReadiness.js'

let raw = ''
for await (const chunk of process.stdin) raw += chunk
const cases = JSON.parse(raw || '[]')
const out = cases.map((p) => {
  const r = buildDeliveryReadiness(p)
  return {
    canDownload: readinessIsDownloadable(p),
    phase: r?.phase || null,
    title: r?.title || null,
    primaryKey: r?.primary?.key || null,
    blockerCount: r?.blockers?.length || 0,
    blockers: (r?.blockers || []).map((b) => b.text),
    downloadImpact: r?.downloadImpact || null,
  }
})
process.stdout.write(JSON.stringify(out))
