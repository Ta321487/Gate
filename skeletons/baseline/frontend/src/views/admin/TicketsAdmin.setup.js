import { computed, onMounted, reactive, ref } from 'vue'
import { APP_DELIVERED } from '../../appDelivered.js'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'
import RichTextView from '../../components/RichTextView.vue'
import CopyableId from '../../components/CopyableId.vue'
import TicketProgressDialog from '../../components/TicketProgressDialog.vue'
import {
  archiveCopy,
  followChannelLabel,
  getSchema,
  hasCap,
  menuLabel,
  nextFollowLabel,
  personLabel,
  roleLabel,
  ticketCopy,
  ticketDueLabel,
  ticketShowsFollowCols,
  ticketShowsLocationCol,
  ticketShowsPriorityCols,
  ticketShowsTypeCol,
} from '../../utils/domainSchema.js'
import { plainFromHtml } from '../../utils/richHtml.js'

/** 审批组页内构图：typelist / inboxsteps；非审批域为空 */
const approveSurface = computed(() => {
  const s = String(
    APP_DELIVERED?.approveSurfaceStyle
      || import.meta.env.VITE_APPROVE_SURFACE_STYLE
      || '',
  ).trim()
  if (['typelist', 'inboxsteps'].includes(s)) return s
  return ''
})

/** 收件箱顶栏：待我审分档计数（对标 G-1.5 ASCII） */
const approveInboxStats = computed(() => {
  if (approveSurface.value !== 'inboxsteps') return null
  let pending = 0
  let mid = 0
  let final = 0
  for (const row of list.value || []) {
    const st = String(row?.status || '')
    if (st === 'pending') pending += 1
    else if (st === 'pending_mid') mid += 1
    else if (st === 'pending_final') final += 1
  }
  return { pending, mid, final, total: pending + mid + final }
})

const ticket = ticketCopy()
const archive = archiveCopy()
const verbs = computed(() => ticket.verbs || {})
const states = computed(() => ticket.states || {})
const ticketNoun = computed(() => ticket.label || '申请')
const richRemark = computed(() => !!ticket.richRemark)
const requireRemark = computed(() => !!ticket.requireRemark)
const requireClaimProof = computed(() => !!ticket.requireClaimProof || hasCap('claim_proof'))
const remarkLabel = computed(() => ticket.remarkLabel || '说明')
const twoLevel = computed(() => !!ticket.twoLevelApprove || !!ticket.threeLevelApprove)
const threeLevel = computed(() => !!ticket.threeLevelApprove)
const allowBookHold = computed(() => !!(ticket.allowBookHold || hasCap('book_hold')))
const allowQty = computed(() => !!ticket.allowQty)
const pickLoanPeriod = computed(() => !!ticket.pickLoanPeriod)
const slaDeadline = computed(() => !!ticket.slaDeadline)
const applicantCompleteOnly = computed(() => !!ticket.applicantCompleteOnly)
const dueLabel = computed(() => ticketDueLabel(slaDeadline.value ? '处理时限' : '到期日'))
const userLabel = computed(() => roleLabel('user', '用户'))
const recordsLabel = computed(() => menuLabel('admin', 'ticket_records', ticket.recordsMenu || '记录'))
const showFollowCols = computed(() => ticketShowsFollowCols())
const channelLabel = computed(() => followChannelLabel())
const nextAtLabel = computed(() => nextFollowLabel())
const showTypeCol = computed(() => ticketShowsTypeCol(archive))
const showLocationCol = computed(() => ticketShowsLocationCol(archive))
const showPriorityCols = computed(() => ticketShowsPriorityCols())
const labels = computed(() => getSchema()?.labels || {})
const rejectReasonRequired = computed(
  () => labels.value.rejectReasonRequired || '请填写驳回原因，申请人可见',
)
const approvePhrases = computed(() => {
  const raw = ticket.approvePhrases
  if (Array.isArray(raw)) return raw.map((x) => String(x || '').trim()).filter(Boolean)
  return []
})
const approvePhraseLabel = computed(() => labels.value.approvePhraseLabel || '常用意见')
const approvePhraseHint = computed(() => labels.value.approvePhraseHint || '')
const minApproveRemarkWords = computed(() => Math.max(0, Number(ticket.minApproveRemarkWords) || 0))
const minApproveRemarkHint = computed(() => labels.value.minApproveRemarkHint || '')
const allowApproveCc = computed(() => !!ticket.allowApproveCc)
const approveCcLabel = computed(() => labels.value.approveCcLabel || '抄送知会')
const approveCcHint = computed(() => labels.value.approveCcHint || '')
const approveDueSoonHint = computed(() => labels.value.approveDueSoonHint || '')
const allowApproveTransfer = computed(() => !!ticket.allowApproveTransfer)
const approveTransferLabel = computed(() => labels.value.approveTransferLabel || '转审')
const approveTransferHint = computed(() => labels.value.approveTransferHint || '')
const allowApproveDelegate = computed(() => !!ticket.allowApproveDelegate)
const approveDelegateLabel = computed(() => labels.value.approveDelegateLabel || '请假代审')
const approveDelegateHint = computed(() => labels.value.approveDelegateHint || '')
const allowApproveRemarkAttach = computed(() => !!ticket.allowApproveRemarkAttach)
const approveRemarkAttachLabel = computed(() => labels.value.approveRemarkAttachLabel || '审核意见附件')
const approveRemarkAttachHint = computed(() => labels.value.approveRemarkAttachHint || '')
const allowApproveCcComment = computed(() => !!ticket.allowApproveCcComment)
const approveCcCommentLabel = computed(() => labels.value.approveCcCommentLabel || '知会评论')
const approveCcCommentHint = computed(() => labels.value.approveCcCommentHint || '')
const approveAutoPassHint = computed(() => labels.value.approveAutoPassHint || '')
const reassignActionLabel = computed(() =>
  allowApproveTransfer.value && !repairThickenOn.value
    ? approveTransferLabel.value
    : (allowApproveTransfer.value ? approveTransferLabel.value : '转派'),
)
const reassignDialogTitle = computed(() =>
  allowApproveTransfer.value ? approveTransferLabel.value : '转派处理人',
)
const approveRemarkPlaceholder = computed(() => {
  if (!audit.pass) return rejectReasonRequired.value
  if (minApproveRemarkWords.value > 0) return minApproveRemarkHint.value || '请填写审核意见'
  return '可填写受理说明，留空则保留申请说明'
})
function applyApprovePhrase(v) {
  const text = String(v || '').trim()
  if (!text) return
  audit.remark = text
  audit.phrasePick = ''
}
// 事件等级 → 处理时限（工程生成: ticket-level-sla-*-days 由 /api/tickets 回显）
const levelSlaDays = ref('')
const dutyNotifyOn = ref(false)
const levelSlaHint = computed(() => labels.value.levelSlaHint || '')
const notifyDutyHint = computed(() => labels.value.notifyDutyHint || '')
const levelSlaText = computed(() => {
  const parts = String(levelSlaDays.value || '').split(',').map((s) => String(s || '').trim())
  if (parts.length < 3 || !parts[0]) return ''
  return `高 ${parts[0]} 天 / 中 ${parts[1]} 天 / 低 ${parts[2]} 天`
})
const creditOn = computed(() => !!ticket.creditOnOverdue || !!ticket.creditPoints)
const creditScoreLabel = computed(() => labels.value.creditScoreLabel || '信誉分')
const creditRows = ref([])
const credit = reactive({
  visible: false,
  username: '',
  delta: -5,
  reason: '',
  loading: false,
})

/** 管理端信誉分台账：credit-on-overdue 未开时不开面。 */
async function loadCredit() {
  if (!creditOn.value) return
  const res = await http.get('/api/tickets/credit/ledger')
  creditRows.value = res.data?.rows || []
}

function openCredit() {
  Object.assign(credit, { visible: true, username: '', delta: -5, reason: '' })
}

/** 人工调整：正数加分 / 负数扣分，落 credit_ledger 留痕。 */
async function submitCredit() {
  const username = credit.username.trim()
  if (!username) {
    ElMessage.warning('请填写用户名')
    return
  }
  if (!credit.delta) {
    ElMessage.warning('调整分值不能为 0')
    return
  }
  credit.loading = true
  try {
    await http.post('/api/tickets/credit/adjust', {
      username,
      delta: credit.delta,
      reason: credit.reason.trim(),
    })
    ElMessage.success(`${creditScoreLabel.value}已调整`)
    credit.visible = false
    loadCredit()
  } finally {
    credit.loading = false
  }
}
const repairThickenOn = computed(() => !!ticket.repairThicken || !!ticket.allowUserUrge)
const allowSkillTag = computed(() => !!ticket.allowSkillTag || !!ticket.repairThicken)
const allowHelper = computed(() => !!ticket.allowHelper)
const allowQuote = computed(() => !!ticket.allowQuote)
const allowDisburseBatch = computed(() => !!ticket.allowDisburseBatch)
const disburseBatchLabel = computed(() => labels.value.disburseBatchLabel || '发放批次号')
const allowExcellentMark = computed(() => !!ticket.allowExcellentMark)
const excellentMarkLabel = computed(() => labels.value.excellentMarkLabel || '优秀周报')
const requireMeetingAck = computed(() => !!ticket.requireMeetingAck)
const ownerMeetingAckLabel = computed(
  () => labels.value.ownerMeetingAckLabel || '启事方确认面交安排',
)
const allowAssignDept = computed(() => !!ticket.allowAssignDept)
const assignDeptLabel = computed(() => labels.value.assignDeptLabel || '分拨科室')
const allowExceptionClose = computed(() => !!ticket.allowExceptionClose)
const exceptionReasonLabel = computed(() => labels.value.exceptionReasonLabel || '异常件原因')
const damageClaimLabel = computed(() => labels.value.damageClaimLabel || '破损理赔说明')
const categoryColorOn = computed(() => !!ticket.categoryColorHint || !!ticket.repairThicken)
const locationFilterOn = computed(() => !!(labels.value.dispatchFilterHint || ticket.repairThicken))
const skillFilterHint = computed(() => labels.value.skillFilterHint || '按技能标签筛选处理人')
const locationFilterHint = computed(() => labels.value.dispatchFilterHint || '可按地点/楼栋关键词筛选处理人')
const interviewRoomHint = computed(() => labels.value.interviewRoomHint || '')
const dispatchHint = computed(
  () => labels.value.dispatchFilterHint || labels.value.rosterConflictHint || '',
)
const quoteLabel = computed(() => labels.value.quoteLabel || '维修报价（元）')
const materialFeeLabel = computed(() => labels.value.materialFeeLabel || '材料费（元）')
const skillOptions = computed(() => {
  const list = ticket.skillTags || ticket.faultReasons
  return Array.isArray(list) && list.length
    ? list.slice(0, 12)
    : ['水电', '门锁', '网络', '照明', '综合']
})
function typeColor(key) {
  const s = String(key || '')
  let h = 0
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0
  return `hsl(${h % 360} 55% 48%)`
}
const superAdmin = localStorage.getItem('superAdmin') === 'true'
/** 终审/单级受理时可选派给维修员等子管 */
const showDispatch = computed(() => applicantCompleteOnly.value || slaDeadline.value)
const allowBatchHire = computed(() => !!ticket.allowBatchHire)
const allowVisitWalkIn = computed(() => !!ticket.allowVisitWalkIn)
const visitWalkInLabel = computed(() => labels.value.visitWalkInLabel || '现场补录')
const visitWalkInForLabel = computed(() => labels.value.visitWalkInForLabel || '被访人账号')
const visitWalkInHint = computed(() => labels.value.visitWalkInHint || '')
const allowCheckinProxy = computed(() => !!ticket.allowCheckinProxy)
const checkinProxyLabel = computed(() => labels.value.checkinProxyLabel || '楼栋长代登记')
const checkinProxyForLabel = computed(() => labels.value.checkinProxyForLabel || '学生账号')
const checkinProxyHint = computed(() => labels.value.checkinProxyHint || '')
const allowEvalUrge = computed(() => !!ticket.allowEvalUrge)
const evalUrgeLabel = computed(() => labels.value.evalUrgeLabel || '催评')
const evalUrgeHint = computed(() => labels.value.evalUrgeHint || '')
const allowCheckinSpot = computed(() => !!ticket.allowCheckinSpot)
const checkinSpotLabel = computed(() => labels.value.checkinSpotLabel || '抽查任务')
const checkinSpotSampleLabel = computed(() => labels.value.checkinSpotSampleLabel || '抽查人数')
const checkinSpotOnLabel = computed(() => labels.value.checkinSpotOnLabel || '抽查日期')
const checkinSpotHint = computed(() => labels.value.checkinSpotHint || '')
const allowApproveDurationStats = computed(() => !!ticket.allowApproveDurationStats)
const approveDurationStatsLabel = computed(() => labels.value.approveDurationStatsLabel || '人均办理耗时')
const approveDurationStatsHint = computed(() => labels.value.approveDurationStatsHint || '')
const allowCheckinDailyReport = computed(() => !!ticket.allowCheckinDailyReport)
const checkinDailyLabel = computed(() => labels.value.checkinDailyLabel || '楼长日报')
const checkinDailyOnLabel = computed(() => labels.value.checkinDailyOnLabel || '汇总日期')
const checkinDailyHint = computed(() => labels.value.checkinDailyHint || '')
const allowEvalCollegeExport = computed(() => !!ticket.allowEvalCollegeExport)
const evalCollegeExportLabel = computed(() => labels.value.evalCollegeExportLabel || '院系汇总导出')
const evalCollegeLabel = computed(() => labels.value.evalCollegeLabel || '开课学院')
const evalCollegeExportHint = computed(() => labels.value.evalCollegeExportHint || '')
const archiveItems = ref([])
const userOptions = ref([])
const walkIn = reactive({ visible: false, loading: false, itemId: null, forUsername: '', visitOn: '', remark: '' })
const checkinProxy = reactive({ visible: false, loading: false, itemId: null, forUsername: '', remark: '' })
const evalUrge = reactive({ visible: false, loading: false, itemId: null })
const spotCheck = reactive({ visible: false, loading: false, itemId: null, onDate: '', sampleN: 3, list: [] })
const durationRows = ref([])
const checkinDaily = reactive({ visible: false, loading: false, onDate: '', total: 0, pending: 0, approved: 0, absent: 0, list: [] })
const evalCollege = reactive({ visible: false, list: [] })
const batchHireLabel = computed(() => labels.value.batchHireLabel || '批量录用')
const batchRejectLabel = computed(() => labels.value.batchRejectLabel || '批量淘汰')
const selectedIds = ref([])

function onSelectionChange(rows) {
  selectedIds.value = (rows || []).map((r) => r.id).filter((id) => id != null)
}

async function batchHire(pass) {
  if (!selectedIds.value.length) {
    ElMessage.warning('请先勾选单据')
    return
  }
  const action = pass ? batchHireLabel.value : batchRejectLabel.value
  let remark = pass ? '' : '批量淘汰'
  if (!pass) {
    try {
      const { value } = await ElMessageBox.prompt('请填写淘汰原因', action, {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        inputPattern: /\S+/,
        inputErrorMessage: '原因不能为空',
      })
      remark = String(value || '').trim()
    } catch {
      return
    }
  }
  const res = await http.post('/api/tickets/batch-hire', {
    ids: selectedIds.value,
    pass,
    remark,
  })
  const data = res.data || res
  const ok = data.okCount || 0
  const fail = data.failCount || 0
  if (fail > 0) {
    ElMessage.warning(`${action}完成：成功 ${ok} 条，失败 ${fail} 条`)
  } else {
    ElMessage.success(`${action}成功 ${ok} 条`)
  }
  selectedIds.value = []
  load()
}

function archiveFieldLabel(key, fallback) {
  const f = (archive.fields || []).find((x) => x.key === key)
  return f?.label || fallback
}

const typeColLabel = computed(() => {
  if ((archive.fields || []).some((f) => f.key === 'itemKind')) {
    return archiveFieldLabel('itemKind', '类型')
  }
  if ((archive.fields || []).some((f) => f.key === 'category')) {
    return archiveFieldLabel('category', '类型')
  }
  return '类型'
})

const locationColLabel = computed(() => {
  if ((archive.fields || []).some((f) => f.key === 'isbn')) {
    return archiveFieldLabel('isbn', '地点')
  }
  return '地点'
})

function remarkPlain(v) {
  if (!v) return ''
  return richRemark.value ? plainFromHtml(String(v)) : String(v)
}

const todoHint = computed(() => {
  const base = `待受理 · 历史见「${recordsLabel.value}」`
  return twoLevel.value ? `${base} · 二级审批（终审需总管）` : base
})

const list = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)

const audit = reactive({
  visible: false,
  loading: false,
  pass: true,
  remark: '',
  phrasePick: '',
  ccUsernames: [],
  approveAttachUrl: '',
  assigneeUsername: '',
  helperUsername: '',
  skillFilter: '',
  locationFilter: '',
  quoteYuan: null,
  materialFeeYuan: null,
  disburseBatch: '',
  excellentMark: false,
  ownerMeetingAck: false,
  assignDept: '',
  exceptionReason: '',
  damageClaimNote: '',
  row: null,
})
const delegate = reactive({
  visible: false,
  loading: false,
  to: '',
  untilAt: '',
  current: null,
})
const ccComment = reactive({
  visible: false,
  loading: false,
  row: null,
  text: '',
})
const reassign = reactive({
  visible: false,
  loading: false,
  row: null,
  to: '',
  remark: '',
  skillFilter: '',
  locationFilter: '',
})

const progressVisible = ref(false)
const progressId = ref(null)
const proofDlg = reactive({ visible: false, list: [], claimId: 0 })
const dispatchTargets = ref([])

const filteredDispatchTargets = computed(() =>
  filterTargets(dispatchTargets.value, audit.skillFilter, audit.locationFilter || audit.row?.location),
)
const filteredReassignTargets = computed(() =>
  filterTargets(dispatchTargets.value, reassign.skillFilter, reassign.locationFilter || reassign.row?.location),
)

function filterTargets(list, skill, locationKey) {
  let out = list || []
  const s = String(skill || '').trim()
  if (s) {
    out = out.filter((t) => {
      const blob = `${t.username || ''} ${t.nickname || ''} ${t.staffPost || ''} ${t.staffKind || ''}`
      return blob.includes(s)
    })
  }
  const loc = String(locationKey || '').trim()
  if (loc) {
    // 取地点前缀（楼栋/小区）做关键词；与处理人昵称/岗位匹配
    const token = loc.split(/[\s\-_/|，,]/)[0] || loc
    if (token.length >= 2) {
      const keyed = out.filter((t) => {
        const blob = `${t.username || ''} ${t.nickname || ''} ${t.staffPost || ''} ${t.staffKind || ''}`
        return blob.includes(token)
      })
      if (keyed.length) out = keyed
    }
  }
  return out
}

function statusText(s) {
  return (
    states.value[s]
    || ({
      pending: '待交凭证',
      verifying: '待核验',
      pending_mid: '待复审',
      pending_final: '待终审',
    }[s])
    || s
  )
}

function passLabel(row) {
  if (allowBookHold.value && row?.status === 'hold_ready') return '确认出借'
  if (row?.status === 'verifying') return verbs.value.approve || '受理'
  if (!twoLevel.value || !row) return verbs.value.approve || '受理'
  if (row.status === 'pending_final') return '终审通过'
  if (threeLevel.value && row.status === 'pending_mid') return '复审通过'
  if (threeLevel.value && row.status === 'pending') return '初审通过'
  // 二级首关：跟 verbs 文案（报修「受理」、借阅「通过」）；勿写死「初审」
  return verbs.value.approve || '受理'
}

function canPass(row) {
  if (requireClaimProof.value && row?.status === 'pending') return false
  if (!twoLevel.value) return true
  if (row?.status === 'pending_final') return superAdmin
  return true
}

/** 仅进入「处理中」的那一关展示派单 */
function isFinalPass(row) {
  if (!row) return false
  if (allowBookHold.value && row.status === 'hold_ready') return true
  if (!twoLevel.value) return true
  return row.status === 'pending_final'
}

function dispatchLabel(t) {
  const name = t.nickname || t.username
  const post = t.staffPost ? ` · ${t.staffPost}` : ''
  const duty = t.onDutyToday ? ' · 当日当班' : ''
  return `${name}${post}${duty}`
}

async function loadDispatchTargets() {
  try {
    const res = await http.get('/api/tickets/dispatch-targets')
    dispatchTargets.value = Array.isArray(res.data) ? res.data : []
  } catch {
    dispatchTargets.value = []
  }
}

async function load() {
  const res = await http.get('/api/tickets', {
    params: { page: page.value, size: size.value, status: 'todo' },
  })
  list.value = res.data.list
  total.value = res.data.total
  levelSlaDays.value = res.data.levelSlaDays || ''
  dutyNotifyOn.value = !!res.data.dutyNotify
}

async function returnRevise(row) {
  try {
    const { value } = await ElMessageBox.prompt('请填写退回修改说明', '退回修改', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      inputPlaceholder: '如：附件缺失，请补充后重交',
    })
    await http.post(`/api/tickets/${row.id}/return-revise`, { note: value || '' })
    ElMessage.success('已退回修改')
    await load()
  } catch (e) {
    if (e === 'cancel' || e === 'close') return
    ElMessage.error(e?.response?.data?.message || e?.message || '退回修改失败')
  }
}

function openAudit(row, pass) {
  if (pass && requireClaimProof.value && row.status === 'pending') {
    ElMessage.warning('请先等待用户提交认领凭证')
    return
  }
  if (pass && !canPass(row)) {
    ElMessage.warning('终审通过需总管操作')
    return
  }
  audit.row = row
  audit.pass = pass
  audit.remark = ''
  audit.phrasePick = ''
  audit.ccUsernames = []
  audit.approveAttachUrl = ''
  audit.assigneeUsername = ''
  audit.helperUsername = ''
  audit.skillFilter = ''
  audit.locationFilter = row?.location || ''
  audit.quoteYuan = row?.quoteYuan != null ? Number(row.quoteYuan) : null
  audit.materialFeeYuan = row?.materialFeeYuan != null ? Number(row.materialFeeYuan) : null
  audit.disburseBatch = row?.disburseBatch || ''
  audit.excellentMark = !!row?.excellentMark
  audit.assignDept = row?.assignDept || ''
  audit.exceptionReason = row?.exceptionReason || ''
  audit.damageClaimNote = row?.damageClaimNote || ''
  audit.visible = true
  if ((pass && showDispatch.value && isFinalPass(row)) || allowApproveCc.value || allowApproveDelegate.value) {
    loadDispatchTargets()
  }
}

function canReassign(row) {
  if (!row) return false
  if (!(repairThickenOn.value || allowApproveTransfer.value)) return false
  return ['pending', 'pending_mid', 'pending_final', 'approved', 'overdue', 'paused'].includes(row.status)
}

function canCcComment(row) {
  if (!allowApproveCcComment.value || !row) return false
  const me = (localStorage.getItem('username') || '').trim().toLowerCase()
  if (!me) return false
  const raw = String(row.ccUsernames || '')
  return raw.split(/[,;\s]+/).some((p) => p.trim().toLowerCase() === me)
}

async function loadPickLists() {
  try {
    const [a, u] = await Promise.all([
      http.get('/api/archive', { params: { page: 1, size: 200 } }),
      http.get('/api/tickets/apply-targets'),
    ])
    archiveItems.value = a.data?.list || []
    userOptions.value = Array.isArray(u.data) ? u.data : (u.data?.list || [])
  } catch {
    archiveItems.value = []
    userOptions.value = []
  }
}

async function openWalkIn() {
  walkIn.itemId = null
  walkIn.forUsername = ''
  walkIn.visitOn = ''
  walkIn.remark = ''
  walkIn.visible = true
  await loadPickLists()
}

async function submitWalkIn() {
  if (!walkIn.itemId) {
    ElMessage.warning('请选择来访对象')
    return
  }
  if (!walkIn.forUsername) {
    ElMessage.warning(`请选择${visitWalkInForLabel.value}`)
    return
  }
  if (!walkIn.visitOn) {
    ElMessage.warning('请选择来访日期')
    return
  }
  walkIn.loading = true
  try {
    await http.post('/api/tickets/walk-in', {
      itemId: walkIn.itemId,
      forUsername: walkIn.forUsername,
      visitOn: walkIn.visitOn,
      remark: walkIn.remark,
      walkIn: true,
    })
    ElMessage.success('已补录')
    walkIn.visible = false
    load()
  } finally {
    walkIn.loading = false
  }
}

async function openCheckinProxy() {
  checkinProxy.itemId = null
  checkinProxy.forUsername = ''
  checkinProxy.remark = ''
  checkinProxy.visible = true
  await loadPickLists()
}

async function submitCheckinProxy() {
  if (!checkinProxy.itemId) {
    ElMessage.warning('请选择查寝对象')
    return
  }
  if (!checkinProxy.forUsername) {
    ElMessage.warning(`请选择${checkinProxyForLabel.value}`)
    return
  }
  checkinProxy.loading = true
  try {
    await http.post('/api/tickets/checkin-proxy', {
      itemId: checkinProxy.itemId,
      forUsername: checkinProxy.forUsername,
      remark: checkinProxy.remark,
    })
    ElMessage.success('已代登记')
    checkinProxy.visible = false
    load()
  } finally {
    checkinProxy.loading = false
  }
}

async function openEvalUrge() {
  evalUrge.itemId = null
  evalUrge.visible = true
  await loadPickLists()
}

async function submitEvalUrge() {
  if (!evalUrge.itemId) {
    ElMessage.warning('请选择课程')
    return
  }
  evalUrge.loading = true
  try {
    const res = await http.post('/api/tickets/eval-urge', { itemId: evalUrge.itemId })
    const n = res.data?.sent
    ElMessage.success(n != null ? `已向 ${n} 位同学发送催评` : '已发送催评')
    evalUrge.visible = false
  } finally {
    evalUrge.loading = false
  }
}

function formatSpotMembers(raw) {
  if (!Array.isArray(raw)) return ''
  return raw.map((x) => x.username || '').filter(Boolean).join('，')
}

async function loadDurationStats() {
  if (!allowApproveDurationStats.value) {
    durationRows.value = []
    return
  }
  try {
    const res = await http.get('/api/tickets/approve-duration-stats')
    durationRows.value = res.data?.data || res.data || []
  } catch {
    durationRows.value = []
  }
}

function downloadCsv(filename, headers, rows) {
  const lines = [headers.join(','), ...rows.map((r) => r.map((c) => `"${String(c ?? '').replace(/"/g, '""')}"`).join(','))]
  const blob = new Blob(['\ufeff' + lines.join('\n')], { type: 'text/csv;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = filename
  a.click()
  URL.revokeObjectURL(a.href)
}

async function openCheckinDaily() {
  checkinDaily.onDate = ''
  checkinDaily.visible = true
  await loadCheckinDaily()
}

async function loadCheckinDaily() {
  checkinDaily.loading = true
  try {
    const res = await http.get('/api/tickets/checkin-daily', {
      params: { onDate: checkinDaily.onDate || undefined },
    })
    const data = res.data?.data || res.data || {}
    checkinDaily.onDate = data.onDate || checkinDaily.onDate
    checkinDaily.total = Number(data.total || 0)
    checkinDaily.pending = Number(data.pending || 0)
    checkinDaily.approved = Number(data.approved || 0)
    checkinDaily.absent = Number(data.absent || 0)
    checkinDaily.list = data.list || []
  } finally {
    checkinDaily.loading = false
  }
}

function exportCheckinDaily() {
  downloadCsv(
    `checkin-daily-${checkinDaily.onDate || 'export'}.csv`,
    ['账号', '说明', '状态'],
    (checkinDaily.list || []).map((r) => [r.username, r.title, r.status]),
  )
}

async function openEvalCollege() {
  evalCollege.visible = true
  try {
    const res = await http.get('/api/tickets/eval-college-stats')
    evalCollege.list = res.data?.data || res.data || []
  } catch {
    evalCollege.list = []
  }
}

function exportEvalCollege() {
  downloadCsv(
    'eval-college.csv',
    [evalCollegeLabel.value, '已评份数'],
    (evalCollege.list || []).map((r) => [r.college, r.count]),
  )
}

async function openSpotCheck() {
  spotCheck.itemId = null
  spotCheck.onDate = ''
  spotCheck.sampleN = 3
  spotCheck.visible = true
  await loadPickLists()
  await loadSpotList()
}

async function loadSpotList() {
  try {
    const res = await http.get('/api/tickets/spot-check', {
      params: { itemId: spotCheck.itemId || undefined },
    })
    spotCheck.list = res.data?.data || res.data || []
  } catch {
    spotCheck.list = []
  }
}

async function submitSpotCheck() {
  if (!spotCheck.itemId) {
    ElMessage.warning('请选择查寝对象')
    return
  }
  if (!spotCheck.onDate) {
    ElMessage.warning(`请选择${checkinSpotOnLabel.value}`)
    return
  }
  spotCheck.loading = true
  try {
    await http.post('/api/tickets/spot-check', {
      itemId: spotCheck.itemId,
      onDate: spotCheck.onDate,
      sampleN: spotCheck.sampleN,
    })
    ElMessage.success('已生成抽查名单')
    await loadSpotList()
  } finally {
    spotCheck.loading = false
  }
}

async function openDelegate() {
  delegate.to = ''
  delegate.untilAt = ''
  delegate.current = null
  delegate.visible = true
  await loadDispatchTargets()
  try {
    const res = await http.get('/api/tickets/approve-delegate')
    delegate.current = res.data || null
    if (delegate.current?.delegateUsername) {
      delegate.to = delegate.current.delegateUsername
      delegate.untilAt = delegate.current.untilAt || ''
    }
  } catch {
    delegate.current = null
  }
}

async function submitDelegate() {
  if (!delegate.to) {
    ElMessage.warning('请选择代审人')
    return
  }
  if (!delegate.untilAt) {
    ElMessage.warning('请选择截止日期')
    return
  }
  delegate.loading = true
  try {
    await http.post('/api/tickets/approve-delegate', {
      delegateUsername: delegate.to,
      untilAt: delegate.untilAt,
    })
    ElMessage.success('已保存代审')
    delegate.visible = false
  } finally {
    delegate.loading = false
  }
}

async function clearDelegate() {
  delegate.loading = true
  try {
    await http.post('/api/tickets/approve-delegate/clear')
    ElMessage.success('已取消代审')
    delegate.visible = false
  } finally {
    delegate.loading = false
  }
}

function openCcComment(row) {
  ccComment.row = row
  ccComment.text = ''
  ccComment.visible = true
}

async function submitCcComment() {
  if (!ccComment.row) return
  const text = (ccComment.text || '').trim()
  if (!text) {
    ElMessage.warning('请填写评论')
    return
  }
  ccComment.loading = true
  try {
    await http.post(`/api/tickets/${ccComment.row.id}/cc-comment`, { comment: text })
    ElMessage.success('已提交')
    ccComment.visible = false
    load()
  } finally {
    ccComment.loading = false
  }
}

async function uploadApproveAttach(opt) {
  const fd = new FormData()
  fd.append('file', opt.file)
  const res = await http.post('/api/upload', fd)
  audit.approveAttachUrl = res.data?.url || res.data?.data?.url || ''
  if (!audit.approveAttachUrl) ElMessage.warning('上传失败')
}

async function openReassign(row) {
  reassign.row = row
  reassign.to = ''
  reassign.remark = ''
  reassign.skillFilter = row.skillTag || ''
  reassign.locationFilter = row.location || ''
  reassign.visible = true
  await loadDispatchTargets()
}

async function submitReassign() {
  if (!reassign.row) return
  if (!reassign.to) {
    ElMessage.warning('请选择转派对象')
    return
  }
  reassign.loading = true
  try {
    const body = {
      assigneeUsername: reassign.to,
      remark: reassign.remark,
    }
    if (allowSkillTag.value && reassign.skillFilter) {
      body.skillTag = reassign.skillFilter
    }
    await http.post(`/api/tickets/${reassign.row.id}/reassign`, body)
    ElMessage.success('已转派')
    reassign.visible = false
    load()
  } finally {
    reassign.loading = false
  }
}

async function openProofVerify(row) {
  proofDlg.claimId = row.id
  proofDlg.visible = true
  const res = await http.get('/api/lost/proof', { params: { claimId: row.id } })
  proofDlg.list = res.data || []
}

async function verifyProof(row, pass) {
  await http.post(`/api/lost/proof/${row.id}/verify`, { pass })
  ElMessage.success(pass ? '凭证已通过，可继续受理' : '凭证已驳回，用户可重交')
  const res = await http.get('/api/lost/proof', { params: { claimId: proofDlg.claimId } })
  proofDlg.list = res.data || []
  load()
}

function resetAudit() {
  audit.row = null
  audit.remark = ''
  audit.phrasePick = ''
  audit.ccUsernames = []
  audit.approveAttachUrl = ''
  audit.assigneeUsername = ''
  audit.helperUsername = ''
  audit.skillFilter = ''
  audit.locationFilter = ''
  audit.quoteYuan = null
  audit.materialFeeYuan = null
  audit.disburseBatch = ''
  audit.excellentMark = false
  audit.ownerMeetingAck = false
  audit.assignDept = ''
  audit.exceptionReason = ''
  audit.damageClaimNote = ''
  audit.loading = false
}

async function submitAudit() {
  if (!audit.row) return
  const remark = audit.remark.trim()
  if (!audit.pass && !remark) {
    ElMessage.warning(rejectReasonRequired.value)
    return
  }
  if (minApproveRemarkWords.value > 0) {
    const words = remark.replace(/\s+/g, '').length
    if (words < minApproveRemarkWords.value) {
      ElMessage.warning(minApproveRemarkHint.value || `审核意见不少于 ${minApproveRemarkWords.value} 字`)
      return
    }
  }
  if (audit.pass && requireMeetingAck.value && !audit.ownerMeetingAck) {
    ElMessage.warning(ownerMeetingAckLabel.value || '请勾选启事方确认面交安排')
    return
  }
  audit.loading = true
  try {
    const body = {
      pass: audit.pass,
      remark,
    }
    if (!audit.pass && getSchema()?.uxCrosscut?.confirm) body.confirm = true
    if (allowApproveCc.value && Array.isArray(audit.ccUsernames) && audit.ccUsernames.length) {
      body.ccUsernames = audit.ccUsernames
    }
    if (allowApproveRemarkAttach.value && audit.approveAttachUrl) {
      body.approveAttachUrl = audit.approveAttachUrl
    }
    if (audit.pass && showDispatch.value && isFinalPass(audit.row) && audit.assigneeUsername) {
      body.assigneeUsername = audit.assigneeUsername
    }
    if (audit.pass && allowHelper.value && audit.helperUsername) {
      body.helperUsername = audit.helperUsername
    }
    if (audit.pass && allowSkillTag.value && audit.skillFilter) {
      body.skillTag = audit.skillFilter
    }
    if (audit.pass && allowQuote.value) {
      if (audit.quoteYuan != null) body.quoteYuan = audit.quoteYuan
      if (audit.materialFeeYuan != null) body.materialFeeYuan = audit.materialFeeYuan
    }
    if (audit.pass && allowDisburseBatch.value && (audit.disburseBatch || '').trim()) {
      body.disburseBatch = audit.disburseBatch.trim()
    }
    if (audit.pass && allowExcellentMark.value) {
      body.excellentMark = !!audit.excellentMark
    }
    if (audit.pass && requireMeetingAck.value) {
      body.ownerMeetingAck = !!audit.ownerMeetingAck
    }
    if (audit.pass && allowAssignDept.value && (audit.assignDept || '').trim()) {
      body.assignDept = audit.assignDept.trim()
    }
    if (audit.pass && allowExceptionClose.value) {
      if ((audit.exceptionReason || '').trim()) body.exceptionReason = audit.exceptionReason.trim()
      if ((audit.damageClaimNote || '').trim()) body.damageClaimNote = audit.damageClaimNote.trim()
    }
    const res = await http.post(`/api/tickets/${audit.row.id}/approve`, body)
    const n = Number(res?.data?.autoRejectedCount) || 0
    ElMessage.success(
      audit.pass && n > 0
        ? `已处理；另有 ${n} 条同对象待审已自动驳回`
        : '已处理',
    )
    audit.visible = false
    load()
  } finally {
    audit.loading = false
  }
}

function openProgress(row) {
  progressId.value = row.id
  progressVisible.value = true
}

onMounted(() => {
  load()
  loadCredit()
  loadDurationStats()
})
