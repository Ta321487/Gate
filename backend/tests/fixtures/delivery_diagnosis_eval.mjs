/** Node 冒烟：deliveryDiagnosis 矩阵（cwd = 仓库根） */
import { pathToFileURL } from "url"
import path from "path"
import { fileURLToPath } from "url"

const here = path.dirname(fileURLToPath(import.meta.url))
const root = path.resolve(here, "../../..")
const modUrl = pathToFileURL(path.join(root, "frontend/src/deliveryDiagnosis.js")).href
const { buildDeliveryDiagnosis } = await import(modUrl)

const tide = buildDeliveryDiagnosis({
  zipStale: true,
  blockingGates: [
    { key: "p3q", label: "交付质量摘要", desc: "管理员导语串主办方" },
    { key: "p3lean", label: "学生包瘦身 · ZIP 最终确认", desc: "contentOn；theme_missing" },
  ],
  regressions: [],
  openNotesCount: 0,
  canRepack: false,
  reviewActive: false,
})
if (!tide?.verdict) throw new Error("missing tide")
if (/^暂不可下载/.test(tide.verdict)) throw new Error("download-centric verdict")
if (tide.layers.length < 3) throw new Error("expect flow+2 gates")
if (tide.nextAction !== "verify") throw new Error("next should verify")

const staleOnly = buildDeliveryDiagnosis({
  zipStale: true,
  blockingGates: [],
  canRepack: true,
})
if (staleOnly.nextAction !== "repack") throw new Error("stale+canRepack → repack")
if (!/工程又动过|不同步/.test(staleOnly.verdict)) throw new Error("stale verdict")

const none = buildDeliveryDiagnosis({ zipStale: false, blockingGates: [] })
if (none !== null) throw new Error("expect null when clean")

// 未进复审 + 清单回退 → 只推进入复审，禁止「结束复审」
const regressIdle = buildDeliveryDiagnosis({
  zipStale: true,
  blockingGates: [{ key: "p3q", label: "交付质量摘要", desc: "串台" }],
  regressions: [{ message: "质量检查项回退" }],
  reviewActive: false,
  rebakeEscape: false,
})
if (regressIdle.nextAction !== "start") throw new Error("idle+regress → start")
if (regressIdle.nextLabel !== "进入复审") throw new Error("idle label")

// 复审中 + 回退 → 结束并重生
const regressActive = buildDeliveryDiagnosis({
  zipStale: true,
  blockingGates: [{ key: "p3q", label: "交付质量摘要", desc: "串台" }],
  regressions: [{ message: "质量检查项回退" }],
  reviewActive: true,
  rebakeEscape: true,
})
if (regressActive.nextAction !== "close-rebake") throw new Error("active+regress → close-rebake")

console.log(JSON.stringify({ ok: true, tideLayers: tide.layers.length }))
