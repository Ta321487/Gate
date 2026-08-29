/** Project detail page logic — extracted from ProjectDetail.vue (behavior unchanged). */
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, message, confirm } from '../../api'
import { softThemeSwatch } from '../../softThemeSwatches.js'
import {
  CHECKLIST_RESULT,
  JOB_STEP_LABELS,
  LOG_SIDES,
  defaultTabForStatus,
  detailCrumb,
  getCatalog,
  normalizeStepStatus,
  projectStatusLabel,
  projectStatusPill,
  projectIsDownloadable,
  deliveryMarkLabel,
  statusPillNode,
  stepStatusLabel,
  stepStatusMark,
  domainCascaderOptions as buildDomainCascaderOptions,
} from '../../opsShared'

export function useProjectDetail() {
const route = useRoute()
const router = useRouter()
/** 离开详情页 / 切换项目时递增，作废进行中的启动轮询，避免用空 id 请求 */
let viewEpoch = 0
const p = ref(null)
const loadError = ref('')
const loadErrorCode = ref(500)
const tab = ref('match')
const catalog = ref({
  archetypes: [],
  domains: [],
  themes_by_domain: {},
  chrome_styles: [],
  layout_shells: [],
  type_pairings: [],
  portal_home_styles: [],
})
const form = reactive({
  archetype: '',
  domain: '',
  persistence: 'jdbc',
  springSecurity: 'off',
  scene: 'campus',
  entry: '',
  theme: '',
  chrome: 'soft',
  layout: 'topbar',
  typeface: 'clean',
  portalHomeStyle: 'cards',
  llm: 'on',
  passwordHash: 'none',
})
const ack = ref(false)
const ackMainPath = ref(false)
const unlocked = ref(false)
const currentJob = ref(null)
const rt = reactive({
  backend_status: 'stopped',
  frontend_status: 'stopped',
  preview_url: null,
  backend_url: null,
  public_host: '127.0.0.1',
  backend_log_tail: '',
  frontend_log_tail: '',
})
const rtBusyBe = ref(false)
const rtBusyFe = ref(false)
const rtPendingAll = ref('')
const rtAnyBusy = computed(() => rtBusyBe.value || rtBusyFe.value)
const rtAllBusy = computed(() => rtBusyBe.value && rtBusyFe.value)
/** IDE 式：已在跑就不能再启动；全停就不能关/重启；生成中禁止启动/重启 */
const rtGenerating = computed(() => p.value?.status === 'generating')
const rtBeLive = computed(() => runtimeCanStop(rt.backend_status))
const rtFeLive = computed(() => runtimeCanStop(rt.frontend_status))
const rtAnyLive = computed(() => rtBeLive.value || rtFeLive.value)
const rtBothLive = computed(() => rtBeLive.value && rtFeLive.value)
const rtCanStartAll = computed(
  () =>
    Boolean(p.value?.workspace_path) &&
    !rtGenerating.value &&
    !rtAnyBusy.value &&
    !rtBothLive.value,
)
const rtCanStopAll = computed(
  () => Boolean(p.value?.workspace_path) && !rtAnyBusy.value && rtAnyLive.value,
)
const rtCanRestartAll = computed(() => rtCanStopAll.value && !rtGenerating.value)
const backendAddr = computed(() => {
  if (rt.backend_url) return rt.backend_url
  const host = rt.public_host || '127.0.0.1'
  const port = p.value?.backend_port
  return port ? `http://${host}:${port}` : ''
})
const frontendAddr = computed(() => {
  if (rt.preview_url) return rt.preview_url
  const host = rt.public_host || '127.0.0.1'
  const port = p.value?.frontend_port
  return port ? `http://${host}:${port}` : ''
})
const logSide = ref('job')
const logText = ref('')
const logFilter = ref('')
const logLoading = ref(false)
const logSides = LOG_SIDES
const showSpec = ref(false)
const showPreGenerate = ref(false)
const proposalDiff = ref(null)
const preGenBusy = ref(false)
const showFillPlan = ref(false)
const fillPlanLoading = ref(false)
const fillPlanRows = ref([])
const FILL_UNIT_KIND_ZH = {
  island_labels: 'Island 文案',
  island_seeds: '公告种子',
  island_entities: '实体称呼',
  island_roles: '岗位称呼',
  er_labels: 'E-R 中文',
  module_labels: '模块图',
  testcase_labels: '测试用例',
}
const fillPlanCols = [
  { title: 'Unit ID', key: 'id', width: 160, ellipsis: { tooltip: true } },
  { title: '类型', key: 'kind', width: 120 },
  { title: '状态', key: 'status', width: 88 },
  { title: '预算字符', key: 'budget_chars', width: 88 },
  { title: '来源', key: 'source_refs', ellipsis: { tooltip: true } },
]
const FILL_UNIT_STATUS_ZH = {
  pending: '待执行',
  running: '进行中',
  done: '完成',
  failed: '失败',
  skipped: '跳过',
}
const fillLiveSnap = ref(null)
const fillLiveCols = [
  { title: 'Unit', key: 'id', width: 150, ellipsis: { tooltip: true } },
  { title: '类型', key: 'kind', width: 110 },
  {
    title: '状态',
    key: 'status',
    width: 88,
    render: (r) => statusPillNode(
      FILL_UNIT_STATUS_ZH[r.status] || r.status,
      r.status === 'done'
        ? 'pill-green'
        : r.status === 'failed'
          ? 'pill-red'
          : r.status === 'running'
            ? 'pill-teal'
            : r.status === 'skipped'
              ? 'pill-neutral'
              : 'pill-neutral',
    ),
  },
]
const fillLiveRows = computed(() => {
  const units = fillLiveSnap.value?.units
  if (!units || typeof units !== 'object') return []
  return Object.values(units).map((u) => ({
    id: u.id,
    kind: FILL_UNIT_KIND_ZH[u.kind] || u.kind,
    status: u.status || 'pending',
  }))
})
const fillLiveVisible = computed(() => fillLiveRows.value.length > 0)
const fillLiveSummary = computed(() => {
  const s = fillLiveSnap.value
  if (!s?.total) return ''
  const parts = [`填岛 ${s.done || 0}/${s.total}`]
  if (s.running) parts.push(`进行中 ${s.running}`)
  if (s.failed) parts.push(`失败 ${s.failed}`)
  if (s.phase === 'done') parts.push('已合并')
  if (s.phase === 'failed') parts.push('填岛中断')
  return parts.join(' · ')
})
const fillPlanHint = computed(() => {
  if (!p.value?.workspace_path) return '生成工作区后可预览'
  if (fillPlanRows.value.length) return `共 ${fillPlanRows.value.length} 个 Unit`
  return '点击预览拆解粒度'
})
const showEr = ref(false)
const showModules = ref(false)
const showTestcases = ref(false)
const erLoading = ref(false)
const modLoading = ref(false)
const tcLoading = ref(false)
const matchBusy = ref(false)
const softSaving = ref(false)
const jobActing = ref('')
const artifactLoading = ref(false)
const showDelete = ref(false)
const keepDb = ref(false)
const deleting = ref(false)
const schema = ref(null)
const erLabelSaving = ref(false)
const apis = ref(null)
const apiSmokeBusy = ref(false)
const apiSmokeResult = ref(null)
const apiSmokeFactoryHint = ref('')
const artifactView = ref('db')
const apiQuery = ref('')
const apiSurface = ref('all')
const collapsedApis = ref({})
const erSvgSource = ref('')
const erLayoutKey = ref(0)
const erMode = ref('total')
const erEntity = ref('')
const modSvgSource = ref('')
const modLayoutKey = ref(0)
const modulesLayout = ref('biz')
const modulesMeta = ref(null)
const tcFields = ref(6)
const tcColumns = ref([])
const tcRows = ref([])
const tcMarkdown = ref('')
const tcCount = ref(0)
let pollTimer = null
let fillEventSource = null

function applyFillSnapshot(event) {
  if (!event || event.type === 'heartbeat') return
  if (event.type === 'snapshot') {
    fillLiveSnap.value = {
      phase: event.phase || 'idle',
      units: event.units || {},
      total: event.total || 0,
      done: event.done || 0,
      failed: event.failed || 0,
      running: event.running || 0,
      error: event.error || '',
    }
    if (showFillPlan.value && fillLiveRows.value.length) {
      fillPlanRows.value = fillLiveRows.value.map((r) => ({
        ...r,
        status: FILL_UNIT_STATUS_ZH[r.status] || r.status,
        budget_chars: fillLiveSnap.value?.units?.[r.id]?.budget_chars,
        source_refs: (fillLiveSnap.value?.units?.[r.id]?.source_refs || []).join(' · ') || '—',
      }))
    }
    if (['done', 'failed'].includes(event.phase)) {
      stopFillEvents()
    }
  }
}

function stopFillEvents() {
  if (fillEventSource) {
    fillEventSource.close()
    fillEventSource = null
  }
}

function startFillEvents() {
  if (!p.value?.id || fillEventSource) return
  const url = api.fillEventsUrl(p.value.id)
  const es = new EventSource(url)
  fillEventSource = es
  es.onmessage = (ev) => {
    try {
      applyFillSnapshot(JSON.parse(ev.data))
    } catch {
      /* ignore malformed frame */
    }
  }
  es.onerror = () => {
    /* EventSource 自动重连；轮询仍作兜底 */
  }
}

const planSteps = [
  { t: JOB_STEP_LABELS.parse_merge, m: '匹配与 Spec' },
  { t: JOB_STEP_LABELS.copy_bake, m: '确定性生成' },
  { t: JOB_STEP_LABELS.island_fill, m: '拆解 Unit 并发填岛' },
  { t: JOB_STEP_LABELS.build_verify, m: '编译检查' },
  { t: JOB_STEP_LABELS.gate_e2e, m: '关键路径' },
  { t: JOB_STEP_LABELS.pack, m: '检查通过后打包' },
]

const archOptions = computed(() => catalog.value.archetypes.map((x) => ({ label: x.label, value: x.id })))
const domCascaderOptions = computed(() => buildDomainCascaderOptions(catalog.value))
const themeOptions = computed(() => {
  const list = catalog.value.themes_by_domain?.[form.domain] || []
  return list.map((x) => ({ label: x.label, value: x.id }))
})
const chromeOptions = computed(() => {
  const list = catalog.value.chrome_styles || []
  return list.map((x) => ({ label: x.label, value: x.id }))
})
const layoutOptions = computed(() => {
  const list = catalog.value.layout_shells || []
  return list.map((x) => ({ label: x.label, value: x.id }))
})
function softThemeWireStyle(themeId) {
  const s = softThemeSwatch(themeId)
  return {
    '--lsw-bg': s.bg,
    '--lsw-surface': s.surface,
    '--lsw-ink': s.ink,
    '--lsw-accent': s.accent,
    '--lsw-soft': s.soft,
  }
}
const softVisualWireStyle = computed(() => softThemeWireStyle(form.theme))
const typefaceOptions = computed(() => {
  const list = catalog.value.type_pairings || []
  return list.map((x) => ({ label: x.label, value: x.id }))
})
const PORTAL_HOME_FALLBACK = [
  { label: '功能卡片首页', value: 'cards' },
  { label: '资讯侧栏首页', value: 'editorial' },
]
const portalHomeOptions = computed(() => {
  const list = catalog.value.portal_home_styles || []
  const mapped = list
    .map((x) => ({ label: x.label || x.id, value: x.id }))
    .filter((x) => !!x.value)
  return mapped.length ? mapped : PORTAL_HOME_FALLBACK
})
const passwordHashOptions = [
  { label: '明文', value: 'none' },
  { label: 'BCrypt', value: 'bcrypt' },
  { label: 'MD5', value: 'md5' },
  { label: 'SHA-256', value: 'sha256' },
]
const persistenceOptions = [
  { label: 'Spring JDBC（JdbcTemplate）', value: 'jdbc' },
  { label: 'MyBatis + PageHelper', value: 'mybatis' },
  { label: 'Spring Data JPA（Hibernate）', value: 'jpa' },
]
const securityOptions = [
  { label: '关 · 仅 Session + AdminAuth（默认）', value: 'off' },
  { label: '开 · Spring Security 过滤器链', value: 'on' },
]
function persistenceLabel(v) {
  if (v === 'mybatis') return 'MyBatis + PageHelper'
  if (v === 'jpa') return 'Spring Data JPA'
  return 'JdbcTemplate'
}
function securityLabel(v) {
  const on = v === true || v === 'on' || v === 1
  return on ? 'Spring Security' : 'Session（无过滤器链）'
}
function securityOn(v) {
  return v === true || v === 'on' || v === 1
}
const llmOptions = [
  { label: '开启 · 填充业务文案与种子数据', value: 'on' },
  { label: '关闭 · 仅使用基线生成', value: 'off' },
]

const persistenceDeviant = computed(() => {
  if (!p.value) return false
  return (form.persistence || 'jdbc') !== (p.value.recommended_persistence || 'jdbc')
})
const securityDeviant = computed(() => {
  if (!p.value) return false
  return securityOn(form.springSecurity) !== securityOn(p.value.recommended_spring_security)
})
const matchPath = computed(() => {
  const mp = p.value?.spec?.match_path
  return mp && typeof mp === 'object' ? mp : {}
})
const sceneOptions = computed(() =>
  (matchPath.value.scene_options || []).map((o) => ({
    label: o.label || o.id,
    value: o.id,
  })),
)
const entryOptions = computed(() =>
  (matchPath.value.entry_options || []).map((o) => ({
    label: o.label || o.id,
    value: o.id,
  })),
)
const pathSceneDeviant = computed(() => {
  const mp = matchPath.value
  return Boolean(mp.scene && mp.recommended_scene && mp.scene !== mp.recommended_scene)
})
const pathEntryDeviant = computed(() => {
  const mp = matchPath.value
  return Boolean(mp.entry && mp.recommended_entry && mp.entry !== mp.recommended_entry)
})
const archDomainDeviant = computed(() => {
  if (!p.value) return false
  return (
    form.archetype !== p.value.recommended_arch
    || form.domain !== p.value.recommended_domain
  )
})
const deviant = computed(() => {
  if (!p.value) return false
  return (
    archDomainDeviant.value
    || persistenceDeviant.value
    || securityDeviant.value
    || pathSceneDeviant.value
    || pathEntryDeviant.value
    || Boolean(matchPath.value.deviant)
  )
})
/** 交叉题：推荐能力路径并集（多 ARCH） */
const recommendedArchesText = computed(() => {
  const arches = p.value?.spec?.archetypes
  if (!Array.isArray(arches) || arches.length < 2) return ''
  const labels = arches.map((id) => {
    const hit = (catalog.value.archetypes || []).find((x) => x.id === id)
    return hit?.label || id
  })
  return labels.join(' + ')
})
const displayConf = computed(() => (deviant.value ? 0.41 : (p.value?.confidence || 0)))
const matchPillClass = computed(() => {
  if (deviant.value) return 'pill-red'
  if (unlocked.value) return 'pill-amber'
  return 'pill-green'
})
const matchPillText = computed(() => {
  if (deviant.value) return '已偏离推荐'
  if (unlocked.value) return '已解锁'
  return '已锁定推荐'
})
const matchWarnings = computed(() => {
  const spec = p.value?.spec || {}
  const stackWarn = spec.match_meta?.stack?.warnings
  if (Array.isArray(stackWarn) && stackWarn.length) {
    return [...stackWarn, ...((Array.isArray(spec.match_warnings) && spec.match_warnings) || [])]
  }
  if (Array.isArray(spec.match_warnings) && spec.match_warnings.length) return spec.match_warnings
  return (spec.hits || []).filter((h) => typeof h === 'string' && h.startsWith('提示：'))
})
const preGenStackWarnings = computed(() => {
  const spec = p.value?.spec || {}
  const stackWarn = spec.match_meta?.stack?.warnings
  return Array.isArray(stackWarn) ? stackWarn : []
})
const preGenTechDual = computed(() => {
  if (!p.value) return ''
  const stack = p.value.spec?.match_meta?.stack
  if (!stack || typeof stack !== 'object') return ''
  const parts = []
  const chosen = String(p.value.persistence || 'jdbc')
  const rec = String(p.value.recommended_persistence || chosen)
  if (stack.persistence_hint && stack.persistence_hint !== chosen) {
    parts.push(`持久层 · 开题：${stack.persistence_hint} · 拟选：${chosen}`)
  } else if (rec && rec !== chosen) {
    parts.push(`持久层 · 推荐：${rec} · 拟选：${chosen}`)
  }
  if (stack.security_hint != null && stack.security_hint !== p.value.spring_security) {
    parts.push(`Security · 开题：${stack.security_hint ? '是' : '否'} · 拟选：${p.value.spring_security ? '是' : '否'}`)
  }
  return parts.join(' · ')
})
const preGenReady = computed(() => {
  const d = proposalDiff.value
  if (!d) return false
  if (d.ready === true) return true
  return !!d.ok && !(d.unmatched_proposal || []).length
})
/** 易混近邻 / 关键词 ≠ 推荐时双显（周报 vs 投递等） */
const narrativeDualText = computed(() => {
  if (!p.value) return ''
  const kwArch = matchMeta.value?.keyword_arch
  const kwDom = matchMeta.value?.keyword_domain
  const recArch = p.value.recommended_arch
  const recDom = p.value.recommended_domain
  if (kwArch && kwDom && (kwArch !== recArch || kwDom !== recDom)) {
    return `关键词 ${kwArch} × ${kwDom}；系统推荐 ${recArch} × ${recDom}`
  }
  const pairMap = {
    'DOM-INTERN': ['DOM-RECRUIT', '易混近邻：招聘投递（DOM-RECRUIT）— 本题是交周报/在岗填报，不是投简历找岗'],
    'DOM-RECRUIT': ['DOM-INTERN', '易混近邻：实习周报（DOM-INTERN）— 本题是岗→投递→初筛，不是在岗周报'],
    'DOM-ACTIVITY': ['DOM-COURSE', '易混近邻：选课学分（DOM-COURSE）— 本题是活动报名占名额，不是选课'],
    'DOM-COURSE': ['DOM-ACTIVITY', '易混近邻：活动报名（DOM-ACTIVITY）— 本题是选课学分，不是社团志愿报名'],
    'DOM-ATTEND': ['DOM-EVENT', '易混近邻：健康打卡/上报（DOM-EVENT）— 本题是请销假单据，不是晨午检'],
    'DOM-EVENT': ['DOM-ATTEND', '易混近邻：请假考勤（DOM-ATTEND）— 本题是上报/随访/巡检，不是请销假'],
    'DOM-HOSPITAL': ['DOM-LOST', '易混近邻：领养认领（DOM-LOST）— 本题是挂号/预约时段，不是领养'],
    'DOM-LOST': ['DOM-HOSPITAL', '易混近邻：宠物医院挂号（DOM-HOSPITAL）— 本题是认领/领养申请，不是门诊'],
    'DOM-INSTRUMENT': ['DOM-MEETING', '易混近邻：纯场地预约（DOM-MEETING）— 本题是仪器借+机时一体'],
    'DOM-BED': ['DOM-DORM', '易混近邻：宿舍报修（DOM-DORM）— 本题是床位分配/调宿，不是报修'],
    'DOM-DORM': ['DOM-BED', '易混近邻：床位调宿（DOM-BED）— 本题是宿舍报修工单，不是分床'],
  }
  const oos = p.value.spec?.out_of_mvp || []
  if (recDom === 'DOM-COURSE' && Array.isArray(oos) && oos.some((x) => String(x).includes('排课'))) {
    return '开题拟选排课引擎 · 实包为选课占名额与冲突检测（无自动排课）'
  }
  const pair = pairMap[recDom]
  if (!pair) return ''
  const [neighbor, tip] = pair
  const alts = matchMeta.value?.alts
  const altHit = Array.isArray(alts) && alts.some((a) => a?.domain === neighbor)
  const tipHit = (matchWarnings.value || []).some(
    (w) => typeof w === 'string' && (w.includes(neighbor) || w.includes('请人工确认') || w.includes('排课')),
  )
  return altHit || tipHit ? tip : ''
})
const keywordHits = computed(() =>
  (p.value?.spec?.hits || []).filter((h) => typeof h === 'string' && !h.startsWith('提示：')),
)
function warningText(w) {
  return String(w || '').replace(/^提示：/, '')
}
const confirmHint = computed(() => {
  if (deviant.value) return '确认按当前骨架 / 领域 / 持久层 / 鉴权生成。'
  return '已核对骨架、领域与本期范围，确认后开始生成。'
})
const canDownload = computed(() => projectIsDownloadable(p.value))
const downloadZipLabel = computed(() => (p.value?.status === 'generating' ? '生成中…' : '下载 ZIP'))
const downloadBlockedReason = computed(() => p.value?.download_blocked_reason || '')
const zipLockHint = computed(() =>
  canDownload.value ? '质量检查已通过 · 可下载' : (downloadBlockedReason.value || '暂锁定'),
)
const deliveryMark = computed(() => String(p.value?.delivery_mark || 'none'))
const deliveryBusy = ref(false)
const canMarkReady = computed(() =>
  canDownload.value
  && ['generated', 'running'].includes(p.value?.status)
  && deliveryMark.value === 'none',
)
/** 已审待发暂存，或质检可下时一步标已发出 */
const canMarkDelivered = computed(() =>
  deliveryMark.value === 'ready'
  || (
    deliveryMark.value === 'none'
    && canDownload.value
    && ['generated', 'running'].includes(p.value?.status)
  ),
)
const canDownloadAndDeliver = computed(() =>
  deliveryMark.value === 'ready' && canDownload.value,
)
const canUndoDelivery = computed(() =>
  deliveryMark.value === 'ready' || deliveryMark.value === 'delivered',
)
const undoDeliveryLabel = computed(() =>
  deliveryMark.value === 'delivered' ? '撤回已发出' : '撤回待发',
)
const genSuccessBannerTitle = computed(() => {
  if (deliveryMark.value === 'delivered' || deliveryMark.value === 'ready') {
    const base = deliveryMarkLabel(deliveryMark.value)
    return genState.value === 'live' ? `${base} · 预览运行中` : base
  }
  return genState.value === 'live'
    ? '已生成 · 预览运行中'
    : '生成完成 · 质量检查已通过 · 可下载'
})
const genSuccessBannerHint = computed(() => {
  if (deliveryMark.value === 'delivered') return '已发给学生。重新生成会清掉履约标记。'
  if (deliveryMark.value === 'ready') return '人工已审过。发出时用页头「下载并发出」。'
  return '机器质检已通过。履约请用页头：直接「标记已发出」，或先「暂存待发」。'
})
const failedBannerTitle = computed(() => {
  const err = String(currentJob.value?.error || '')
  if (err.includes('质量检查未通过') || err.includes('门禁')) {
    return '质量检查未通过 · 暂不可下载'
  }
  if (err.includes('已取消')) return '任务已取消'
  return '生成失败 · 暂不可下载'
})
const rtStartBlockedReason = computed(() => {
  const base = p.value?.preview_blocked_reason || ''
  if (base) return base
  if (!rtCanStartAll.value) {
    if (rtBothLive.value) return '前后端已在运行'
    if (rtAnyBusy.value) return '启停进行中 · 请稍候'
  }
  return ''
})

const deleteBlocked = computed(() => {
  if (!p.value) return true
  if (p.value.status === 'running' || p.value.status === 'generating') return true
  if (p.value.backend_running || p.value.frontend_running) return true
  const be = rt.backend_status
  const fe = rt.frontend_status
  if (['starting', 'healthy', 'stopping'].includes(be) || ['starting', 'healthy', 'stopping'].includes(fe)) {
    return true
  }
  return false
})
const deleteBlockedReason = computed(() =>
  deleteBlocked.value ? '项目运行中或正在生成，请先停止后再删除' : '',
)

function runtimeStatusLabel(st) {
  return ({
    stopped: '已停止',
    starting: '启动中',
    stopping: '停止中',
    healthy: '正常',
    error: '异常',
  })[st] || st || '已停止'
}
function runtimeStatusPill(st) {
  return ({
    stopped: 'pill-neutral',
    starting: 'pill-amber',
    stopping: 'pill-amber',
    healthy: 'pill-green',
    error: 'pill-red',
  })[st] || 'pill-neutral'
}
function runtimeCanStop(st) {
  return st === 'healthy' || st === 'starting' || st === 'stopping'
}
function runtimeTransient(st) {
  return st === 'starting' || st === 'stopping'
}
/** 状态只在 pill；这里只展示真实日志，占位文案一律收成 — */
function runtimeLogView(st, tail) {
  if (st === 'stopped' || st === 'stopping') return '—'
  if (!tail || /^(后端|前端)?(启动|停止)中/.test(String(tail).trim())) return '—'
  return _tailLines(tail, st === 'error' ? 12 : 8)
}
function _tailLines(tail, keep) {
  const lines = String(tail).split(/\r?\n/).filter((l) => l.trim())
  return lines.slice(-keep).join('\n') || '—'
}

const statusLabel = computed(() =>
  projectStatusLabel(p.value?.status, {
    zipReady: canDownload.value,
    deliveryMark: deliveryMark.value,
    blockedReason: downloadBlockedReason.value,
    reviewStatus: p.value?.delivery_review?.review?.status || '',
  }),
)
const statusPill = computed(() =>
  projectStatusPill(p.value?.status, {
    zipReady: canDownload.value,
    deliveryMark: deliveryMark.value,
    blockedReason: downloadBlockedReason.value,
    reviewStatus: p.value?.delivery_review?.review?.status || '',
  }),
)

const jobInFlight = computed(() => {
  const st = String(currentJob.value?.status || '')
  return st === 'queued' || st === 'running'
})

const genState = computed(() => {
  if (!p.value) return 'idle'
  if (p.value.status === 'generating' || jobInFlight.value) return 'running'
  if (p.value.status === 'running') return 'live'
  if (p.value.status === 'generated') return 'success'
  if (p.value.status === 'failed') return 'failed'
  return 'idle'
})

const showJobSteps = computed(() => {
  const steps = currentJob.value?.steps || []
  if (!steps.length) return false
  if (jobInFlight.value) return true
  return ['running', 'failed', 'success', 'live'].includes(genState.value)
})

/** 重生中：工程目录在改写，导出类对照操作冻结 */
const artifactsFrozen = computed(() => genState.value === 'running')
const artifactsFrozenReason = '工程正在重新生成，完成后可再打开'
const schemaErGapCount = computed(() => Number(schema.value?.er_gap_count || 0))

/** 展示名仍含拉丁字母（与后端 looks_latin 对齐） */
function labelLooksLatin(text) {
  return /[A-Za-z]/.test(String(text || ''))
}

async function putErLabelPatch(body) {
  if (!p.value?.id || artifactsFrozen.value || erLabelSaving.value) return null
  erLabelSaving.value = true
  try {
    const res = await api.putErLabels(p.value.id, body)
    schema.value = res
    return res
  } catch (e) {
    const detail = e?.response?.data?.detail
    message.error((typeof detail === 'string' ? detail : '') || e?.message || '保存中文名失败')
    return null
  } finally {
    erLabelSaving.value = false
  }
}

async function commitTableZh(t, inputEl) {
  const el = inputEl
  const next = String(el?.value || '').trim()
  const prev = String(t?.label || '').trim()
  if (!next || next === prev) {
    if (el && t) el.value = t.label || ''
    return
  }
  if (labelLooksLatin(next)) {
    message.warning('请填纯中文短名')
    if (el) el.value = t.label || ''
    return
  }
  const ok = await putErLabelPatch({ tables: { [t.name]: next } })
  if (ok) message.success('已保存表中文名')
  else if (el) el.value = t.label || ''
}

async function commitColZh(t, c, inputEl) {
  const el = inputEl
  const next = String(el?.value || '').trim()
  const prev = String(c?.label || '').trim()
  if (!next || next === prev) {
    if (el && c) el.value = c.label || ''
    return
  }
  if (labelLooksLatin(next)) {
    message.warning('请填纯中文短名')
    if (el) el.value = c.label || ''
    return
  }
  // 角色逻辑实体（sys_user:user）列补丁归物理表，否则保存了盖不上
  const tableKey = t.role_of || t.name
  const ok = await putErLabelPatch({ columns: { [tableKey]: { [c.name]: next } } })
  if (ok) message.success('已保存列中文名')
  else if (el) el.value = c.label || ''
}

async function commitRelZh(r, inputEl) {
  const el = inputEl
  const next = String(el?.value || '').trim()
  const prev = String(r?.label || r?.name || '').trim()
  if (!next || next === prev) {
    if (el && r) el.value = r.label || r.name || ''
    return
  }
  if (labelLooksLatin(next)) {
    message.warning('请填纯中文短名')
    if (el) el.value = r.label || r.name || ''
    return
  }
  const key = r.name || `${r.left}|${r.right}|${r.via}`
  const ok = await putErLabelPatch({ relations: { [key]: next } })
  if (ok) message.success('已保存联系中文名')
  else if (el) el.value = r.label || r.name || ''
}

/** 已有工程产物（含运行中 / 失败），匹配页不再当首次门禁 */
const alreadyBaked = computed(() =>
  ['success', 'live', 'failed'].includes(genState.value),
)

const showSoftBakePanel = computed(() => {
  if (!p.value || genState.value === 'running') return false
  return !!(p.value.match_confirmed || alreadyBaked.value)
})

const softBakeHint = computed(() =>
  genState.value === 'idle'
    ? '选项即时保存；点「一键生成」写入工程'
    : '选项即时保存；点下方按钮写入工程',
)

const softApplying = ref(false)

const specText = computed(() => JSON.stringify(p.value?.spec || {}, null, 2))
const proposal = computed(() => p.value?.spec?.proposal || {})
const matchMeta = computed(() => p.value?.spec?.match_meta || {})
const matchSourceLabel = computed(() => {
  const s = matchMeta.value?.source
  if (s === 'llm') return '大模型推荐'
  if (s === 'keyword') return '关键词'
  return ''
})
const matchAltsText = computed(() => {
  const alts = matchMeta.value?.alts
  if (!Array.isArray(alts) || !alts.length) return ''
  return alts
    .map((a) => {
      const label = a.label || `${a.archetype}×${a.domain}`
      const c = typeof a.confidence === 'number' ? a.confidence.toFixed(2) : ''
      return c ? `${label}(${c})` : label
    })
    .join('；')
})
/** 统一登录无身份选择时不展示身份控件样式，避免文案打架 */
const authEntryDisplay = computed(() => {
  const spec = p.value?.spec || {}
  const modeLabel = spec.auth_entry_mode_label || '—'
  const mode = spec.auth_entry_mode
  const needWidget = mode === 'role_pick' || mode === 'split_entry'
  if (needWidget && spec.auth_role_widget_label) {
    return `${modeLabel} · ${spec.auth_role_widget_label}`
  }
  return modeLabel
})
const zipFileName = computed(() => {
  const name = p.value?.spec?.zip_name || p.value?.spec?.match_meta?.zip_name
  return (typeof name === 'string' && name.endsWith('.zip')) ? name : 'thesis-app.zip'
})
/** Spec 角色文案：schema.roles / staff_posts[].label，不写死中文 */
const roleSpecText = computed(() => {
  const roles = p.value?.spec?.roles || []
  if (!roles.length) return '—'
  const byId = p.value?.spec?.schema?.roles || {}
  const posts = Array.isArray(byId.staff_posts) ? byId.staff_posts : []
  const postLabel = Object.fromEntries(
    posts.filter((x) => x?.id).map((x) => [x.id, x.label || x.id]),
  )
  return roles
    .map((id) => {
      const label = postLabel[id] || byId[id]?.label
      const kind = posts.find((x) => x?.id === id)?.kind
      const kindZh = kind === 'worker' ? '员工' : kind === 'clerk' ? '子管理' : ''
      if (label && kindZh) return `${id}（${label}·${kindZh}）`
      return label ? `${id}（${label}）` : id
    })
    .join('、')
})
const filteredLog = computed(() => {
  const q = logFilter.value.trim().toLowerCase()
  if (!q) return logText.value || '（无日志）'
  return logText.value.split('\n').filter((l) => l.toLowerCase().includes(q)).join('\n') || '（无匹配）'
})

const gateCols = [
  { title: '级别', key: 'level', width: 80, render: (r) => statusPillNode(r.level, 'pill-neutral') },
  { title: '检查项', key: 'label' },
  {
    title: '结果',
    key: 'ok',
    width: 100,
    render: (r) => statusPillNode(r.ok ? '通过' : '未通过', r.ok ? 'pill-green' : 'pill-red'),
  },
  { title: '说明', key: 'desc' },
]
const gateRows = computed(() => {
  const g = p.value?.gates || {}
  // 含 p3c/p3d/accept：否则 overall 被这些项卡住时 UI 看不见原因
  const keys = ['p0a', 'p0b', 'p1', 'p2', 'p3a', 'p3b', 'p3t', 'p3s', 'p3q', 'p3c', 'p3d', 'accept']
  const levels = {
    p0a: 'P0', p0b: 'P0', p1: 'P1', p2: 'P2',
    p3a: 'P3', p3b: 'P3', p3t: 'P3', p3s: 'P3', p3q: 'P3', p3c: 'P3', p3d: 'P3', accept: 'P3',
  }
  return keys
    .filter((k) => g[k] != null)
    .map((k) => ({
      key: k,
      level: levels[k] || 'P3',
      label: g[k]?.label || k,
      ok: !!g[k]?.ok,
      desc: g[k]?.desc || '',
    }))
})
const checkCols = [
  { title: '清单项', key: 'name' },
  {
    title: '实现状态',
    key: 'result',
    render: (r) => {
      const m = CHECKLIST_RESULT[r.result] || CHECKLIST_RESULT.pending
      return statusPillNode(m.label, m.pill)
    },
  },
  {
    title: '说明',
    key: 'status',
    render: (r) => {
      // status 若只是 result 的英文 key，不再重复展示
      if (!r.status || CHECKLIST_RESULT[r.status]) return '—'
      return String(r.status)
    },
  },
]
const checkRows = computed(() => (p.value?.checklist || []).map((x) => ({
  name: x.name,
  result: x.result || (x.status === 'out_of_mvp' ? 'out_of_mvp' : 'pending'),
  status: x.status,
})))

/** 开：varchar(60)；关：类型 / 长度 分列 */
const TYPE_PAREN_KEY = 'gf-ops-schema-type-paren'
const typeParenMode = ref(
  (() => {
    try {
      const v = localStorage.getItem(TYPE_PAREN_KEY)
      if (v === '0' || v === 'false') return false
    } catch { /* ignore */ }
    return true
  })(),
)
watch(typeParenMode, (v) => {
  try {
    localStorage.setItem(TYPE_PAREN_KEY, v ? '1' : '0')
  } catch { /* ignore */ }
})

/** 解析 MySQL 类型 → 标准小写 + 可选长度参数 */
function parseMysqlType(raw) {
  const s = String(raw || '').trim()
  const m = s.match(/^([a-zA-Z][a-zA-Z0-9_]*)\s*(?:\(([^)]*)\))?/)
  if (!m) {
    const base = s.toLowerCase()
    return { base, len: '', full: base }
  }
  const base = m[1].toLowerCase()
  const len = (m[2] || '').replace(/\s+/g, '').trim()
  return { base, len, full: len ? `${base}(${len})` : base }
}

/**
 * 单表复制：制表符分隔，可贴进 Word「文本转换成表格」。
 * 随 typeParenMode：合并类型 或 类型/长度分列。
 */
function tableCopyText(t) {
  if (!t) return ''
  const title = t.label && t.label !== t.name
    ? `表 ${t.label}（${t.name}）`
    : `表 ${t.name}`
  const paren = typeParenMode.value
  const rows = paren
    ? [['字段名', '中文名', '数据类型']]
    : [['字段名', '中文名', '类型', '长度']]
  for (const c of t.columns || []) {
    const { base, len, full } = parseMysqlType(c.type)
    if (paren) {
      rows.push([c.name || '', c.label || c.name || '', full])
    } else {
      rows.push([c.name || '', c.label || c.name || '', base, len])
    }
  }
  const body = rows.map((cols) => cols.join('\t')).join('\n')
  return `${title}\n\n${body}`
}

/** 表卡片折叠（点表头空白处切换；复制按钮自带 stop） */
const collapsedTables = ref({})
function isTableCollapsed(name) {
  return !!collapsedTables.value[name]
}
function toggleTable(name) {
  collapsedTables.value = {
    ...collapsedTables.value,
    [name]: !collapsedTables.value[name],
  }
}

function formatSize(n) {
  if (!n) return '—'
  if (n < 1024) return n + ' B'
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + ' KB'
  return (n / 1024 / 1024).toFixed(1) + ' MB'
}

function viewActive(projectId, epoch) {
  return epoch === viewEpoch && route.params.id === projectId
}

async function load({ syncTab = false, lite = false, id: idOpt } = {}) {
  const id = idOpt || route.params.id
  loadError.value = ''
  if (!id || id === 'undefined' || id === 'null') {
    p.value = null
    detailCrumb.value = ''
    loadErrorCode.value = 404
    loadError.value = '项目 ID 无效'
    return
  }
  try {
    if (
      !lite
      && (
        !catalog.value.archetypes.length
        || !(catalog.value.portal_home_styles || []).length
      )
    ) {
      catalog.value = await getCatalog({
        force: !(catalog.value.portal_home_styles || []).length
          && !!catalog.value.archetypes.length,
      })
    }
    // 轮询用短超时静默接口：后端 reload 时不弹错、不卡 60s
    p.value = lite ? await api.getProjectPoll(id) : await api.getProject(id)
    detailCrumb.value = p.value.title || ''
    pollSyncHint.value = ''
    pollFailStreak.value = 0
    if (!lite) {
      form.archetype = p.value.archetype
      form.domain = p.value.domain
      form.persistence = p.value.persistence || p.value.spec?.persistence || 'jdbc'
      form.springSecurity = securityOn(p.value.spring_security ?? p.value.spec?.spring_security) ? 'on' : 'off'
      form.scene = p.value.spec?.match_path?.scene || 'campus'
      form.entry = p.value.spec?.match_path?.entry || ''
      form.theme = p.value.theme
      form.chrome = p.value.spec?.chrome || 'soft'
      form.layout = p.value.spec?.layout || 'topbar'
      form.typeface = p.value.spec?.typeface || 'clean'
      form.portalHomeStyle = p.value.spec?.portal_home_style || 'cards'
      form.llm = p.value.llm_enabled ? 'on' : 'off'
      form.passwordHash = p.value.password_hash || 'none'
      unlocked.value = !p.value.match_locked
      ack.value = p.value.match_confirmed
      ackMainPath.value = p.value.match_confirmed
    }
    // 仅进入/切项目时同步主 tab；轮询禁止强切，否则无法停在日志页
    if (syncTab) tab.value = defaultTabForStatus(p.value.status)
    if (!lite && p.value.workspace_path && tab.value === 'runtime') await refreshRuntime(id)
    await refreshJob({ silent: lite })
    // schema / apis 只在产物 Tab 拉，避免生成轮询疯狂刷
    if (!lite && tab.value === 'artifacts') await loadArtifactView()
  } catch (e) {
    if (lite) {
      pollFailStreak.value += 1
      if (pollFailStreak.value >= 2) {
        pollSyncHint.value = '状态同步暂时中断（后端可能在重载），后台任务仍在跑，自动重试中…'
      }
      return
    }
    p.value = null
    detailCrumb.value = ''
    const status = e?.response?.status
    loadErrorCode.value = status === 404 ? 404 : 500
    const detail = e?.response?.data?.detail
    loadError.value = (typeof detail === 'string' ? detail : '') || e?.message || '加载失败'
  }
}

async function reload() {
  stopPoll()
  fillLiveSnap.value = null
  await load({ syncTab: true })
  if (p.value?.status === 'generating') startPoll()
}

async function loadSchema() {
  if (!p.value?.workspace_path) {
    schema.value = null
    return
  }
  artifactLoading.value = true
  try {
    schema.value = await api.getSchema(p.value.id)
  } catch {
    schema.value = null
  } finally {
    artifactLoading.value = false
  }
}

async function loadApis() {
  if (!p.value?.workspace_path) {
    apis.value = null
    return
  }
  artifactLoading.value = true
  try {
    apis.value = await api.getApis(p.value.id)
  } catch {
    apis.value = null
  } finally {
    artifactLoading.value = false
  }
}

function smokeStatusLabel(row) {
  if (!row) return '—'
  if (row.skip || row.error_source === 'skip') return '跳过'
  if (row.layer === 'reachability' || row.reachable) {
    if (!row.ok) return '失败'
    return '可达'
  }
  if (row.ok) return '通过'
  return '失败'
}

function smokePillClass(row) {
  if (!row) return 'pill-neutral'
  if (row.skip || row.error_source === 'skip') return 'pill-neutral'
  if (!row.ok) {
    if (row.error_source === 'factory') return 'pill-amber'
    return 'pill-red'
  }
  if ((row.layer === 'reachability' || row.reachable) && row.business_ok === false) {
    return 'pill-amber'
  }
  return 'pill-green'
}

function smokeRowClass(row) {
  if (!row) return ''
  if (row.skip || row.error_source === 'skip') return 'smoke-row-skip'
  if (row.error_source === 'factory' && !row.ok) return 'smoke-row-factory'
  if (row.error_source === 'student' && !row.ok) return 'smoke-row-student'
  if ((row.layer === 'reachability' || row.reachable) && row.business_ok === false) {
    return 'smoke-row-biz'
  }
  return ''
}

function smokeDetailText(row) {
  if (!row) return ''
  if (row.detail) return row.detail
  const body = row.student_body
  if (body && typeof body === 'object') {
    const data = body.data
    if (
      data &&
      typeof data === 'object' &&
      data.message != null &&
      (data.ok === false || body.message === 'ok' || body.message == null)
    ) {
      return String(data.message)
    }
    if (body.message != null && String(body.message) !== 'ok') {
      return String(body.message)
    }
    try {
      return typeof body === 'string' ? body : ''
    } catch {
      return ''
    }
  }
  if (row.http_status && !(row.layer === 'reachability' || row.reachable)) {
    return `HTTP ${row.http_status}`
  }
  return ''
}

function smokeDetailFromAxios(err) {
  const d = err?.response?.data?.detail
  if (d && typeof d === 'object') return d
  if (typeof d === 'string') return { message: d, error_source: 'factory' }
  return { message: err?.message || '冒烟请求失败', error_source: 'factory' }
}

async function runApiSmoke() {
  if (!p.value?.id || apiSmokeBusy.value) return
  apiSmokeBusy.value = true
  apiSmokeFactoryHint.value = ''
  apiSmokeResult.value = null
  try {
    const res = await api.smokeStudentApis(p.value.id)
    apiSmokeResult.value = res
  } catch (err) {
    const d = smokeDetailFromAxios(err)
    if (d.need_runtime || err?.response?.status === 409) {
      apiSmokeFactoryHint.value = d.message || '请先到运行页启动前后端预览'
    } else {
      apiSmokeFactoryHint.value = d.message || '冒烟失败'
    }
  } finally {
    apiSmokeBusy.value = false
  }
}

async function loadArtifactView() {
  if (artifactView.value === 'api') await loadApis()
  else if (artifactView.value === 'db' || artifactView.value === 'thesis') await loadSchema()
  else {
    // 门禁数据已在项目上；顺带预热 schema
    await loadSchema()
  }
}

function onArtifactView(name) {
  if (name === 'api') loadApis()
  else if (name === 'db' || name === 'thesis') loadSchema()
}

function goArtifacts(view = 'db') {
  artifactView.value = view
  tab.value = 'artifacts'
  loadArtifactView()
}

function isApiCollapsed(name) {
  return !!collapsedApis.value[name]
}

function toggleApi(name) {
  collapsedApis.value = {
    ...collapsedApis.value,
    [name]: !collapsedApis.value[name],
  }
}

const filteredApiGroups = computed(() => {
  const inv = apis.value
  if (!inv?.controllers?.length) return []
  const q = (apiQuery.value || '').trim().toLowerCase()
  const surface = apiSurface.value
  const groups = []
  for (const c of inv.controllers) {
    const endpoints = (c.endpoints || []).filter((ep) => {
      if (surface !== 'all' && ep.surface !== surface) return false
      if (!q) return true
      const blob = `${ep.method} ${ep.path} ${ep.handler} ${(ep.flow_keys || []).join(' ')} ${c.controller}`.toLowerCase()
      return blob.includes(q)
    })
    if (endpoints.length) groups.push({ ...c, endpoints })
  }
  return groups
})

function apiGroupCopyText(g) {
  return (g.endpoints || [])
    .map((ep) => `${ep.method} ${ep.path}`)
    .join('\n')
}

const apiCopyText = computed(() => {
  const groups = filteredApiGroups.value
  if (!groups.length) return ''
  return groups.map((g) => apiGroupCopyText(g)).filter(Boolean).join('\n')
})

async function fetchErSvg() {
  if (!p.value) return ''
  const params = { mode: erMode.value }
  if (erMode.value === 'part' && erEntity.value) params.entity = erEntity.value
  const res = await fetch(`${api.erSvgUrl(p.value.id, params)}&t=${Date.now()}`)
  if (!res.ok) throw new Error('er svg')
  return await res.text()
}

const erEntityOptions = computed(() =>
  (schema.value?.tables || []).map((t) => ({
    value: t.name,
    label: t.label && t.label !== t.name ? `${t.label}（${t.name}）` : t.name,
  })),
)

const erDownloadBase = computed(() => {
  const id = p.value?.id || 'er'
  if (erMode.value === 'part') {
    const ent = erEntity.value || 'entity'
    const lab = (schema.value?.tables || []).find((t) => t.name === ent)?.label
    const tag = lab && lab !== ent ? lab : ent
    return `${id}-er-分图-${tag}`
  }
  return `${id}-er-总图`
})

const modulesOk = computed(() => !!modulesMeta.value?.root || !!schema.value)

const modDownloadBase = computed(() => {
  const id = p.value?.id || 'modules'
  const title = modulesMeta.value?.title || '功能模块图'
  const tag = modulesLayout.value === 'side' ? '按端' : '按业务'
  return `${id}-模块图-${tag}-${title}`
})

async function fetchModSvg() {
  if (!p.value) return ''
  const url = `${api.modulesSvgUrl(p.value.id, { layout: modulesLayout.value })}&t=${Date.now()}`
  const res = await fetch(url)
  if (!res.ok) throw new Error('modules svg')
  return await res.text()
}

async function openFillPlan() {
  if (!p.value?.workspace_path || fillPlanLoading.value) return
  fillPlanLoading.value = true
  try {
    const res = await api.getFillPlan(p.value.id)
    const plan = res?.data?.plan || res?.plan
    const units = plan?.units || []
    fillPlanRows.value = units.map((u) => ({
      id: u.id,
      kind: FILL_UNIT_KIND_ZH[u.kind] || u.kind,
      status: FILL_UNIT_STATUS_ZH[u.status] || u.status || '—',
      budget_chars: u.budget_chars,
      source_refs: (u.source_refs || []).join(' · ') || '—',
    }))
    showFillPlan.value = true
  } catch (e) {
    message.error(e?.response?.data?.detail || e?.message || '无法加载填岛计划')
  } finally {
    fillPlanLoading.value = false
  }
}

async function openModules() {
  if (!p.value || modLoading.value || artifactsFrozen.value) return
  modLoading.value = true
  try {
    modulesMeta.value = await api.getModules(p.value.id, { layout: modulesLayout.value })
    modSvgSource.value = await fetchModSvg()
    modLayoutKey.value += 1
    showModules.value = true
  } catch {
    message.error('无法加载功能模块图')
  } finally {
    modLoading.value = false
  }
}

async function reloadModSvg() {
  if (!p.value || modLoading.value) return
  modLoading.value = true
  try {
    modulesMeta.value = await api.getModules(p.value.id, { layout: modulesLayout.value })
    modSvgSource.value = await fetchModSvg()
    modLayoutKey.value += 1
  } catch {
    message.error('无法重新加载模块图')
  } finally {
    modLoading.value = false
  }
}

async function onModulesLayout(v) {
  modulesLayout.value = v === 'side' ? 'side' : 'biz'
  await reloadModSvg()
}

const tcDownloadBase = computed(() => {
  const id = p.value?.id || 'tc'
  const title = modulesMeta.value?.title || schema.value?.title || '测试用例'
  return `${id}-测试用例-${tcFields.value}字段-${title}`
})

async function reloadTestcases() {
  if (!p.value || tcLoading.value) return
  tcLoading.value = true
  try {
    const data = await api.getTestcases(p.value.id, { fields: tcFields.value })
    tcColumns.value = data.columns || []
    tcRows.value = data.rows || []
    tcMarkdown.value = data.markdown || ''
    tcCount.value = data.count || 0
    if (data.fields) tcFields.value = data.fields
  } catch {
    message.error('无法加载测试用例')
  } finally {
    tcLoading.value = false
  }
}

async function openTestcases() {
  if (!p.value || tcLoading.value || artifactsFrozen.value) return
  await reloadTestcases()
  if (tcRows.value.length || tcColumns.value.length) {
    showTestcases.value = true
  }
}

async function onTcFields(v) {
  const n = Number(v)
  tcFields.value = [5, 6, 7, 8, 9].includes(n) ? n : 6
  await reloadTestcases()
}

async function openEr() {
  if (!p.value || erLoading.value || artifactsFrozen.value) return
  if (!erEntity.value && schema.value?.tables?.length) {
    erEntity.value = schema.value.tables[0].name
  }
  erLoading.value = true
  try {
    erSvgSource.value = await fetchErSvg()
    erLayoutKey.value += 1
    showEr.value = true
  } catch {
    message.error('无法加载 E-R 图')
  } finally {
    erLoading.value = false
  }
}

async function reloadErSvg() {
  if (!p.value || erLoading.value) return
  erLoading.value = true
  try {
    erSvgSource.value = await fetchErSvg()
    erLayoutKey.value += 1
  } catch {
    message.error('无法重新加载 E-R 图')
  } finally {
    erLoading.value = false
  }
}

async function onErMode(v) {
  erMode.value = v === 'part' ? 'part' : 'total'
  if (erMode.value === 'part' && !erEntity.value && schema.value?.tables?.length) {
    erEntity.value = schema.value.tables[0].name
  }
  await reloadErSvg()
}

async function onErEntity(v) {
  erEntity.value = v || ''
  if (erMode.value === 'part') await reloadErSvg()
}

async function refreshJob({ silent = false } = {}) {
  try {
    const jobs = silent ? await api.listJobsPoll() : await api.listJobs()
    currentJob.value = jobs.find((j) => j.project_id === route.params.id) || null
  } catch (e) {
    if (!silent) throw e
  }
}

async function refreshRuntime(projectId) {
  const id = projectId || route.params.id
  if (!id || id === 'undefined' || id === 'null') return
  let data
  try {
    data = await api.runtime(id)
  } catch {
    return
  }
  if (route.params.id !== id) return
  rt.preview_url = data.preview_url || null
  rt.backend_url = data.backend_url || null
  rt.public_host = data.public_host || '127.0.0.1'
  if (p.value && p.value.id === id) {
    p.value.backend_port = data.backend_port || 0
    p.value.frontend_port = data.frontend_port || 0
    if (data.project_status) {
      p.value.status = data.project_status
      p.value.backend_running = ['starting', 'healthy'].includes(data.backend_status)
      p.value.frontend_running = ['starting', 'healthy'].includes(data.frontend_status)
    }
  }
  rt.backend_log_tail = data.backend_log_tail || ''
  rt.frontend_log_tail = data.frontend_log_tail || ''
  const be = data.backend_status || 'stopped'
  const fe = data.frontend_status || 'stopped'
  // 仅忙碌的那一侧保留中间态，另一侧照常刷新
  if (rtBusyBe.value) {
    if (rt.backend_status === 'stopping') {
      rt.backend_status = be === 'stopped' ? 'stopped' : 'stopping'
    } else if (rt.backend_status === 'starting') {
      rt.backend_status = be === 'stopped' ? 'starting' : be
    } else {
      rt.backend_status = be
    }
  } else {
    rt.backend_status = be
  }
  if (rtBusyFe.value) {
    if (rt.frontend_status === 'stopping') {
      rt.frontend_status = fe === 'stopped' ? 'stopped' : 'stopping'
    } else if (rt.frontend_status === 'starting') {
      rt.frontend_status = fe === 'stopped' ? 'starting' : fe
    } else {
      rt.frontend_status = fe
    }
  } else {
    rt.frontend_status = fe
  }
}

async function toggleUnlock() {
  if (matchBusy.value) return
  if (!unlocked.value) {
    const ok = await confirm('解锁后可调整骨架、领域与持久层。确认解锁？', {
      title: '解锁匹配',
      type: 'warning',
      positiveText: '解锁',
    })
    if (!ok) return
    matchBusy.value = true
    try {
      await api.patchMatch(p.value.id, { unlock: true })
      unlocked.value = true
      message.success('已解锁')
      await load()
    } finally {
      matchBusy.value = false
    }
  } else {
    if (deviant.value) {
      message.warning('已偏离推荐，请先恢复推荐再锁定')
      return
    }
    matchBusy.value = true
    try {
      await api.patchMatch(p.value.id, { unlock: false })
      unlocked.value = false
      message.success('已重新锁定')
      await load()
    } finally {
      matchBusy.value = false
    }
  }
}

async function resetMatch() {
  if (matchBusy.value) return
  matchBusy.value = true
  try {
    p.value = await api.patchMatch(p.value.id, { reset: true })
    form.archetype = p.value.archetype
    form.domain = p.value.domain
    form.persistence = p.value.persistence || 'jdbc'
    form.springSecurity = securityOn(p.value.spring_security) ? 'on' : 'off'
    form.scene = p.value.spec?.match_path?.scene || 'campus'
    form.entry = p.value.spec?.match_path?.entry || ''
    form.theme = p.value.theme
    form.chrome = p.value.spec?.chrome || 'soft'
    form.layout = p.value.spec?.layout || 'topbar'
    form.typeface = p.value.spec?.typeface || 'clean'
    form.portalHomeStyle = p.value.spec?.portal_home_style || 'cards'
    form.passwordHash = p.value.password_hash || 'none'
    unlocked.value = false
    ack.value = false
    ackMainPath.value = false
    message.success('已恢复推荐')
  } finally {
    matchBusy.value = false
  }
}

async function onArchDomChange() {
  if (matchBusy.value) return
  matchBusy.value = true
  try {
    p.value = await api.patchMatch(p.value.id, {
      archetype: form.archetype,
      domain: form.domain,
      persistence: form.persistence,
      spring_security: securityOn(form.springSecurity),
    })
    form.theme = p.value.theme
    form.chrome = p.value.spec?.chrome || form.chrome
    form.layout = p.value.spec?.layout || form.layout
    form.typeface = p.value.spec?.typeface || form.typeface
    form.portalHomeStyle = p.value.spec?.portal_home_style || form.portalHomeStyle
    form.persistence = p.value.persistence || form.persistence
    form.springSecurity = securityOn(p.value.spring_security) ? 'on' : 'off'
    form.scene = p.value.spec?.match_path?.scene || form.scene
    form.entry = p.value.spec?.match_path?.entry || ''
    ack.value = false
    ackMainPath.value = false
  } catch {
    form.archetype = p.value.archetype
    form.domain = p.value.domain
    form.persistence = p.value.persistence || 'jdbc'
    form.springSecurity = securityOn(p.value.spring_security) ? 'on' : 'off'
    form.theme = p.value.theme
    form.chrome = p.value.spec?.chrome || form.chrome
    form.layout = p.value.spec?.layout || form.layout
    form.typeface = p.value.spec?.typeface || form.typeface
    form.portalHomeStyle = p.value.spec?.portal_home_style || form.portalHomeStyle
    form.scene = p.value.spec?.match_path?.scene || form.scene
    form.entry = p.value.spec?.match_path?.entry || form.entry
  } finally {
    matchBusy.value = false
  }
}

async function onPathChange() {
  if (matchBusy.value) return
  matchBusy.value = true
  try {
    const body = { scene: form.scene }
    if (entryOptions.value.length) body.entry = form.entry
    p.value = await api.patchMatch(p.value.id, body)
    form.scene = p.value.spec?.match_path?.scene || form.scene
    form.entry = p.value.spec?.match_path?.entry || form.entry
    ack.value = false
    ackMainPath.value = false
  } catch {
    form.scene = p.value.spec?.match_path?.scene || form.scene
    form.entry = p.value.spec?.match_path?.entry || form.entry
  } finally {
    matchBusy.value = false
  }
}

async function saveSoft() {
  if (softSaving.value) return
  softSaving.value = true
  try {
    p.value = await api.patchMatch(p.value.id, {
      theme: form.theme,
      chrome: form.chrome,
      layout: form.layout,
      typeface: form.typeface,
      portal_home_style: form.portalHomeStyle,
      llm_enabled: form.llm === 'on',
      password_hash: form.passwordHash,
    })
    message.success('已保存')
  } finally {
    softSaving.value = false
  }
}

async function confirmMatch() {
  if (matchBusy.value) return
  if (matchPath.value.needs_path_ack && !ackMainPath.value) {
    message.warning('请先勾选「主路径已核对」，或解锁后选择入口')
    return
  }
  if (deviant.value) {
    const ok = await confirm('当前已偏离系统推荐。确认仍按当前骨架、领域、身份入口与持久层生成？', {
      title: '偏离推荐确认',
      type: 'warning',
    })
    if (!ok) return
  }
  matchBusy.value = true
  try {
    p.value = await api.patchMatch(p.value.id, {
      confirm: true,
      ack: true,
      ack_main_path: Boolean(ackMainPath.value || !matchPath.value.needs_path_ack),
    })
    unlocked.value = false
    message.success(deviant.value ? '已按当前选择确认' : '已确认匹配')
    tab.value = 'generate'
  } finally {
    matchBusy.value = false
  }
}

async function startGenerate() {
  if (softApplying.value) return
  if (p.value?.source_path || p.value?.source_filename) {
    preGenBusy.value = true
    try {
      proposalDiff.value = await api.getProposalDiff(p.value.id)
      showPreGenerate.value = true
    } catch (e) {
      message.error(e?.response?.data?.detail || e?.message || '加载开题措辞核对失败')
    } finally {
      preGenBusy.value = false
    }
    return
  }
  await runGenerateJob()
}

async function confirmPreGenerate() {
  if (!p.value?.id || preGenBusy.value) return
  preGenBusy.value = true
  try {
    await runGenerateJob({ confirmDiff: true })
    showPreGenerate.value = false
  } catch (e) {
    message.error(e?.response?.data?.detail || e?.message || '启动生成失败')
  } finally {
    preGenBusy.value = false
  }
}

async function runGenerateJob(opts = {}) {
  if (softApplying.value) {
    message.info('生成请求进行中，请稍候')
    return
  }
  softApplying.value = true
  try {
    const res = await api.generate(p.value.id, { confirmDiff: !!opts.confirmDiff })
    message.success(res.message || '已启动生成')
    const jobId = res?.data?.job_id
    if (jobId) {
      try {
        currentJob.value = await api.getJob(jobId)
      } catch {
        /* listJobs 兜底 */
      }
    }
    await refreshJob()
    tab.value = 'generate'
    startPoll()
    await load({ syncTab: false, lite: true })
  } catch (e) {
    message.error(e?.response?.data?.detail || e?.message || '启动生成失败')
    throw e
  } finally {
    softApplying.value = false
  }
}

async function cancelCurrent() {
  if (!currentJob.value || jobActing.value) return
  const ok = await confirm('确认取消该生成任务？进行中的步骤将中止。', {
    title: '取消任务',
    type: 'warning',
    positiveText: '确认取消',
  })
  if (!ok) return
  jobActing.value = 'cancel'
  try {
    await api.cancelJob(currentJob.value.id)
    message.success('已取消')
    await load()
  } finally {
    jobActing.value = ''
  }
}

async function retryCurrent() {
  if (jobActing.value) return
  if (!currentJob.value) {
    await startGenerate()
    return
  }
  jobActing.value = 'retry'
  try {
    const res = await api.retryJob(currentJob.value.id)
    message.success(res?.message || '已从失败步骤续跑')
    await load()
    startPoll()
  } finally {
    jobActing.value = ''
  }
}

function downloadZip() {
  if (!canDownload.value) {
    message.error(downloadBlockedReason.value || '质量检查未通过 · 暂不可下载交付包')
    if (p.value?.status !== 'generating') goArtifacts('gates')
    return
  }
  window.open(api.downloadUrl(p.value.id), '_blank')
}

async function markDelivery(mark) {
  if (!p.value || deliveryBusy.value) return
  deliveryBusy.value = true
  try {
    const detail = await api.patchDelivery(p.value.id, mark)
    p.value = detail
    message.success(
      mark === 'delivered' || mark === 'ready'
        ? `已标记为${deliveryMarkLabel(mark)}`
        : '已清除履约标记',
    )
  } finally {
    deliveryBusy.value = false
  }
}

async function downloadAndDeliver() {
  downloadZip()
  await markDelivery('delivered')
}

async function undoDelivery() {
  const next = deliveryMark.value === 'delivered' ? 'ready' : 'none'
  await markDelivery(next)
}

function onDelete() {
  if (deleteBlocked.value) {
    message.warning(deleteBlockedReason.value || '请先停止运行后再删除')
    return
  }
  keepDb.value = false
  showDelete.value = true
}

async function confirmDelete() {
  if (!p.value || deleting.value) return false
  deleting.value = true
  try {
    const res = await api.deleteProject(p.value.id, { keepDb: keepDb.value })
    message.success(res?.message || '已删除')
    showDelete.value = false
    router.push('/')
    return true
  } catch (e) {
    message.error(e?.response?.data?.detail || e?.message || '删除失败')
    return false
  } finally {
    deleting.value = false
  }
}

async function rtAction(side, action) {
  const projectId = p.value?.id
  if (!projectId) return
  if (action === 'start' || action === 'restart') {
    const blocked = p.value?.preview_blocked_reason
    if (blocked) {
      message.warning(blocked)
      return
    }
  }
  const epoch = viewEpoch
  const touchBe = side === 'all' || side === 'backend'
  const touchFe = side === 'all' || side === 'frontend'
  if ((touchBe && rtBusyBe.value) || (touchFe && rtBusyFe.value)) return
  if (touchBe) rtBusyBe.value = true
  if (touchFe) rtBusyFe.value = true
  if (side === 'all') rtPendingAll.value = action

  if (action === 'start' || action === 'restart') {
    if (touchBe) rt.backend_status = 'starting'
    if (touchFe) rt.frontend_status = 'starting'
  } else if (action === 'stop') {
    if (touchBe) rt.backend_status = 'stopping'
    if (touchFe) rt.frontend_status = 'stopping'
  }
  try {
    await api.runtimeAction(projectId, side, action)
    if (!viewActive(projectId, epoch)) return
    await load({ id: projectId })
    if (!viewActive(projectId, epoch)) return
    const deadline = Date.now() + (action === 'stop' ? 8000 : 90000)
    while (Date.now() < deadline && viewActive(projectId, epoch) && tab.value === 'runtime') {
      await refreshRuntime(projectId)
      if (_runtimeSettled(side, action)) break
      await new Promise((r) => setTimeout(r, 700))
    }
  } finally {
    if (touchBe) rtBusyBe.value = false
    if (touchFe) rtBusyFe.value = false
    if (side === 'all') rtPendingAll.value = ''
    if (viewActive(projectId, epoch) && tab.value === 'runtime') {
      await refreshRuntime(projectId)
    }
  }
}

function _runtimeSettled(side, action) {
  const be = rt.backend_status
  const fe = rt.frontend_status
  const beDone = be !== 'starting' && be !== 'stopping'
  const feDone = fe !== 'starting' && fe !== 'stopping'
  if (side === 'backend') return beDone
  if (side === 'frontend') return feDone
  if (action === 'stop') return be === 'stopped' && fe === 'stopped'
  return beDone && feDone
}

function openPreview() {
  if (rt.frontend_status !== 'healthy') {
    message.warning('前端未就绪，请先启动并等待可访问')
    return
  }
  const url = rt.preview_url || frontendAddr.value
  if (url) {
    window.open(url, '_blank')
    return
  }
  message.warning('前端未就绪，请先启动并等待可访问')
}

let logReqSeq = 0
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

let pollInFlight = false
const pollSyncHint = ref('')
const pollFailStreak = ref(0)

function startPoll() {
  stopPoll()
  pollSyncHint.value = ''
  pollFailStreak.value = 0
  if (p.value?.status === 'generating') startFillEvents()
  pollTimer = setInterval(async () => {
    if (pollInFlight) return
    pollInFlight = true
    try {
      // 轻量轮询：只刷项目状态/Job/日志，不拉 catalog/schema
      await load({ syncTab: false, lite: true })
      if (tab.value === 'logs') await loadLog(logSide.value, { silent: true })
      const jobActive = currentJob.value
        && ['queued', 'running'].includes(String(currentJob.value.status || ''))
      const generating = p.value?.status === 'generating'
      if (!generating && !jobActive) {
        stopPoll()
        stopFillEvents()
        pollSyncHint.value = ''
        // 结束后补一次完整刷新；人在日志/产物页则不强切 Tab
        if (p.value) {
          const keepTab = tab.value === 'logs' || tab.value === 'artifacts'
          await load({ syncTab: !keepTab, lite: false })
        }
      } else if (generating) {
        startFillEvents()
      }
    } finally {
      pollInFlight = false
    }
  }, 1500)
}

function stopPoll() {
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = null
  pollInFlight = false
  stopFillEvents()
}

watch(tab, (v) => {
  if (v === 'logs') loadLog(logSide.value)
  if (v === 'runtime') refreshRuntime()
  if (v === 'artifacts') loadArtifactView()
})

watch(artifactsFrozen, (frozen) => {
  if (!frozen) return
  showEr.value = false
  showModules.value = false
  showTestcases.value = false
})

watch(
  () => route.params.id,
  async (id, prev) => {
    if (!id || id === prev) return
    viewEpoch += 1
    stopPoll()
    p.value = null
    loadError.value = ''
    await reload()
  },
)

onMounted(reload)
onUnmounted(() => {
  viewEpoch += 1
  stopPoll()
  stopFillEvents()
  fillLiveSnap.value = null
  detailCrumb.value = ''
})

  return {
    FILL_UNIT_KIND_ZH,
    FILL_UNIT_STATUS_ZH,
    PORTAL_HOME_FALLBACK,
    TYPE_PAREN_KEY,
    _runtimeSettled,
    _tailLines,
    ack,
    ackMainPath,
    alreadyBaked,
    apiCopyText,
    apiGroupCopyText,
    apiQuery,
    apiSmokeBusy,
    apiSmokeFactoryHint,
    apiSmokeResult,
    apiSurface,
    apis,
    applyFillSnapshot,
    archDomainDeviant,
    archOptions,
    artifactLoading,
    artifactView,
    artifactsFrozen,
    artifactsFrozenReason,
    authEntryDisplay,
    backendAddr,
    canDownload,
    canDownloadAndDeliver,
    canMarkDelivered,
    canMarkReady,
    canUndoDelivery,
    cancelCurrent,
    catalog,
    checkCols,
    checkRows,
    chromeOptions,
    collapsedApis,
    collapsedTables,
    commitColZh,
    commitRelZh,
    commitTableZh,
    confirmDelete,
    confirmHint,
    confirmMatch,
    confirmPreGenerate,
    currentJob,
    deleteBlocked,
    deleteBlockedReason,
    deleting,
    deliveryBusy,
    deliveryMark,
    deviant,
    displayConf,
    domCascaderOptions,
    downloadAndDeliver,
    downloadBlockedReason,
    downloadZip,
    downloadZipLabel,
    entryOptions,
    erDownloadBase,
    erEntity,
    erEntityOptions,
    erLabelSaving,
    erLayoutKey,
    erLoading,
    erMode,
    erSvgSource,
    failedBannerTitle,
    fetchErSvg,
    fetchModSvg,
    fillEventSource,
    fillLiveCols,
    fillLiveRows,
    fillLiveSnap,
    fillLiveSummary,
    fillLiveVisible,
    fillPlanCols,
    fillPlanHint,
    fillPlanLoading,
    fillPlanRows,
    filteredApiGroups,
    filteredLog,
    form,
    formatSize,
    frontendAddr,
    gateCols,
    gateRows,
    genState,
    genSuccessBannerHint,
    genSuccessBannerTitle,
    goArtifacts,
    isApiCollapsed,
    isTableCollapsed,
    jobActing,
    jobInFlight,
    keepDb,
    keywordHits,
    labelLooksLatin,
    layoutOptions,
    llmOptions,
    load,
    loadApis,
    loadArtifactView,
    loadError,
    loadErrorCode,
    loadLog,
    loadSchema,
    logFilter,
    logLoading,
    logReqSeq,
    logSide,
    logSides,
    logText,
    markDelivery,
    matchAltsText,
    matchBusy,
    matchMeta,
    matchPath,
    matchPillClass,
    matchPillText,
    matchSourceLabel,
    matchWarnings,
    modDownloadBase,
    modLayoutKey,
    modLoading,
    modSvgSource,
    modulesLayout,
    modulesMeta,
    modulesOk,
    narrativeDualText,
    normalizeStepStatus,
    onArchDomChange,
    onArtifactView,
    onDelete,
    onErEntity,
    onErMode,
    onModulesLayout,
    onPathChange,
    onTcFields,
    openEr,
    openFillPlan,
    openModules,
    openPreview,
    openTestcases,
    p,
    parseMysqlType,
    passwordHashOptions,
    pathEntryDeviant,
    pathSceneDeviant,
    persistenceDeviant,
    persistenceLabel,
    persistenceOptions,
    planSteps,
    pollFailStreak,
    pollInFlight,
    pollSyncHint,
    pollTimer,
    portalHomeOptions,
    preGenBusy,
    preGenReady,
    preGenStackWarnings,
    preGenTechDual,
    proposal,
    proposalDiff,
    putErLabelPatch,
    recommendedArchesText,
    refreshJob,
    refreshRuntime,
    reload,
    reloadErSvg,
    reloadModSvg,
    reloadTestcases,
    resetMatch,
    retryCurrent,
    roleSpecText,
    route,
    router,
    rt,
    rtAction,
    rtAllBusy,
    rtAnyBusy,
    rtAnyLive,
    rtBeLive,
    rtBothLive,
    rtBusyBe,
    rtBusyFe,
    rtCanRestartAll,
    rtCanStartAll,
    rtCanStopAll,
    rtFeLive,
    rtGenerating,
    rtPendingAll,
    rtStartBlockedReason,
    runApiSmoke,
    runGenerateJob,
    runtimeCanStop,
    runtimeLogView,
    runtimeStatusLabel,
    runtimeStatusPill,
    runtimeTransient,
    saveSoft,
    sceneOptions,
    schema,
    schemaErGapCount,
    securityDeviant,
    securityLabel,
    securityOn,
    securityOptions,
    showDelete,
    showEr,
    showFillPlan,
    showJobSteps,
    showModules,
    showPreGenerate,
    showSoftBakePanel,
    showSpec,
    showTestcases,
    smokeDetailFromAxios,
    smokeDetailText,
    smokePillClass,
    smokeRowClass,
    smokeStatusLabel,
    softApplying,
    softBakeHint,
    softSaving,
    softThemeWireStyle,
    softVisualWireStyle,
    specText,
    startFillEvents,
    startGenerate,
    startPoll,
    statusLabel,
    statusPill,
    stepStatusLabel,
    stepStatusMark,
    stopFillEvents,
    stopPoll,
    tab,
    tableCopyText,
    tcColumns,
    tcCount,
    tcDownloadBase,
    tcFields,
    tcLoading,
    tcMarkdown,
    tcRows,
    themeOptions,
    toggleApi,
    toggleTable,
    toggleUnlock,
    typeParenMode,
    typefaceOptions,
    undoDelivery,
    undoDeliveryLabel,
    unlocked,
    viewActive,
    viewEpoch,
    warningText,
    zipFileName,
    zipLockHint,
  }
}
