/**
 * 交付就绪指示（产品化 P1 / A5 / A6）——纯投影，不另起下载判定。
 * canDownload 口径与 opsShared.projectIsDownloadable 一致。
 * 就绪提示：recoveryHint 短述下一步（self / code），不改门禁语义。
 */

/** @param {object|null|undefined} row */
export function readinessIsDownloadable(row) {
  if (!row) return false
  if ('download_blocked_reason' in row) return !row.download_blocked_reason
  return !!row.zip_ready
}

/**
 * @typedef {'match'|'generate'|'generating'|'failed'|'scrub'|'gates'|'review'|'repack'|'download'|'delivered'|'idle'} ReadyPhase
 * @typedef {'self'|'code'|null} RecoveryKind
 * @typedef {{ text: string }} ReadyBlocker
 * @typedef {{
 *   key: string,
 *   label: string,
 *   tone: 'ok'|'warn'|'fail'|'info'|'neutral',
 * }} ReadyPrimary
 */

/**
 * @param {object|null|undefined} p 项目详情投影
 * @returns {null|{
 *   phase: ReadyPhase,
 *   title: string,
 *   canDownload: boolean,
 *   blockers: ReadyBlocker[],
 *   primary: ReadyPrimary,
 *   downloadImpact: string,
 *   recoveryKind: RecoveryKind,
 *   recoveryHint: string,
 * }}
 */
export function buildDeliveryReadiness(p) {
  if (!p) return null

  const canDownload = readinessIsDownloadable(p)
  const reason = String(p.download_blocked_reason || '').trim()
  const status = String(p.status || '')
  const mark = String(p.delivery_mark || 'none')
  const review = p.delivery_review && typeof p.delivery_review === 'object' ? p.delivery_review : {}
  const reviewState = review.review && typeof review.review === 'object' ? review.review : {}
  const reviewStatus = String(reviewState.status || '')
  const zipStale = !!review.zip_stale || /合卷|重打包|工程已变更/.test(reason)
  const gates = p.gates && typeof p.gates === 'object' ? p.gates : {}
  const blockingGates = Array.isArray(review.blocking_gates) ? review.blocking_gates : []
  const needsScrub =
    gates.p3copy?.ok === false
    || (gates.p3s?.ok === false && Array.isArray(gates.p3s?.detail?.demo_hits) && gates.p3s.detail.demo_hits.length > 0)

  /** @type {ReadyBlocker[]} */
  const blockers = []
  const pushBlocker = (text) => {
    const t = String(text || '').trim()
    if (!t) return
    if (blockers.some((b) => b.text === t)) return
    if (blockers.length >= 3) return
    blockers.push({ text: t })
  }
  if (reason) pushBlocker(reason)
  for (const g of blockingGates) {
    if (!g || typeof g !== 'object') continue
    const label = String(g.label || g.key || '').trim()
    if (label) pushBlocker(`门禁未过：${label}`)
  }
  if (needsScrub && gates.p3copy?.ok === false) {
    pushBlocker(gates.p3copy?.desc || '学生可见文案未过 · 可先清洗')
  }

  const downloadImpact = canDownload ? '可以下载 ZIP' : '暂不可下载 ZIP'

  /** @param {Partial<ReturnType<typeof buildDeliveryReadiness>> & { phase: ReadyPhase, title: string, primary: ReadyPrimary }} base */
  const pack = (base) => ({
    canDownload: false,
    blockers: [],
    downloadImpact: '暂不可下载 ZIP',
    recoveryKind: null,
    recoveryHint: '',
    ...base,
  })

  // —— 阶段机（只读已有字段，不改下载条件）——
  if (
    !p.match_confirmed
    && status !== 'generating'
    && status !== 'failed'
    && !['generated', 'running'].includes(status)
  ) {
    return pack({
      phase: 'match',
      title: '待匹配确认',
      blockers: blockers.length ? blockers : [{ text: '待匹配确认' }],
      primary: { key: 'match', label: '去匹配确认', tone: 'info' },
      recoveryHint: '核对业务类型与用法后确认。',
    })
  }

  if (status === 'generating') {
    return pack({
      phase: 'generating',
      title: '生成中',
      blockers: blockers.length ? blockers : [{ text: reason || '打包中' }],
      primary: { key: 'generate', label: '查看生成进度', tone: 'info' },
    })
  }

  if (status === 'failed') {
    return pack({
      phase: 'failed',
      title: '生成失败',
      blockers: blockers.length ? blockers : [{ text: reason || '生成未完成 · 暂不可下载' }],
      primary: { key: 'retry', label: '从失败步骤重试', tone: 'fail' },
      recoveryKind: 'self',
      recoveryHint: '从失败步骤重试；同错反复则改生成逻辑。',
    })
  }

  if (mark === 'delivered') {
    return pack({
      phase: 'delivered',
      title: '已发出',
      canDownload,
      primary: canDownload
        ? { key: 'download', label: '再次下载 ZIP', tone: 'neutral' }
        : { key: 'gates', label: '查看质量检查', tone: 'warn' },
      downloadImpact: canDownload ? '可以下载 ZIP' : '暂不可下载 ZIP',
    })
  }

  if (canDownload) {
    if (mark === 'ready') {
      return pack({
        phase: 'download',
        title: '可下载 · 已审待发',
        canDownload: true,
        primary: { key: 'downloadDeliver', label: '下载并发出', tone: 'ok' },
        downloadImpact,
      })
    }
    return pack({
      phase: 'download',
      title: '可下载',
      canDownload: true,
      primary: { key: 'download', label: '下载 ZIP', tone: 'ok' },
      downloadImpact,
    })
  }

  // 以下均不可下载：按阻断原因指向下一步（同源 reason / gates / review）
  if (zipStale || /合卷|重打包/.test(reason)) {
    return pack({
      phase: 'repack',
      title: '待重打包',
      blockers: blockers.length ? blockers : [{ text: reason || '工程已变更 · 请验收后重打包' }],
      primary: { key: 'review', label: '去质检交付重打包', tone: 'warn' },
      downloadImpact,
      recoveryKind: 'self',
      recoveryHint: '验收通过后重打包。',
    })
  }

  if (reviewStatus === 'active' || /复审|结案|回退/.test(reason)) {
    return pack({
      phase: 'review',
      title: '复审中',
      blockers: blockers.length ? blockers : [{ text: reason || '交付复审进行中' }],
      primary: { key: 'review', label: '打开交付复审', tone: 'warn' },
      downloadImpact,
      recoveryKind: 'self',
      recoveryHint: '在质检交付验收或重打包。',
    })
  }

  if (needsScrub) {
    return pack({
      phase: 'scrub',
      title: '待清洗文案',
      blockers: blockers.length ? blockers : [{ text: '学生可见文案门禁未过' }],
      primary: { key: 'scrub', label: '清洗文案', tone: 'warn' },
      downloadImpact,
      recoveryKind: 'self',
      recoveryHint: '清洗文案后验收。',
    })
  }

  if (['generated', 'running', 'ready'].includes(status) || reason) {
    const gateFail = /质量检查|质检|门禁/.test(reason) || blockingGates.length > 0
    const layoutOrControls = /布局|控件|p3layout|p3controls|空壳/i.test(reason)
      || blockingGates.some((g) => /布局|控件|layout|controls|空壳/i.test(String(g?.label || g?.key || '')))
    // 壳顶标题与第 6 步诊断卡对齐：门禁红用「门禁未过」，禁「暂不可下载」当总判
    return pack({
      phase: 'gates',
      title: gateFail ? '门禁未过' : (zipStale ? '待重打包' : '交付未就绪'),
      blockers: blockers.length ? blockers : [{ text: reason || '质量检查未通过' }],
      primary: { key: 'gates', label: '去质检交付', tone: 'fail' },
      downloadImpact,
      recoveryKind: layoutOrControls ? 'code' : 'self',
      recoveryHint: layoutOrControls
        ? '需要改程序 · 记下失败类型后改生成逻辑'
        : '打开质检交付 · 可清洗或重打包',
    })
  }

  return pack({
    phase: 'idle',
    title: '准备中',
    blockers: blockers.length ? blockers : [{ text: '完成匹配并生成后可在此查看交付状态' }],
    primary: {
      key: p.match_confirmed ? 'generate' : 'match',
      label: p.match_confirmed ? '去一键生成' : '去匹配确认',
      tone: 'info',
    },
  })
}
