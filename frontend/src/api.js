import axios from 'axios'
import { message } from './ui'

const http = axios.create({ baseURL: '/api', timeout: 60000 })

/** 扫盘 / 批量进程 / 大上传：禁止裸默认 60s */
const HEAVY_OPTS = { timeout: 600000 }

http.interceptors.response.use(
  (res) => res.data,
  (err) => {
    // silent: 后台轮询等场景不弹全局错误（避免 reload 超时刷屏、卡死观感）
    if (!err.config?.silent) {
      const msg = err.response?.data?.detail || err.message || '请求失败'
      message.error(typeof msg === 'string' ? msg : JSON.stringify(msg))
    }
    return Promise.reject(err)
  }
)

/** 生成中轮询：静默失败；超时须盖过「复制骨架」等重步骤下的偶发排队，
 *  过短会整段 8.00s「已取消」刷屏，误报「后端重载」。真挂死仍靠连续失败提示。 */
const POLL_OPTS = { silent: true, timeout: 45000 }

export { message }
export { confirm, alert, prompt, dialog } from './ui'

export const api = {
  health: () => http.get('/health'),
  stats: () => http.get('/projects/stats'),
  listProjects: (params) => http.get('/projects', { params }),
  upload: (files, onProgress) => {
    const list = Array.isArray(files) ? files : [files]
    const fd = new FormData()
    list.forEach((f) => {
      if (f) fd.append('files', f)
    })
    return http.post('/projects/upload', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: onProgress,
      ...HEAVY_OPTS,
    })
  },
  /** 多材料分堆预览（不建项目） */
  uploadPlan: (files, onProgress) => {
    const list = Array.isArray(files) ? files : [files]
    const fd = new FormData()
    list.forEach((f) => {
      if (f) fd.append('files', f)
    })
    return http.post('/projects/upload/plan', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: onProgress,
      ...HEAVY_OPTS,
    })
  },
  /** 未确认分堆列表（刷新恢复） */
  uploadPlans: () => http.get('/projects/upload/plans'),
  /** 丢弃未确认分堆 */
  uploadPlanDelete: (planId) =>
    http.delete(`/projects/upload/plans/${encodeURIComponent(planId)}`),
  /** 待确认分堆追加材料并重新分堆（同 plan_id） */
  uploadPlanAppend: (planId, files, onProgress) => {
    const list = Array.isArray(files) ? files : [files]
    const fd = new FormData()
    list.forEach((f) => {
      if (f) fd.append('files', f)
    })
    return http.post(
      `/projects/upload/plans/${encodeURIComponent(planId)}/append`,
      fd,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: onProgress,
        ...HEAVY_OPTS,
      },
    )
  },
  /** 确认分堆并创建项目 */
  uploadConfirm: (body) =>
    http.post('/projects/upload/confirm', body, { ...HEAVY_OPTS }),
  getProject: (id, opts) => http.get(`/projects/${id}`, opts),
  getFillPlan: (id) => http.get(`/projects/${id}/fill-plan`),
  fillEventsUrl: (id) => `/api/projects/${id}/fill-events`,
  getProjectPoll: (id) => http.get(`/projects/${id}`, POLL_OPTS),
  patchMatch: (id, body) => http.patch(`/projects/${id}/match`, body),
  patchDelivery: (id, mark) => http.patch(`/projects/${id}/delivery`, { mark }),
  generate: (id, { confirmDiff = false } = {}) =>
    http.post(`/projects/${id}/generate`, {}, {
      params: confirmDiff ? { confirm_diff: true } : {},
    }),
  deleteProject: (id, { keepDb = false } = {}) =>
    http.delete(`/projects/${id}`, { params: { keep_db: keepDb }, ...HEAVY_OPTS }),
  downloadUrl: (id) => `/api/projects/${id}/download`,
  getSchema: (id) => http.get(`/projects/${id}/schema`),
  /** 论文 4.6.2/4.6.3：逻辑+物理设计正文，同源 schema.sql */
  getThesisDbExport: (id, { typeParen = true } = {}) =>
    http.get(`/projects/${id}/schema/thesis-db-export`, {
      params: { type_paren: typeParen },
      timeout: 120000,
    }),
  getEr: (id, { mode = 'total', entity, display = 'sample' } = {}) =>
    http.get(`/projects/${id}/schema/er`, {
      params: {
        mode,
        display,
        ...(entity ? { entity } : {}),
      },
      timeout: 120000,
    }),
  putErLabels: (id, body) => http.put(`/projects/${id}/schema/er-labels`, body),
  putErView: (id, body) => http.put(`/projects/${id}/schema/er-view`, body),
  getOverrides: (id) => http.get(`/projects/${id}/overrides`, { timeout: 120000 }),
  // apply 会叠材料/洗缓存，勿用默认 60s 误报失败而 UI 仍旧草稿
  putOverrides: (id, body) => http.put(`/projects/${id}/overrides`, body, { timeout: 120000 }),
  clearOverridesStale: (id) =>
    http.post(`/projects/${id}/overrides/clear-stale`, null, { timeout: 120000 }),
  getModules: (id, { layout = 'identity', expandDetails = false, force = false } = {}) =>
    http.get(`/projects/${id}/schema/modules`, {
      params: {
        layout,
        expand_details: expandDetails,
        ...(force ? { force: true } : {}),
      },
    }),
  getArchitecture: (id) => http.get(`/projects/${id}/schema/architecture`),
  architectureSvgUrl: (id) => `/api/projects/${id}/schema/architecture.svg`,
  getSequences: (id, { ids } = {}) =>
    http.get(`/projects/${id}/schema/sequences`, {
      params: ids?.length ? { ids: ids.join(',') } : {},
    }),
  sequencesSvgUrl: (id, { index = 0, ids } = {}) => {
    const q = new URLSearchParams({ index: String(index) })
    if (ids?.length) q.set('ids', ids.join(','))
    return `/api/projects/${id}/schema/sequences.svg?${q}`
  },
  getActivities: (id, { ids } = {}) =>
    http.get(`/projects/${id}/schema/activities`, {
      params: ids?.length ? { ids: ids.join(',') } : {},
    }),
  activitiesSvgUrl: (id, { index = 0, ids } = {}) => {
    const q = new URLSearchParams({ index: String(index) })
    if (ids?.length) q.set('ids', ids.join(','))
    return `/api/projects/${id}/schema/activities.svg?${q}`
  },
  getClasses: (id, { display = 'sample', force = false } = {}) =>
    http.get(`/projects/${id}/schema/classes`, {
      params: { display, ...(force ? { force: true } : {}) },
      timeout: 120000,
    }),
  classesSvgUrl: (id, { display = 'sample' } = {}) => {
    const q = new URLSearchParams({ display })
    return `/api/projects/${id}/schema/classes.svg?${q}`
  },
  putClassesLayout: (id, body) =>
    http.put(`/projects/${id}/schema/classes-layout`, body, { timeout: 120000 }),
  getUsecases: (id, { actor = 'user' } = {}) =>
    http.get(`/projects/${id}/schema/usecases`, { params: { actor } }),
  usecasesSvgUrl: (id, { actor = 'user' } = {}) => {
    const q = new URLSearchParams({ actor })
    return `/api/projects/${id}/schema/usecases.svg?${q}`
  },
  usecasesMdjUrl: (id, { actor = 'user' } = {}) => {
    const q = new URLSearchParams({ actor })
    return `/api/projects/${id}/schema/usecases.mdj?${q}`
  },
  usecasesDrawioUrl: (id, { actor = 'user' } = {}) => {
    const q = new URLSearchParams({ actor })
    return `/api/projects/${id}/schema/usecases.drawio?${q}`
  },
  classesDrawioUrl: (id, { display = 'sample' } = {}) => {
    const q = new URLSearchParams({ display })
    return `/api/projects/${id}/schema/classes.drawio?${q}`
  },
  erDrawioUrl: (id, { mode = 'total', entity, display = 'sample' } = {}) => {
    const q = new URLSearchParams({ mode, display })
    if (entity) q.set('entity', entity)
    return `/api/projects/${id}/schema/er.drawio?${q}`
  },
  erPartsDrawioUrl: (id, { display = 'sample' } = {}) => {
    const q = new URLSearchParams({ display })
    return `/api/projects/${id}/schema/er-parts.drawio?${q}`
  },
  modulesDrawioUrl: (id, { layout = 'identity', expandDetails = false } = {}) => {
    const q = new URLSearchParams({
      layout,
      expand_details: expandDetails ? 'true' : 'false',
    })
    return `/api/projects/${id}/schema/modules.drawio?${q}`
  },
  erMmdUrl: (id, { mode = 'total', entity, display = 'sample' } = {}) => {
    const q = new URLSearchParams({ mode, display })
    if (entity) q.set('entity', entity)
    return `/api/projects/${id}/schema/er.mmd?${q}`
  },
  modulesMmdUrl: (id, { layout = 'identity', expandDetails = false } = {}) => {
    const q = new URLSearchParams({
      layout,
      expand_details: expandDetails ? 'true' : 'false',
    })
    return `/api/projects/${id}/schema/modules.mmd?${q}`
  },
  classesMmdUrl: (id, { display = 'sample' } = {}) => {
    const q = new URLSearchParams({ display })
    return `/api/projects/${id}/schema/classes.mmd?${q}`
  },
  usecasesMmdUrl: (id, { actor = 'user' } = {}) => {
    const q = new URLSearchParams({ actor })
    return `/api/projects/${id}/schema/usecases.mmd?${q}`
  },
  sequencesMmdUrl: (id, { index = 0, ids } = {}) => {
    const q = new URLSearchParams({ index: String(index) })
    if (ids) q.set('ids', Array.isArray(ids) ? ids.join(',') : String(ids))
    return `/api/projects/${id}/schema/sequences.mmd?${q}`
  },
  activitiesMmdUrl: (id, { index = 0, ids } = {}) => {
    const q = new URLSearchParams({ index: String(index) })
    if (ids) q.set('ids', Array.isArray(ids) ? ids.join(',') : String(ids))
    return `/api/projects/${id}/schema/activities.mmd?${q}`
  },
  architectureDrawioUrl: (id) => `/api/projects/${id}/schema/architecture.drawio`,
  architectureMmdUrl: (id) => `/api/projects/${id}/schema/architecture.mmd`,

  getTestcases: (id, { fields = 6 } = {}) =>
    http.get(`/projects/${id}/schema/testcases`, { params: { fields } }),
  testcasesMdUrl: (id, { fields = 6 } = {}) => {
    const q = new URLSearchParams({ fields: String(fields) })
    return `/api/projects/${id}/schema/testcases.md?${q}`
  },
  getUsecaseDescriptions: (id, { count = 4, tableStart = '3.1' } = {}) =>
    http.get(`/projects/${id}/schema/usecase-descriptions`, {
      params: { count, table_start: tableStart },
    }),
  usecaseDescriptionsMdUrl: (id, { count = 4, tableStart = '3.1' } = {}) => {
    const q = new URLSearchParams({
      count: String(count),
      table_start: String(tableStart),
    })
    return `/api/projects/${id}/schema/usecase-descriptions.md?${q}`
  },
  getApis: (id) => http.get(`/projects/${id}/apis`),
  /** 学生端全量冒烟：静默全局 toast，由页面自绘工厂/学生错误 */
  smokeStudentApis: (id) =>
    http.post(`/projects/${id}/apis/smoke`, null, { silent: true, timeout: 120000 }),
  erSvgUrl: (id, { mode = 'total', entity, display = 'sample' } = {}) => {
    const q = new URLSearchParams({ mode, display })
    if (entity) q.set('entity', entity)
    return `/api/projects/${id}/schema/er.svg?${q}`
  },
  modulesSvgUrl: (id, { layout = 'identity', expandDetails = false } = {}) => {
    const q = new URLSearchParams({
      layout,
      expand_details: expandDetails ? 'true' : 'false',
    })
    return `/api/projects/${id}/schema/modules.svg?${q}`
  },
  runtime: (id) => http.get(`/projects/${id}/runtime`),
  // 分配端口 / 启停握手可能超过默认 60s；长跑态靠前端轮询，勿用默认超时误杀
  // silent：由 usePdRuntime 区分超时「可能已受理」与普通失败，避免双 toast
  runtimeAction: (id, side, action) =>
    http.post(`/projects/${id}/runtime/${side}/${action}`, null, {
      timeout: 120000,
      silent: true,
    }),
  /** 批量预览启停；action=start 对运行中的项目等价重启（服务端串行错峰，可能较久） */
  runtimeBatch: (body) => http.post('/projects/runtime/batch', body, { ...HEAVY_OPTS }),
  logs: (id, side, opts) => http.get(`/projects/${id}/logs/${side}`, opts),
  logsPoll: (id, side) => http.get(`/projects/${id}/logs/${side}`, POLL_OPTS),
  listJobs: (opts) => http.get('/jobs', opts),
  listJobsPoll: () => http.get('/jobs', POLL_OPTS),
  listJobsByProject: (projectId) =>
    http.get('/jobs', { params: { project_id: projectId } }),
  getJob: (id) => http.get(`/jobs/${id}`),
  getJobGateReport: (id) => http.get(`/jobs/${id}/gate-report`),
  cancelJob: (id) => http.post(`/jobs/${id}/cancel`),
  retryJob: (id) => http.post(`/jobs/${id}/retry`),
  deleteJob: (id) => http.delete(`/jobs/${id}`),
  // 开题措辞核对可能触 LLM / 重读材料，勿用默认 60s
  getProposalDiff: (id) => http.get(`/projects/${id}/proposal-diff`, { timeout: 120000 }),
  ackPreGenerate: (id) => http.post(`/projects/${id}/delivery-review/ack-pre-generate`),
  // 会算 workspace 指纹，勿用默认 60s
  getDeliveryReview: (id) =>
    http.get(`/projects/${id}/delivery-review`, { timeout: 120000 }),
  startDeliveryReview: (id) =>
    http.post(`/projects/${id}/delivery-review/start`, null, { timeout: 120000 }),
  closeDeliveryReview: (id) =>
    http.post(`/projects/${id}/delivery-review/close`, null, { timeout: 120000 }),
  // 验圈会顺带跑 QA Agent（LLM 可达 ~120s）+ 门禁；勿用默认 60s
  verifyDeliveryReview: (id) =>
    http.post(`/projects/${id}/delivery-review/verify`, null, { timeout: 180000 }),
  repackDeliveryReview: (id) =>
    http.post(`/projects/${id}/delivery-review/repack`, null, { timeout: 120000 }),
  runDeliveryQa: (id) => http.post(`/projects/${id}/delivery-review/qa`, null, { timeout: 180000 }),
  runThesisDiagramAudit: (id) =>
    http.post(`/projects/${id}/schema/thesis-diagram-audit`, null, { timeout: 180000 }),
  scrubStudentCopy: (id) => http.post(`/projects/${id}/scrub-student-copy`, null, { timeout: 120000 }),
  addDeliveryFixNote: (id, text) =>
    http.post(`/projects/${id}/delivery-review/notes`, { text }, { timeout: 120000 }),
  resolveDeliveryFixNote: (id, noteId, done = true) =>
    http.patch(`/projects/${id}/delivery-review/notes/${noteId}`, { done }, { timeout: 120000 }),
  deliveryHandoffUrl: (id) => `/api/projects/${id}/delivery-review/handoff`,
  purgeOrphanJobs: () => http.post('/jobs/purge-orphans'),
  purgeFinishedJobs: () => http.post('/jobs/purge-finished'),
  failAnalysis: (params) => http.get('/jobs/fail-analysis', { params }),
  failAnalysisCatalog: () => http.get('/jobs/fail-analysis/catalog'),
  failAnalysisClassifyAssist: (body) =>
    http.post('/jobs/fail-analysis/classify-assist', body, { timeout: 120000 }),
  failAnalysisFixDraft: (body) =>
    http.post('/jobs/fail-analysis/fix-draft', body, { timeout: 120000 }),
  failAnalysisDiscardDraft: (jobId) =>
    http.delete(`/jobs/fail-analysis/fix-draft/${jobId}`),
  /** 受理式清盘：立刻返回，前端轮询 status */
  purgeOrphanDisk: () => http.post('/projects/purge-orphan-disk', null, HEAVY_OPTS),
  purgeOrphanDiskStatus: () =>
    http.get('/projects/purge-orphan-disk', { silent: true, timeout: 8000 }),
  deepseek: () => http.get('/deepseek'),
  saveDeepseek: (body) => http.put('/deepseek', body),
  testDeepseek: () => http.post('/deepseek/test'),
  deepseekBalance: () => http.get('/deepseek/balance'),
  llmUsage: (params) => http.get('/llm/usage', { params }),
  llmUsageChart: (params) => http.get('/llm/usage/chart', { params }),
  llmUsageSupport: (params) => http.get('/llm/usage/support', { params }),
  llmProjectTokens: () => http.get('/llm/usage/project-tokens'),
  llmCalls: (params) => http.get('/llm/calls', { params }),
  gemini: () => http.get('/gemini'),
  saveGemini: (body) => http.put('/gemini', body),
  testGemini: () => http.post('/gemini/test'),
  unsplash: () => http.get('/unsplash'),
  testUnsplash: () => http.post('/unsplash/test'),
  system: () => http.get('/system'),
  freePorts: () => http.post('/system/free-ports'),
  systemCache: () => http.get('/system/cache'),
  purgeSystemCache: () => http.post('/system/cache/purge', null, HEAVY_OPTS),
  /** 起包前布局检查摘要（台账对账 + 结构契约；全表视觉不在此接口执行） */
  layoutGate: () => http.get('/system/layout-gate', { timeout: 120000 }),
  /** 可交互控件检查摘要（C1～C3 契约；出包另挂 p3controls） */
  formControlsGate: () => http.get('/system/form-controls-gate', { timeout: 120000 }),
  /** 工厂级中文词表（列/表/词根；bake COMMENT 真源） */
  zhLexicon: (params) => http.get('/system/zh-lexicon', { params }),
  zhLexiconMeta: () => http.get('/system/zh-lexicon/meta', { timeout: 60000 }),
  zhLexiconMigrate: () => http.post('/system/zh-lexicon/migrate'),
  zhLexiconGaps: () => http.get('/system/zh-lexicon/gaps', { timeout: 120000 }),
  zhLexiconSuggestDrafts: () =>
    http.post('/system/zh-lexicon/suggest-drafts', null, { timeout: 120000 }),
  zhLexiconUpsert: (body) => http.put('/system/zh-lexicon', body),
  zhLexiconDelete: (id) => http.delete(`/system/zh-lexicon/${id}`),
  /** 工厂状态机话术（domain×machine×status → 徽章/按钮/空态） */
  statusCopy: (params) => http.get('/system/status-copy', { params }),
  statusCopyMeta: () => http.get('/system/status-copy/meta', { timeout: 60000 }),
  statusCopyMigrate: () => http.post('/system/status-copy/migrate'),
  statusCopyGaps: (domainId) =>
    http.get('/system/status-copy/gaps', {
      params: { domain_id: domainId },
      timeout: 120000,
    }),
  statusCopyUpsert: (body) => http.put('/system/status-copy', body),
  statusCopyDelete: (id) => http.delete(`/system/status-copy/${id}`),
  dictValues: (params) => http.get('/system/dict-values', { params }),
  dictValuesMeta: () => http.get('/system/dict-values/meta', { timeout: 60000 }),
  dictValuesMigrate: () => http.post('/system/dict-values/migrate'),
  dictValuesGaps: (domainId, skinId = '') =>
    http.get('/system/dict-values/gaps', {
      params: { domain_id: domainId, skin_id: skinId || undefined },
      timeout: 120000,
    }),
  dictValuesUpsert: (body) => http.put('/system/dict-values', body),
  dictValuesDelete: (id) => http.delete(`/system/dict-values/${id}`),
  demoScripts: (params) => http.get('/system/demo-scripts', { params }),
  demoScriptsMeta: () => http.get('/system/demo-scripts/meta', { timeout: 60000 }),
  demoScriptsMigrate: () => http.post('/system/demo-scripts/migrate'),
  demoScriptsGaps: (domainId) =>
    http.get('/system/demo-scripts/gaps', {
      params: { domain_id: domainId },
      timeout: 60000,
    }),
  demoScriptsUpsert: (body) => http.put('/system/demo-scripts', body),
  demoScriptsDelete: (id) => http.delete(`/system/demo-scripts/${id}`),

  capCards: (params) => http.get('/system/cap-cards', { params }),
  capCardsMeta: () => http.get('/system/cap-cards/meta', { timeout: 60000 }),
  capCardsMigrate: () => http.post('/system/cap-cards/migrate'),
  capCardsGaps: () => http.get('/system/cap-cards/gaps', { timeout: 60000 }),
  capCardsUpsert: (body) => http.put('/system/cap-cards', body),
  capCardsDelete: (id) => http.delete(`/system/cap-cards/${id}`),
  errorCopy: (params) => http.get('/system/error-copy', { params }),
  errorCopyMeta: () => http.get('/system/error-copy/meta', { timeout: 60000 }),
  errorCopyMigrate: () => http.post('/system/error-copy/migrate'),
  errorCopyGaps: () => http.get('/system/error-copy/gaps', { timeout: 60000 }),
  errorCopyUpsert: (body) => http.put('/system/error-copy', body),
  errorCopyDelete: (id) => http.delete(`/system/error-copy/${id}`),
  widgetHints: (params) => http.get('/system/widget-hints', { params }),
  widgetHintsMeta: () => http.get('/system/widget-hints/meta', { timeout: 60000 }),
  widgetHintsMigrate: () => http.post('/system/widget-hints/migrate'),
  widgetHintsGaps: () => http.get('/system/widget-hints/gaps', { timeout: 60000 }),
  widgetHintsUpsert: (body) => http.put('/system/widget-hints', body),
  widgetHintsDelete: (id) => http.delete(`/system/widget-hints/${id}`),
  menuMatrix: (params) => http.get('/system/menu-matrix', { params }),
  menuMatrixMeta: () => http.get('/system/menu-matrix/meta', { timeout: 60000 }),
  menuMatrixMigrate: () => http.post('/system/menu-matrix/migrate'),
  menuMatrixGaps: () => http.get('/system/menu-matrix/gaps', { timeout: 60000 }),
  menuMatrixUpsert: (body) => http.put('/system/menu-matrix', body),
  menuMatrixDelete: (id) => http.delete(`/system/menu-matrix/${id}`),
  ruleParams: (params) => http.get('/system/rule-params', { params }),
  ruleParamsMeta: () => http.get('/system/rule-params/meta', { timeout: 60000 }),
  ruleParamsMigrate: () => http.post('/system/rule-params/migrate'),
  ruleParamsGaps: () => http.get('/system/rule-params/gaps', { timeout: 60000 }),
  ruleParamsUpsert: (body) => http.put('/system/rule-params', body),
  ruleParamsDelete: (id) => http.delete(`/system/rule-params/${id}`),
  erEdgeCopy: (params) => http.get('/system/er-edge-copy', { params }),
  erEdgeCopyMeta: () => http.get('/system/er-edge-copy/meta', { timeout: 60000 }),
  erEdgeCopyMigrate: () => http.post('/system/er-edge-copy/migrate'),
  erEdgeCopyGaps: () => http.get('/system/er-edge-copy/gaps', { timeout: 60000 }),
  erEdgeCopyUpsert: (body) => http.put('/system/er-edge-copy', body),
  erEdgeCopyDelete: (id) => http.delete(`/system/er-edge-copy/${id}`),
  demoAccounts: (params) => http.get('/system/demo-accounts', { params }),
  demoAccountsMeta: () => http.get('/system/demo-accounts/meta', { timeout: 60000 }),
  demoAccountsMigrate: () => http.post('/system/demo-accounts/migrate'),
  demoAccountsGaps: () => http.get('/system/demo-accounts/gaps', { timeout: 60000 }),
  demoAccountsUpsert: (body) => http.put('/system/demo-accounts', body),
  demoAccountsDelete: (id) => http.delete(`/system/demo-accounts/${id}`),
  diagramTitles: (params) => http.get('/system/diagram-titles', { params }),
  diagramTitlesMeta: () => http.get('/system/diagram-titles/meta', { timeout: 60000 }),
  diagramTitlesMigrate: () => http.post('/system/diagram-titles/migrate'),
  diagramTitlesGaps: () => http.get('/system/diagram-titles/gaps', { timeout: 60000 }),
  diagramTitlesUpsert: (body) => http.put('/system/diagram-titles', body),
  diagramTitlesDelete: (id) => http.delete(`/system/diagram-titles/${id}`),
  thesisAbsorbMeta: () => http.get('/system/thesis-absorb/meta', { timeout: 30000 }),
  thesisAbsorbList: (params) => http.get('/system/thesis-absorb', { params, timeout: 30000 }),
  thesisAbsorbGet: (id) => http.get(`/system/thesis-absorb/${id}`, { timeout: 60000 }),
  thesisAbsorbUpload: (file, onProgress) => {
    const fd = new FormData()
    fd.append('file', file)
    return http.post('/system/thesis-absorb/upload', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: onProgress,
      ...HEAVY_OPTS,
    })
  },
  // 与上传同档：大 PDF OCR + LLM（含重试）常超过 2 分钟
  thesisAbsorbReextract: (id) =>
    http.post(`/system/thesis-absorb/${id}/reextract`, null, { ...HEAVY_OPTS }),
  thesisAbsorbPatch: (id, body) => http.patch(`/system/thesis-absorb/${id}`, body),
  thesisAbsorbFeed: (id) => http.post(`/system/thesis-absorb/${id}/feed`),
  thesisAbsorbDelete: (id) => http.delete(`/system/thesis-absorb/${id}`),
  addonSuggest: (params) => http.get('/system/addon-suggest', { params }),
  addonSuggestMeta: () => http.get('/system/addon-suggest/meta', { timeout: 60000 }),
  addonSuggestMigrate: () => http.post('/system/addon-suggest/migrate'),
  addonSuggestGaps: () => http.get('/system/addon-suggest/gaps', { timeout: 60000 }),
  addonSuggestUpsert: (body) => http.put('/system/addon-suggest', body),
  addonSuggestDelete: (id) => http.delete(`/system/addon-suggest/${id}`),
  catalog: () => http.get('/catalog'),
  sampleProposalPacks: () => http.get('/tools/sample-proposal/packs'),
  sampleProposal: (body) =>
    http.post('/tools/sample-proposal', body || {}, { timeout: 180000 }),

  // —— 答辩 PPT（终期；独立任务；PPTX 不进 ZIP）——
  // 契约见 docs/defense-ppt-module.md / docs/defense-ppt-backend.md
  getDefensePpt: (id) =>
    http.get(`/projects/${id}/defense-ppt`, { silent: true }),
  putDefensePptCover: (id, cover) =>
    http.put(`/projects/${id}/defense-ppt/cover`, cover, { silent: true }),
  generateDefensePpt: (id, body) =>
    http.post(`/projects/${id}/defense-ppt/generate`, body || {}, {
      silent: true,
      timeout: 120000,
    }),
  getDefensePptJob: (id) =>
    http.get(`/projects/${id}/defense-ppt/job`, { silent: true, ...POLL_OPTS }),
  cancelDefensePpt: (id) =>
    http.post(`/projects/${id}/defense-ppt/cancel`, null, { silent: true }),
  getDefensePptDeck: (id) =>
    http.get(`/projects/${id}/defense-ppt/deck`, { silent: true }),
  patchDefensePptPage: (id, pageId, patch) =>
    http.patch(`/projects/${id}/defense-ppt/deck/pages/${encodeURIComponent(pageId)}`, patch, {
      silent: true,
    }),
  patchDefensePptSkin: (id, body) =>
    http.patch(`/projects/${id}/defense-ppt/skin`, body || {}, { silent: true }),
  syncDefensePptBiz: (id) =>
    http.post(`/projects/${id}/defense-ppt/sync-biz`, null, { silent: true, timeout: 120000 }),
  checkDefensePpt: (id) =>
    http.post(`/projects/${id}/defense-ppt/check`, null, { silent: true }),
  defensePptExportUrl: (id) => `/api/projects/${id}/defense-ppt/export`,
  defensePptEventsUrl: (id) => `/api/projects/${id}/defense-ppt/events`,
  captureDefensePptScreenshot: (id, body) =>
    http.post(`/projects/${id}/defense-ppt/screenshots/capture-current`, body || {}, {
      silent: true,
      timeout: 120000,
    }),
  uploadDefensePptScreenshot: (id, body) =>
    http.post(`/projects/${id}/defense-ppt/screenshots/upload`, body || {}, {
      silent: true,
      timeout: 120000,
    }),
}

export default http
