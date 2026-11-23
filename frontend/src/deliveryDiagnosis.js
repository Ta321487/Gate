/**
 * 第 6 步质检交付 · 诊断小卡（确定性拼接）。
 * 合同：docs/delivery-diagnosis-orchestration.md
 * - 只服务交付工作台；不进生成页
 * - 总判禁下载中心主义起句；分层一行头；详情下沉
 * - 与 deliveryReadiness 同源信号，不另起下载判定
 */

/** @type {Record<string, { code: string, locus: string, bucket: 'content'|'pack'|'path'|'other' }>} */
const GATE_META = {
  p3q: { code: 'GATE_QA', locus: 'delivery_review · agents_qa / domain_vocab', bucket: 'content' },
  p3copy: { code: 'GATE_STUDENT_COPY', locus: 'bake/gates · FACTORY_UI', bucket: 'content' },
  p3s: { code: 'GATE_SEMANTIC', locus: 'bake/gates/semantic.py', bucket: 'content' },
  p3lean: { code: 'BAKE_PACK_LEAN', locus: 'bake/pack_prune.py', bucket: 'pack' },
  p3layout: { code: 'BAKE_LAYOUT', locus: 'bake/gates/layout_workspace.py', bucket: 'pack' },
  p3controls: { code: 'BAKE_FORM_CONTROLS', locus: 'bake/gates/form_controls_workspace.py', bucket: 'pack' },
  p3n: { code: 'BAKE_SCHEMA_NF', locus: 'bake/gates/schema_nf.py', bucket: 'pack' },
  p3ac: { code: 'BAKE_ARCHIVE_COLUMNS', locus: 'bake/archive_columns.py', bucket: 'pack' },
  p3t: { code: 'BAKE_TABLE_BUDGET', locus: 'bake/engine_sql.py', bucket: 'pack' },
  p3a: { code: 'GATE_CHECKLIST', locus: 'bake/gates/evaluate.py', bucket: 'other' },
  p3b: { code: 'GATE_SCHEMA', locus: 'bake/gates/evaluate.py', bucket: 'other' },
  p3c: { code: 'GATE_SCHEMA', locus: 'bake/gates/evaluate.py', bucket: 'other' },
  p3d: { code: 'GATE_ADMIN_BOUNDARY', locus: 'bake/gates/evaluate.py', bucket: 'other' },
  accept: { code: 'GATE_ACCEPT', locus: 'bake/gates/evaluate.py', bucket: 'other' },
  p2: { code: 'GATE_E2E_PATH', locus: 'bake/gates/evaluate.py', bucket: 'path' },
  p1: { code: 'GATE_E2E_PATH', locus: 'bake/gates/evaluate.py', bucket: 'path' },
  p0a: { code: 'GATE_E2E_PATH', locus: 'bake/gates/evaluate.py', bucket: 'path' },
  p0b: { code: 'GATE_E2E_PATH', locus: 'bake/gates/evaluate.py', bucket: 'path' },
}

const BUCKET_LABEL = {
  content: '内容审',
  pack: '包洁净',
  path: '主路径',
  other: '门禁',
  flow: '流程',
  review: '复审账',
}

/**
 * @param {object|null|undefined} g
 * @returns {{ key: string, label: string, desc: string, code: string, locus: string, bucket: string }}
 */
function normalizeGate(g) {
  const key = String(g?.key || '').trim()
  const meta = GATE_META[key] || {
    code: key ? `GATE_${key.toUpperCase()}` : 'UNKNOWN',
    locus: 'docs/bake-fail-analysis.md',
    bucket: 'other',
  }
  const label = String(g?.label || key || '未命名门禁').trim()
  const desc = String(g?.desc || '').trim()
  // 一行头不在此截字：收起态由 CSS ellipsis；展开/弹层用完整 desc
  const one = desc || label
  return {
    key: key || label,
    label,
    desc,
    one,
    code: meta.code,
    locus: meta.locus,
    bucket: meta.bucket,
  }
}

/**
 * @param {{
 *   blockingGates?: object[],
 *   zipStale?: boolean,
 *   regressions?: object[],
 *   openNotesCount?: number,
 *   rebakeEscape?: boolean,
 *   reviewActive?: boolean,
 *   canRepack?: boolean,
 *   showOkConfirm?: boolean,
 * }} input
 * @returns {null|{
 *   tone: 'warn'|'fail'|'ok',
 *   phaseLabel: string,
 *   verdict: string,
 *   layers: Array<{
 *     id: string,
 *     bucket: string,
 *     bucketLabel: string,
 *     name: string,
 *     one: string,
 *     detail: string,
 *     code: string,
 *     locus: string,
 *     jumpQa?: boolean,
 *     openModal?: boolean,
 *   }>,
 *   nextLabel: string,
 *   nextAction: 'verify'|'repack'|'close-rebake'|'start'|'notes'|'none',
 * }}
 */
export function buildDeliveryDiagnosis(input) {
  const gates = Array.isArray(input?.blockingGates)
    ? input.blockingGates.filter((x) => x && typeof x === 'object').map(normalizeGate)
    : []
  const regressions = Array.isArray(input?.regressions) ? input.regressions : []
  const zipStale = !!input?.zipStale
  const openNotes = Math.max(0, Number(input?.openNotesCount) || 0)
  const rebakeEscape = !!input?.rebakeEscape
  const reviewActive = !!input?.reviewActive
  const canRepack = !!input?.canRepack

  const hasProblem =
    gates.length > 0
    || zipStale
    || regressions.length > 0
    || openNotes > 0
    || rebakeEscape

  if (!hasProblem) {
    if (input?.showOkConfirm) {
      return {
        tone: 'ok',
        phaseLabel: '可交付',
        verdict: '门禁与复审账已齐，ZIP 与工程同步时可下载交付。',
        layers: [],
        nextLabel: '',
        nextAction: 'none',
      }
    }
    return null
  }

  /** @type {ReturnType<typeof buildDeliveryDiagnosis> extends null ? never : NonNullable<ReturnType<typeof buildDeliveryDiagnosis>>['layers']} */
  const layers = []

  if (zipStale) {
    layers.push({
      id: 'flow-stale',
      bucket: 'flow',
      bucketLabel: BUCKET_LABEL.flow,
      name: '工程已变更',
      one: 'ZIP 与工程不同步 · 消红后仍须验收重打包',
      detail: '下载是结果不是病因。验收通过后点重打包，使 ZIP 与工程一致。',
      code: '',
      locus: '',
    })
  }

  if (regressions.length) {
    const first = String(regressions[0]?.message || regressions[0] || '').trim()
    const regressTail = reviewActive
      ? '回退后勿只反复重打包；须改工程时结束复审 → 改工厂 → 重新生成。'
      : '回退后勿只反复重打包；先进入复审收口，再改工厂 → 重新生成。'
    layers.push({
      id: 'review-regress',
      bucket: 'review',
      bucketLabel: BUCKET_LABEL.review,
      name: `清单回退 ${regressions.length} 条`,
      one: first || '已通过项回退 · 勿只反复重打包',
      detail: first ? `${first}\n${regressTail}` : regressTail,
      code: '',
      locus: '',
      openModal: true,
    })
  } else if (openNotes > 0) {
    layers.push({
      id: 'review-notes',
      bucket: 'review',
      bucketLabel: BUCKET_LABEL.review,
      name: `未结案偏差 ${openNotes} 条`,
      one: '偏差未结案前不能重打包',
      detail: '在下方偏差登记结案或处理后再验收重打包。',
      code: '',
      locus: '',
    })
  }

  for (const g of gates) {
    layers.push({
      id: `gate-${g.key}`,
      bucket: g.bucket,
      bucketLabel: BUCKET_LABEL[g.bucket] || BUCKET_LABEL.other,
      name: g.label,
      one: g.one,
      detail: g.desc || g.label,
      code: g.code,
      locus: g.locus,
      jumpQa: g.key === 'p3q',
      openModal: true,
    })
  }

  // 总判：先分层，下载只作后果
  const bits = []
  if (regressions.length) bits.push('已通过清单有回退')
  if (gates.length) bits.push(`${gates.length} 道门禁未过`)
  if (zipStale) bits.push('工程与 ZIP 不同步')
  if (openNotes > 0 && !regressions.length) bits.push(`还有 ${openNotes} 条未结案偏差`)
  let verdict = bits.length ? bits.join('；') + '。' : '交付未就绪。'
  if (gates.length && zipStale) {
    verdict = `叠了多层：${gates.length} 道门禁未过，且工程与 ZIP 不同步。`
  } else if (gates.length && !zipStale) {
    verdict = `${gates.length} 道门禁未过；清单是否齐不代表可交。`
  } else if (zipStale && !gates.length && !regressions.length) {
    verdict = '内容与门禁已齐，只是工程又动过：验收通过后重打包即可。'
  }

  let phaseLabel = '质检交付'
  let nextLabel = '验收'
  let nextAction = /** @type {'verify'|'repack'|'close-rebake'|'start'|'notes'|'none'} */ ('verify')

  // 须改工程出口：已在复审 → 结束并重生；未进复审 → 只推「进入复审」，禁止顶栏进、卡上结束对打
  const needsFactoryRebake = regressions.length > 0 || (rebakeEscape && gates.length > 0)
  if (needsFactoryRebake && reviewActive) {
    phaseLabel = regressions.length ? '清单回退' : '须改工程'
    nextLabel = '结束复审并去重新生成'
    nextAction = 'close-rebake'
  } else if (needsFactoryRebake && !reviewActive) {
    phaseLabel = regressions.length ? '清单回退' : '须改工程'
    nextLabel = '进入复审'
    nextAction = 'start'
  } else if (gates.length) {
    phaseLabel = '门禁未过'
    nextLabel = '验收'
    nextAction = 'verify'
  } else if (openNotes > 0) {
    phaseLabel = '偏差未结案'
    nextLabel = '去处理偏差'
    nextAction = 'notes'
  } else if (zipStale && canRepack) {
    phaseLabel = '待重打包'
    nextLabel = '重打包'
    nextAction = 'repack'
  } else if (zipStale) {
    phaseLabel = '待重打包'
    nextLabel = '验收'
    nextAction = 'verify'
  }

  const tone = regressions.length || (gates.length && /回退/.test(verdict)) ? 'fail' : 'warn'

  return {
    tone: regressions.length ? 'fail' : tone,
    phaseLabel,
    verdict,
    layers,
    nextLabel,
    nextAction,
  }
}

export function failAnalysisHref(code) {
  const c = String(code || '').trim()
  if (!c) return '/fail-analysis'
  return `/fail-analysis?code=${encodeURIComponent(c)}`
}
