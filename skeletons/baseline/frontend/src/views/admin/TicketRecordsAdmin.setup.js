import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'
import TicketProgressDialog from '../../components/TicketProgressDialog.vue'
import RepairFinishDialog from '../../components/RepairFinishDialog.vue'
import SchemaLabelHints from '../../components/SchemaLabelHints.vue'
import { RECORDS_HINT_KEYS } from '../../utils/labelHintMount.js'
import {
  archiveCopy,
  followChannelLabel,
  getSchema,
  hasCap,
  hasTrait,
  nextFollowLabel,
  personLabel,
  roleLabel,
  ticketCopy,
  ticketDueLabel,
  ticketFineLabel,
  ticketFinePaidLabel,
  ticketShowsFollowCols,
  ticketShowsLocationCol,
  ticketShowsPriorityCols,
  ticketShowsScheduleCols,
  ticketShowsTypeCol,
} from '../../utils/domainSchema.js'
import { plainFromHtml } from '../../utils/richHtml.js'
import { downloadCsv } from '../../utils/csvDownload.js'
import { printTicketDocument } from '../../utils/ticketFormPrint.js'

const props = defineProps({
  defaultToday: { type: Boolean, default: false },
})

const route = useRoute()
const ticket = ticketCopy()
const archive = archiveCopy()
const labels = computed(() => getSchema()?.labels || {})
const verbs = computed(() => ticket.verbs || {})
const states = computed(() => ticket.states || {})
function statusLabel(row) {
  if (row && row.checkedInAt) return '已签到'
  return states.value[row?.status] || row?.status || ''
}
const richRemark = computed(() => !!ticket.richRemark)
const allowRating = computed(() => !!ticket.allowRating)
const ratingFilterRatedLabel = computed(
  () => labels.value.ratingFilterRatedLabel || '仅已评分',
)
const ratingAdminLead = computed(() => labels.value.ratingAdminLead || '')
const todayBoardOn = computed(() => !!ticket.todayBoard)
const todayBoardHint = computed(() => labels.value.todayBoardHint || '')
const printTicketOn = computed(
  () =>
    !!ticket.printTicket
    || !!ticket.allowCertFormPrint
    || !!ticket.allowSealFormPrint
    || !!ticket.allowProjMidFormPrint
    || !!ticket.allowEthicOpinionPrint
    || !!(labels.value.gradePrintHint || labels.value.bedPrintHint
      || labels.value.closedStackPrintHint || labels.value.equipQrPrintHint),
)
const printTicketLabel = computed(() => labels.value.printTicketLabel || '打印工单')
const exportAttachUrls = computed(() => !!ticket.exportAttachUrls)
const recordsHintKeys = RECORDS_HINT_KEYS
const monthExportHint = computed(() => labels.value.monthExportHint || '')
const checkExportHint = computed(() => labels.value.checkExportHint || '')
const stuNoMaskHint = computed(() => labels.value.stuNoMaskExportHint || '')
const stuNoMaskOn = computed(() => !!stuNoMaskHint.value)
const maskStuNo = ref(false)
const categoryColorOn = computed(() => !!ticket.categoryColorHint || !!ticket.repairThicken)
const repairFinishNeeded = computed(() => !!(
  ticket.repairThicken
  || ticket.requireFaultReason
  || ticket.requireCloseSummary
  || ticket.requireCloseAttach
  || ticket.allowPartsNote
  || ticket.allowSerialNo
  || ticket.allowRemoteUrl
  || ticket.allowHelper
  || ticket.allowQuote
  || ticket.allowKnowledgeDeposit
  || ticket.allowTicketMerge
  || ticket.allowFleetMileage
          || ticket.allowCompHours
          || ticket.allowReturnFuel
  || ticket.allowFleetViolation
  || ticket.allowProcureReturn
  || ticket.allowCertPickup
  || ticket.allowSealCopies
  || ticket.allowAwardCertNo
  || ticket.allowVendorQuotes
))
const hasRatingDims = computed(
  () => Array.isArray(ticket.ratingDims) && ticket.ratingDims.length > 0,
)
const ratingDimLabels = computed(() => {
  const map = {}
  for (const d of ticket.ratingDims || []) {
    if (d?.key) map[d.key] = d.label || d.key
  }
  return map
})
function formatDims(json) {
  if (!json) return '—'
  try {
    const obj = typeof json === 'string' ? JSON.parse(json) : json
    if (!obj || typeof obj !== 'object') return '—'
    return Object.entries(obj)
      .map(([k, v]) => `${ratingDimLabels.value[k] || k}:${v}`)
      .join(' · ')
  } catch {
    return '—'
  }
}
const allowCheckin = computed(() => !!ticket.allowCheckin)
const allowAdminCheckin = computed(() => !!ticket.allowAdminCheckin)
const allowLateMinutes = computed(() => !!ticket.allowLateMinutes)
const allowWishOrder = computed(() => !!ticket.allowWishOrder)
const allowVolunteerRole = computed(() => !!ticket.allowVolunteerRole)
const allowCompanions = computed(() => !!ticket.allowCompanions)
const allowCertPickup = computed(() => !!ticket.allowCertPickup)
const allowCertUrgent = computed(() => !!ticket.allowCertUrgent)
const allowSealCopies = computed(() => !!ticket.allowSealCopies)
const allowSealLedgerExport = computed(() => !!ticket.allowSealLedgerExport)
const sealLedgerExportHint = computed(() => labels.value.sealLedgerExportHint || '')
const sealLedgerExportLabel = computed(() => labels.value.sealLedgerExportLabel || '导出用印台账')
const sealCopyNosLabel = computed(() => labels.value.sealCopyNosLabel || '用印份号')
const sealWitnessAckLabel = computed(() => labels.value.sealWitnessAckLabel || '监印人已确认')
const allowExpenseInvoice = computed(() => !!ticket.allowExpenseInvoice)
const allowVisitorCount = computed(() => !!ticket.allowVisitorCount)
const allowAwardCertNo = computed(() => !!ticket.allowAwardCertNo)
const allowVendorQuotes = computed(
  () => !!ticket.allowVendorQuotes || Number(ticket.minVendorQuotes || 0) > 0,
)
const allowFleetMileage = computed(() => !!ticket.allowFleetMileage)
const allowFleetCrew = computed(() => !!ticket.allowFleetCrew)
const allowCompHours = computed(() => !!ticket.allowCompHours)
const allowReturnFuel = computed(() => !!ticket.allowReturnFuel)
const allowLaborPlace = computed(() => !!ticket.allowLaborPlace)
const allowEffectiveOn = computed(() => !!ticket.allowEffectiveOn)
const allowCertIssueNo = computed(() => !!ticket.allowCertIssueNo)
const allowDocRev = computed(() => !!ticket.allowDocRev)
const allowFitoutQuiet = computed(() => !!ticket.allowFitoutQuiet)
const allowIssueCopies = computed(() => !!ticket.allowIssueCopies)
const allowSignParties = computed(() => !!ticket.allowSignParties)
const allowTrainHours = computed(() => !!ticket.allowTrainHours)
const allowMemberChange = computed(() => !!ticket.allowMemberChange)
const allowProcureBudget = computed(() => !!ticket.allowProcureBudget)
const allowCheckinException = computed(() => !!ticket.allowCheckinException)
const allowVisitPurpose = computed(() => !!ticket.allowVisitPurpose)
const allowFitoutRectify = computed(() => !!ticket.allowFitoutRectify)
const allowFleetViolation = computed(() => !!ticket.allowFleetViolation)
const allowProjNodeRemind = computed(() => !!ticket.allowProjNodeRemind)
const allowClubCopyLast = computed(() => !!ticket.allowClubCopyLast)
const allowProcureReturn = computed(() => !!ticket.allowProcureReturn)
const allowMoralObjection = computed(() => !!ticket.allowMoralObjection)
const allowProjFundUse = computed(() => !!ticket.allowProjFundUse)
const allowEvalDimWeight = computed(() => !!ticket.allowEvalDimWeight)
const allowVisitSlotRemain = computed(() => !!ticket.allowVisitSlotRemain)
const allowPlagiarismUrl = computed(() => !!ticket.allowPlagiarismUrl)
const allowPartyStage = computed(() => !!ticket.allowPartyStage)
const allowEvalObserve = computed(() => !!ticket.allowEvalObserve)
const allowScheduleImpact = computed(() => !!ticket.allowScheduleImpact)
const allowContractAmount = computed(() => !!ticket.allowContractAmount)
const allowExpenseLines = computed(() => !!ticket.allowExpenseLines)
const allowTripLegs = computed(() => !!ticket.allowTripLegs)
const allowProjChangeLog = computed(() => !!ticket.allowProjChangeLog)
const allowCertVerify = computed(() => !!ticket.allowCertVerify)
const allowVisitWalkIn = computed(() => !!ticket.allowVisitWalkIn)
const allowCheckinProxy = computed(() => !!ticket.allowCheckinProxy)
const allowClubRoster = computed(() => !!ticket.allowClubRoster)
const allowCarpassParkingMutex = computed(() => !!ticket.allowCarpassParkingMutex)
const allowContractRenew = computed(() => !!ticket.allowContractRenew)
const allowCertPickupRedeem = computed(() => !!ticket.allowCertPickupRedeem)
const expenseLinesLabel = computed(() => labels.value.expenseLinesLabel || '报销明细')
const tripLegsLabel = computed(() => labels.value.tripLegsLabel || '出差行程')
const changeLogNoteLabel = computed(() => labels.value.changeLogNoteLabel || '变更摘要')
const certVerifyCodeLabel = computed(() => labels.value.certVerifyCodeLabel || '真伪查询码')
const visitWalkInLabel = computed(() => labels.value.visitWalkInLabel || '现场补录')
const checkinProxyByLabel = computed(() => labels.value.checkinProxyByLabel || '代登人')
const clubRosterLabel = computed(() => labels.value.clubRosterLabel || '成员名册')
const parkingOnLabel = computed(() => labels.value.parkingOnLabel || '占用车位日期')
const renewOnLabel = computed(() => labels.value.renewOnLabel || '续签日期')
const renewNoteLabel = computed(() => labels.value.renewNoteLabel || '续签说明')
const pickupRedeemCodeLabel = computed(() => labels.value.pickupRedeemCodeLabel || '领取核销码')
const pickupRedeemedLabel = computed(() => labels.value.pickupRedeemedLabel || '已核销')
const pickupRedeemHint = computed(() => labels.value.pickupRedeemHint || '')
function formatClubMembers(raw) {
  try {
    const arr = typeof raw === 'string' ? JSON.parse(raw) : raw
    if (!Array.isArray(arr)) return raw || '—'
    return arr.map((x) => `${x.name || ''}${x.studentNo ? `（${x.studentNo}）` : ''}`).join('，') || '—'
  } catch {
    return raw || '—'
  }
}
function formatExpenseLines(raw) {
  try {
    const arr = typeof raw === 'string' ? JSON.parse(raw) : raw
    if (!Array.isArray(arr)) return raw || '—'
    return arr.map((x) => `${x.category || ''} ${x.amount ?? ''}${x.note ? `（${x.note}）` : ''}`).join('；') || '—'
  } catch {
    return raw || '—'
  }
}
function formatTripLegs(raw) {
  try {
    const arr = typeof raw === 'string' ? JSON.parse(raw) : raw
    if (!Array.isArray(arr)) return raw || '—'
    return arr.map((x) => `${x.on || ''} ${x.from || ''}→${x.via ? `${x.via}→` : ''}${x.to || ''}`).join('；') || '—'
  } catch {
    return raw || '—'
  }
}
const fundUseYuanLabel = computed(() => labels.value.fundUseYuanLabel || '本次使用经费（元）')
const fundUseNoteLabel = computed(() => labels.value.fundUseNoteLabel || '经费使用说明')
const visitOnLabel = computed(() => labels.value.visitOnLabel || '来访日期')
const plagiarismUrlLabel = computed(() => labels.value.plagiarismUrlLabel || '查重报告链接')
const partyStageLabel = computed(() => labels.value.partyStageLabel || '当前发展阶段')
const stageOnLabel = computed(() => labels.value.stageOnLabel || '进入该阶段日期')
const observeOnLabel = computed(() => labels.value.observeOnLabel || '听课日期')
const observeNoteLabel = computed(() => labels.value.observeNoteLabel || '听课记录')
const scheduleImpactNoteLabel = computed(() => labels.value.scheduleImpactNoteLabel || '对课表的影响')
const contractAmountLabel = computed(() => labels.value.contractAmountLabel || '合同金额（元）')
const procureReturnFailLabel = computed(() => labels.value.procureReturnFailLabel || '验收不合格')
const returnNoteLabel = computed(() => labels.value.returnNoteLabel || '退货说明')
const moralObjectionLabel = computed(() => labels.value.moralObjectionLabel || '异议说明')
const allowPassExpire = computed(() => !!ticket.allowPassExpire)
const returnFuelLabel = computed(() => labels.value.returnFuelLabel || '回场油量')
const laborPlaceLabel = computed(() => labels.value.laborPlaceLabel || '劳动地点')
const effectiveOnLabel = computed(() => labels.value.effectiveOnLabel || '生效日期')
const certIssueNoLabel = computed(() => labels.value.certIssueNoLabel || '开具流水号')
const docRevLabel = computed(() => labels.value.docRevLabel || '正文版本号')
const fitoutWindowLabel = computed(() => labels.value.fitoutWindowLabel || '施工时段')
const issueCopiesLabel = computed(() => labels.value.issueCopiesLabel || '开具份数')
const signPartiesLabel = computed(() => labels.value.signPartiesLabel || '签署方')
const trainHoursLabel = computed(() => labels.value.trainHoursLabel || '本次培训学时')
const memberChangeNoteLabel = computed(() => labels.value.memberChangeNoteLabel || '成员变更说明')
const procureAmountLabel = computed(() => labels.value.procureAmountLabel || '本次申购金额（元）')
const exceptionTypeLabel = computed(() => labels.value.exceptionTypeLabel || '异常类型')
const visitPurposeLabel = computed(() => labels.value.visitPurposeLabel || '来访目的')
const rectifyNoteLabel = computed(() => labels.value.rectifyNoteLabel || '整改说明')
const violationPersonLabel = computed(() => labels.value.violationPersonLabel || '违章责任人')
const projNodeRemindHint = computed(() => labels.value.projNodeRemindHint || '')
const passExpireAtLabel = computed(() => labels.value.passExpireAtLabel || '通行码有效至')
const passExpiredLabel = computed(() => labels.value.passExpiredLabel || '已失效')
function isPassExpired(row) {
  if (!allowPassExpire.value || !row || !row.passExpireAt) return false
  const t = Date.parse(String(row.passExpireAt).replace('T', ' '))
  return Number.isFinite(t) && Date.now() > t
}
const adminCheckinLabel = computed(() => labels.value.adminCheckinLabel || '补签')
const adminCheckinHint = computed(() => labels.value.adminCheckinHint || '')
const lateMinutesLabel = computed(() => labels.value.lateMinutesLabel || '迟到分钟数')
const wishOrderLabel = computed(() => labels.value.wishOrderLabel || '志愿序')
const volunteerRoleLabel = computed(() => labels.value.volunteerRoleLabel || '报名岗位')
const companionNamesLabel = computed(() => labels.value.companionNamesLabel || '同行人姓名')
const certPickupLabel = computed(() => labels.value.certPickupLabel || '领取方式')
const expressNoLabel = computed(() => labels.value.expressNoLabel || '快递单号')
const certUrgentLabel = computed(() => labels.value.certUrgentLabel || '加急件')
const sealCopiesLabel = computed(() => labels.value.sealCopiesLabel || '用印份数')
const invoiceCountLabel = computed(() => labels.value.invoiceCountLabel || '发票张数')
const visitorCountLabel = computed(() => labels.value.visitorCountLabel || '随行人数')
const awardCertNoLabel = computed(() => labels.value.awardCertNoLabel || '证书编号')
const driverNameLabel = computed(() => labels.value.driverNameLabel || '驾驶员')
const passengerNamesLabel = computed(() => labels.value.passengerNamesLabel || '随车人')
const compHoursLabel = computed(() => labels.value.compHoursLabel || '核定调休小时')
const vendorQuotesLabel = computed(() => labels.value.vendorQuotesLabel || '比价供应商')
const mileageLabel = computed(() => labels.value.mileageLabel || '行驶里程')
const absentExportHint = computed(() => labels.value.absentExportHint || '')
const activityProofHint = computed(() => labels.value.activityProofHint || '')
const allowLottery = computed(() => !!ticket.allowLottery)
const lotteryDrawLabel = computed(() => labels.value.lotteryDrawLabel || '抽签录取')
const lotteryDrawHint = computed(() => labels.value.lotteryDrawHint || '')
const allowPostGallery = computed(() => !!ticket.allowPostGallery)
const postGalleryLabel = computed(() => labels.value.postGalleryLabel || '活动相册')
const postGalleryHint = computed(() => labels.value.postGalleryHint || '')
const requireCreditWritebackAck = computed(() => !!ticket.requireCreditWritebackAck)
const creditWritebackHint = computed(() => labels.value.creditWritebackHint || '')
const lotteryLoading = ref(false)
async function runLotteryDraw() {
  const itemId = list.value?.[0]?.itemId || list.value?.[0]?.archiveId
  if (!itemId) {
    ElMessage.warning('请先查询到含档案编号的记录再抽签')
    return
  }
  lotteryLoading.value = true
  try {
    const res = await http.post('/api/tickets/lottery-draw', { itemId })
    const d = res.data || {}
    ElMessage.success(`已抽取 ${d.drawn || 0} 人（池 ${d.poolSize || 0}）`)
    load()
  } finally {
    lotteryLoading.value = false
  }
}
const interactThicken = computed(() => getSchema()?.interactThicken || {})
const mutualAdjustLogOn = computed(() => !!interactThicken.value.mutualAdjustLog)
const mutualResultExportNotifyOn = computed(() => !!interactThicken.value.mutualResultExportNotify)
const mutualAdjustLogTitle = computed(() => labels.value.mutualAdjustLogTitle || '调剂记录')
const mutualResultExportLabel = computed(() => labels.value.mutualResultExportLabel || '导出互选结果')
const mutualResultNotifyLabel = computed(() => labels.value.mutualResultNotifyLabel || '通知已互选学生')
const mutualNotifyLoading = ref(false)
const adjustLogVisible = ref(false)
const adjustLogList = ref([])
const adjustLogTotal = ref(0)
const adjustLogPage = ref(1)

async function openAdjustLog() {
  adjustLogPage.value = 1
  await loadAdjustLog()
  adjustLogVisible.value = true
}

async function loadAdjustLog() {
  const res = await http.get('/api/tickets/adjust-log', {
    params: { page: adjustLogPage.value, size: 10 },
  })
  const data = res.data || res
  adjustLogList.value = data.list || []
  adjustLogTotal.value = data.total || 0
}

async function exportMutualResults() {
  const res = await http.get('/api/tickets/mutual-match-result')
  const data = res.data || res
  const rows = Array.isArray(data) ? data : data.list || []
  downloadCsv(
    `mutual_results_${Date.now()}.csv`,
    ['编号', '学生', '状态', '申请时间', '对象编号'],
    rows.map((r) => [r.id, r.username || '', r.status || '', r.applyAt || '', r.itemId || '']),
  )
  ElMessage.success(`已导出 ${rows.length} 条互选结果`)
}

async function notifyMutualResults() {
  mutualNotifyLoading.value = true
  try {
    const res = await http.post('/api/tickets/mutual-result-notify')
    const data = res.data || res
    ElMessage.success(labels.value.mutualResultNotifyDone || `已发送 ${data.notified || 0} 条通知`)
  } finally {
    mutualNotifyLoading.value = false
  }
}

const exportBtnLabel = computed(() => {
  if (status.value === 'absent' && (labels.value.absentExportLabel || '')) {
    return labels.value.absentExportLabel
  }
  if (allowSealLedgerExport.value && sealLedgerExportLabel.value) {
    return sealLedgerExportLabel.value
  }
  return monthExportHint.value || checkExportHint.value || '导出 CSV'
})
const issuePassCode = computed(() => !!ticket.issuePassCode)
const passCodeLabel = computed(() => ticket.passCodeLabel || '通行码')
const allowQty = computed(() => !!ticket.allowQty)
const pickLoanPeriod = computed(() => !!ticket.pickLoanPeriod)
const dueLabel = computed(() => ticketDueLabel())
const fineLabel = computed(() => ticketFineLabel())
const finePaidLabel = computed(() => ticketFinePaidLabel())
const allowFineWaive = computed(() => !!ticket.allowFineWaive)
const fineWaiveLabel = computed(() => labels.value.fineWaiveLabel || '罚款减免')
const allowProcureRef = computed(() => !!ticket.allowProcureRef)
const confirmProcureLabel = computed(
  () => labels.value.confirmProcureTransferLabel || '确认申购转入',
)
const procureToStockIn = computed(() => !!ticket.procureToStockIn)
const toStockInLabel = computed(() => labels.value.toStockInLabel || '一键入库')
const userLabel = computed(() => roleLabel('user', '申请人'))
const showPickup = computed(() => hasTrait('pickupFlow'))
const approveEndsFlow = computed(() => !!ticket.approveEndsFlow)
const showFollowCols = computed(() => ticketShowsFollowCols())
const channelLabel = computed(() => followChannelLabel())
const nextAtLabel = computed(() => nextFollowLabel())
const showScheduleCols = computed(() => ticketShowsScheduleCols(ticket, archive))
const showTypeCol = computed(() => ticketShowsTypeCol(archive))
const showLocationCol = computed(() => ticketShowsLocationCol(archive))
const showPriorityCols = computed(() => ticketShowsPriorityCols())
const allowEmergencyContact = computed(() => !!ticket.allowEmergencyContact)
const requireInsuranceAck = computed(() => !!ticket.requireInsuranceAck)
const emergencyContactLabel = computed(() => labels.value.emergencyContactLabel || '紧急联系人')
const emergencyPhoneLabel = computed(() => labels.value.emergencyPhoneLabel || '紧急联系电话')
const insuranceAckColLabel = computed(() => labels.value.insuranceAckLabel || '保险声明')
const showFine = computed(
  () => hasTrait('loanFine') || !!ticket.fineLabel || Number(ticket.noShowPenaltyYuan) > 0,
)

const superAdmin = localStorage.getItem('superAdmin') === 'true'
const myUid = localStorage.getItem('uid') || ''

/** 驿站/失物核销流：approved/overdue 即终态；子管仅处理人可完结 */
function canFinish(row) {
  if (!row) return false
  // 报修等：须申请人确认完结，管理端不代点
  if (ticket.applicantCompleteOnly) return false
  if (approveEndsFlow.value && showPickup.value) return false
  if (!(row.status === 'approved' || row.status === 'overdue')) return false
  if (superAdmin) return true
  const asg = row.assigneeUsername
  if (!asg) return true
  return asg === myUid
}

const allowBookLost = computed(() => !!(ticket.allowBookLost || hasCap('book_lost')))
const compensateVerb = computed(
  () => ticket.verbs?.compensate || labels.value.bookCompensateVerb || '登记赔偿完成',
)

function canCompensate(row) {
  return !!allowBookLost.value && !!row && row.status === 'lost'
}

async function doCompensate(row) {
  await ElMessageBox.confirm(
    `确认「${row.title || ('编号 ' + row.id)}」赔偿已完成？`,
    compensateVerb.value,
  )
  await http.post(`/api/tickets/${row.id}/compensate`)
  ElMessage.success(labels.value.bookCompensateOkMessage || '赔偿已登记完成')
  load()
}

const adminCheckin = reactive({
  visible: false,
  loading: false,
  row: null,
  lateMinutes: 0,
  note: '',
})

function canAdminCheckin(row) {
  if (!allowAdminCheckin.value || !allowCheckin.value || !row) return false
  if (row.status !== 'approved') return false
  return !row.checkedInAt
}

function openAdminCheckin(row) {
  Object.assign(adminCheckin, {
    visible: true,
    loading: false,
    row,
    lateMinutes: 0,
    note: '',
  })
}

async function submitAdminCheckin() {
  if (!adminCheckin.row) return
  adminCheckin.loading = true
  try {
    const body = { note: (adminCheckin.note || '').trim() }
    if (allowLateMinutes.value) body.lateMinutes = Number(adminCheckin.lateMinutes) || 0
    await http.post(`/api/tickets/${adminCheckin.row.id}/admin-checkin`, body)
    ElMessage.success('补签已登记')
    adminCheckin.visible = false
    load()
  } catch {
    // http 拦截器已提示
  } finally {
    adminCheckin.loading = false
  }
}

function canConfirmProcure(row) {
  return !!allowProcureRef.value && !!row && String(row.procureRefNo || '').trim()
}

async function doConfirmProcure(row) {
  await ElMessageBox.confirm(
    `确认申购单号「${row.procureRefNo}」已转入本领用单？`,
    confirmProcureLabel.value,
  )
  try {
    await http.post(`/api/tickets/${row.id}/confirm-procure-transfer`)
    ElMessage.success('已确认申购转入')
    load()
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e?.message || '操作失败')
  }
}

function canToStockIn(row) {
  if (!procureToStockIn.value || !row) return false
  return row.status === 'approved' || row.status === 'returned' || row.status === 'completed'
}

async function doToStockIn(row) {
  await ElMessageBox.confirm(
    `将申购单「${row.title || row.id}」明细一键转入库存？`,
    toStockInLabel.value,
  )
  try {
    const res = await http.post(`/api/tickets/${row.id}/to-stock-in`)
    const data = res.data?.data || res.data || {}
    const n = data.stockIn?.count ?? data.count
    ElMessage.success(n != null ? `已入库 ${n} 行` : '已入库')
    load()
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e?.message || '入库失败')
  }
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

function remarkText(v) {
  if (!v) return '—'
  return plainFromHtml(String(v)) || '—'
}

function canPickup(row) {
  if (!showPickup.value || !row) return false
  if (row.pickupAt) return false
  // 与后端一致：退库后不可再登记，避免库存回补错乱
  return row.status === 'approved' || row.status === 'overdue'
}

function canRedeemPickup(row) {
  if (!allowCertPickupRedeem.value || !row) return false
  if (!row.pickupRedeemCode || row.pickupRedeemed) return false
  return row.status === 'approved' || row.status === 'returned'
}

function canFinePaid(row) {
  if (!showFine.value || !row) return false
  if (!(Number(row.fineYuan) > 0)) return false
  if (row.fineStatus === 'paid' || row.fineStatus === 'waived') return false
  return ['approved', 'overdue', 'returned'].includes(row.status)
}

function canFineWaive(row) {
  if (!allowFineWaive.value || !showFine.value || !row) return false
  if (row.fineStatus === 'paid' || row.fineStatus === 'waived') return false
  if (!(Number(row.fineYuan) > 0) && row.status !== 'overdue') return false
  return ['approved', 'overdue', 'returned'].includes(row.status)
}

const list = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const status = ref(null)
const ratedOnly = ref(false)
const todayOnly = ref(!!props.defaultToday)
const progressVisible = ref(false)
const progressId = ref(null)
const finishVisible = ref(false)
const finishRow = ref(null)

function typeColor(key) {
  const s = String(key || '')
  let h = 0
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0
  const hue = h % 360
  return `hsl(${hue} 55% 48%)`
}

function listParams(extra = {}) {
  const params = {
    page: page.value,
    size: size.value,
    status: status.value || undefined,
    ...extra,
  }
  if (allowRating.value && ratedOnly.value) params.rated = true
  if (todayBoardOn.value && todayOnly.value) params.todayAssigned = true
  return params
}

function onFilter() {
  page.value = 1
  load()
}

async function load() {
  const res = await http.get('/api/tickets', { params: listParams() })
  list.value = res.data.list
  total.value = res.data.total
}

async function finish(row) {
  if (repairFinishNeeded.value) {
    finishRow.value = row
    finishVisible.value = true
    return
  }
  const body = {}
  if (ticket.allowExceptionClose) {
    const { value: er } = await ElMessageBox.prompt(
      '异常件可填写原因；正常办结可留空',
      labels.value.exceptionReasonLabel || '异常件原因',
      {
        confirmButtonText: '继续',
        cancelButtonText: '取消',
        inputPlaceholder: '选填',
      },
    ).catch(() => ({ value: null }))
    if (er === null) return
    if (String(er || '').trim()) body.exceptionReason = String(er).trim()
    const { value: dn } = await ElMessageBox.prompt(
      '如有破损理赔说明可填写',
      labels.value.damageClaimLabel || '破损理赔说明',
      {
        confirmButtonText: '办结',
        cancelButtonText: '取消',
        inputPlaceholder: '选填',
        inputType: 'textarea',
      },
    ).catch(() => ({ value: null }))
    if (dn === null) return
    if (String(dn || '').trim()) body.damageClaimNote = String(dn).trim()
  } else {
    await ElMessageBox.confirm(`确认标记「${row.title}」为已完成？`, '完成')
  }
  await http.post(`/api/tickets/${row.id}/complete`, body)
  ElMessage.success('已完成')
  load()
}

function printTicket(row) {
  const ok = printTicketDocument(row, {
    ticket,
    labels: labels.value,
    statusText: statusLabel,
    personLabel,
    remarkText: (r) => plainFromHtml(r || ''),
  })
  if (!ok) ElMessage.warning('请允许弹出窗口以打印')
}

const repairThickenOn = computed(() => !!ticket.repairThicken || !!ticket.allowHoldResume)

function canHold(row) {
  if (!repairThickenOn.value || !ticket.allowHoldResume || !row) return false
  return row.status === 'approved' || row.status === 'overdue'
}

function canResume(row) {
  return !!(repairThickenOn.value && ticket.allowHoldResume && row && row.status === 'paused')
}

function canRejectAssign(row) {
  if (!repairThickenOn.value || !row) return false
  return row.status === 'approved' || row.status === 'overdue' || row.status === 'paused'
}

async function doHold(row) {
  const { value } = await ElMessageBox.prompt('请填写挂起原因', '挂起工单', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    inputPattern: /\S+/,
    inputErrorMessage: '请填写原因',
  })
  await http.post(`/api/tickets/${row.id}/hold`, { reason: value })
  ElMessage.success('已挂起')
  load()
}

async function doResume(row) {
  await ElMessageBox.confirm(`确认恢复「${row.title || row.id}」继续处理？`, '恢复')
  await http.post(`/api/tickets/${row.id}/resume`)
  ElMessage.success('已恢复')
  load()
}

async function doRejectAssign(row) {
  const { value } = await ElMessageBox.prompt('请填写拒单原因（将回池待受理）', '拒单回池', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    inputPattern: /\S+/,
    inputErrorMessage: '请填写原因',
  })
  await http.post(`/api/tickets/${row.id}/reject-assignment`, { reason: value })
  ElMessage.success('已回池')
  load()
}

function openProgress(row) {
  progressId.value = row.id
  progressVisible.value = true
}

async function doPickup(row) {
  const applied = Math.max(1, Number(row.qty) || 1)
  const { value } = await ElMessageBox.prompt(
    '领取地点（可留空则使用系统默认配置；两者皆空将无法登记）',
    '领取登记',
    {
      confirmButtonText: '下一步',
      cancelButtonText: '取消',
      inputPlaceholder: '如 行政楼地下库房',
      inputValue: row.pickupPlace || '',
      inputValidator: (v) => {
        if (String(v || '').trim().length > 128) return '领取地点过长'
        return true
      },
    },
  ).catch(() => ({ value: null }))
  if (value === null) return
  const body = { pickupPlace: String(value || '').trim() }
  if (allowQty.value) {
    const { value: qty } = await ElMessageBox.prompt(
      `实发数量（申领 ${applied}，不可超过）`,
      '领取登记',
      {
        confirmButtonText: '登记',
        cancelButtonText: '取消',
        inputValue: String(applied),
        inputValidator: (v) => {
          const s = String(v ?? '').trim()
          if (!/^[1-9]\d*$/.test(s)) return '请输入正整数'
          const n = Number(s)
          if (n > applied) return `不能超过申领数量 ${applied}`
          return true
        },
      },
    ).catch(() => ({ value: null }))
    if (qty === null) return
    body.actualQty = Number(qty)
  }
  try {
    await http.post(`/api/tickets/${row.id}/pickup`, body)
    ElMessage.success('已登记领取，已通知申请人')
    load()
  } catch {
    // http 拦截器已提示业务错误
  }
}

async function doRedeemPickup(row) {
  const { value } = await ElMessageBox.prompt(
    pickupRedeemHint.value || `请填写${pickupRedeemCodeLabel.value}`,
    pickupRedeemedLabel.value,
    {
      confirmButtonText: '核销',
      cancelButtonText: '取消',
      inputPlaceholder: pickupRedeemCodeLabel.value,
      inputValidator: (v) => {
        if (!String(v || '').trim()) return `请填写${pickupRedeemCodeLabel.value}`
        return true
      },
    },
  ).catch(() => ({ value: null }))
  if (value === null) return
  try {
    await http.post(`/api/tickets/${row.id}/redeem-pickup`, { code: String(value || '').trim() })
    ElMessage.success('已核销领取')
    load()
  } catch {
    // http 拦截器已提示业务错误
  }
}

async function doFinePaid(row) {
  await ElMessageBox.confirm(`确认「${row.title || row.id}」${finePaidLabel.value}？`, finePaidLabel.value)
  await http.post(`/api/tickets/${row.id}/fine-paid`)
  ElMessage.success(`已标记${finePaidLabel.value}`)
  load()
}

async function doFineWaive(row) {
  const { value } = await ElMessageBox.prompt('请填写减免原因', fineWaiveLabel.value, {
    confirmButtonText: '确认减免',
    cancelButtonText: '取消',
    inputPattern: /\S+/,
    inputErrorMessage: '请填写原因',
  })
  await http.post(`/api/tickets/${row.id}/fine-waive`, { reason: value })
  ElMessage.success('已登记罚款减免')
  load()
}

async function exportCsv() {
  const res = await http.get('/api/tickets', {
    params: listParams({ page: 1, size: 5000 }),
  })
  const rows = res.data?.list || []
  if (!rows.length) {
    ElMessage.warning('当前筛选无数据可导出')
    return
  }
  const headers = ['编号', '标题']
  if (showTypeCol.value) headers.push(typeColLabel.value)
  if (showLocationCol.value) headers.push(locationColLabel.value)
  if (showPriorityCols.value) headers.push('优先级', '联系电话')
  if (allowEmergencyContact.value) headers.push(emergencyContactLabel.value, emergencyPhoneLabel.value)
  if (requireInsuranceAck.value) headers.push(insuranceAckColLabel.value)
  if (allowWishOrder.value) headers.push(wishOrderLabel.value)
  if (allowVolunteerRole.value) headers.push(volunteerRoleLabel.value)
  if (allowCompanions.value) headers.push(companionNamesLabel.value)
  if (allowCertPickup.value) headers.push(certPickupLabel.value, '邮寄地址')
  if (allowSealCopies.value) headers.push(sealCopiesLabel.value, '装订说明')
  if (allowSealLedgerExport.value) {
    headers.push(sealCopyNosLabel.value, sealWitnessAckLabel.value)
  }
  if (allowExpenseInvoice.value) headers.push(invoiceCountLabel.value, '报销金额')
  if (allowVisitorCount.value) headers.push(visitorCountLabel.value)
  if (allowAwardCertNo.value) headers.push(awardCertNoLabel.value)
  if (allowVendorQuotes.value) headers.push(vendorQuotesLabel.value)
  if (allowFleetMileage.value) headers.push(mileageLabel.value, '油耗备注')
  if (allowFleetCrew.value) headers.push(driverNameLabel.value, passengerNamesLabel.value)
  if (allowCompHours.value) headers.push(compHoursLabel.value)
  if (allowReturnFuel.value) headers.push(returnFuelLabel.value)
  if (allowLaborPlace.value) headers.push(laborPlaceLabel.value)
  if (allowEffectiveOn.value) headers.push(effectiveOnLabel.value)
  if (allowCertIssueNo.value) headers.push(certIssueNoLabel.value)
  if (allowDocRev.value) headers.push(docRevLabel.value)
  if (allowFitoutQuiet.value) headers.push(fitoutWindowLabel.value)
  if (allowIssueCopies.value) headers.push(issueCopiesLabel.value)
  if (allowSignParties.value) headers.push(signPartiesLabel.value)
  if (allowTrainHours.value) headers.push(trainHoursLabel.value)
  if (allowMemberChange.value) headers.push(memberChangeNoteLabel.value)
  if (allowProcureBudget.value) headers.push(procureAmountLabel.value)
  if (allowCheckinException.value) headers.push(exceptionTypeLabel.value)
  if (allowVisitPurpose.value) headers.push(visitPurposeLabel.value)
  if (allowFitoutRectify.value) headers.push(rectifyNoteLabel.value)
  if (allowFleetViolation.value) headers.push(violationPersonLabel.value)
  if (allowProjFundUse.value) headers.push(fundUseYuanLabel.value, fundUseNoteLabel.value)
  if (allowVisitSlotRemain.value) headers.push(visitOnLabel.value)
  if (allowPlagiarismUrl.value) headers.push(plagiarismUrlLabel.value)
  if (allowPartyStage.value) headers.push(partyStageLabel.value, stageOnLabel.value)
  if (allowEvalObserve.value) headers.push(observeOnLabel.value, observeNoteLabel.value)
  if (allowScheduleImpact.value) headers.push(scheduleImpactNoteLabel.value)
  if (allowContractAmount.value) headers.push(contractAmountLabel.value)
  if (allowExpenseLines.value) headers.push(expenseLinesLabel.value)
  if (allowTripLegs.value) headers.push(tripLegsLabel.value)
  if (allowProjChangeLog.value) headers.push(changeLogNoteLabel.value)
  if (allowCertVerify.value) headers.push(certVerifyCodeLabel.value)
  if (allowVisitWalkIn.value) headers.push(visitWalkInLabel.value)
  if (allowCheckinProxy.value) headers.push(checkinProxyByLabel.value)
  if (allowClubRoster.value) headers.push(clubRosterLabel.value)
  if (allowCarpassParkingMutex.value) headers.push(parkingOnLabel.value)
  if (allowContractRenew.value) headers.push(renewOnLabel.value, renewNoteLabel.value)
  if (allowCertPickupRedeem.value) headers.push(pickupRedeemCodeLabel.value, pickupRedeemedLabel.value)
  if (allowProcureReturn.value) headers.push(procureReturnFailLabel.value, returnNoteLabel.value)
  if (allowMoralObjection.value) headers.push(moralObjectionLabel.value)
  if (issuePassCode.value && allowPassExpire.value) headers.push(passExpireAtLabel.value)
  headers.push(userLabel.value, '处理人', '状态')
  if (allowQty.value) headers.push('数量')
  if (pickLoanPeriod.value) headers.push(dueLabel.value)
  if (showFine.value) headers.push(fineLabel.value)
  if (showPickup.value) {
    headers.push('领取地点', '领取时间')
    if (allowQty.value) headers.push('实发数量')
  }
  if (showScheduleCols.value) headers.push('开始', '结束')
  headers.push('说明', '附件')
  if (exportAttachUrls.value) headers.push('结单附件')
  if (showFollowCols.value) headers.push(channelLabel.value, nextAtLabel.value)
  headers.push('申请时间', '受理时间')
  if (allowCheckin.value) headers.push('签到时间')
  headers.push('完成时间')
  if (allowRating.value) headers.push('评分', '短评', '评价时间')

  const data = rows.map((row) => {
    let person = personLabel(row, '')
    if (maskStuNo.value && person) {
      person = String(person).replace(/\d{4,}/g, (m) => `${m.slice(0, 2)}****${m.slice(-2)}`)
    }
    const line = [row.id, row.title]
    if (showTypeCol.value) line.push(row.typeName)
    if (showLocationCol.value) line.push(row.location)
    if (showPriorityCols.value) line.push(row.priority || '', row.contactPhone || '')
    if (allowEmergencyContact.value) {
      line.push(row.emergencyContact || '', row.emergencyPhone || '')
    }
    if (requireInsuranceAck.value) {
      line.push(row.insuranceAck ? '已勾选' : '')
    }
    if (allowWishOrder.value) {
      line.push(row.wishOrder === 1 ? '第一志愿' : row.wishOrder === 2 ? '第二志愿' : '')
    }
    if (allowVolunteerRole.value) {
      line.push(row.volunteerRole || '')
    }
    if (allowCompanions.value) {
      line.push(row.companionNames || '')
    }
    if (allowCertPickup.value) {
      line.push(row.pickupMethod || '', row.mailAddress || '')
    }
    if (allowSealCopies.value) {
      line.push(row.sealCopies != null ? row.sealCopies : '', row.bindNote || '')
    }
    if (allowSealLedgerExport.value) {
      line.push(row.sealCopyNos || '', row.sealWitnessAck ? '已监印' : '')
    }
    if (allowExpenseInvoice.value) {
      line.push(row.invoiceCount != null ? row.invoiceCount : '', row.fineYuan > 0 ? row.fineYuan : '')
    }
    if (allowVisitorCount.value) {
      line.push(row.visitorCount != null ? row.visitorCount : '')
    }
    if (allowAwardCertNo.value) {
      line.push(row.awardCertNo || '')
    }
    if (allowVendorQuotes.value) {
      line.push(row.vendorQuotes || '')
    }
    if (allowFleetMileage.value) {
      line.push(row.mileageKm != null ? row.mileageKm : '', row.fuelNote || '')
    }
    if (allowFleetCrew.value) {
      line.push(row.driverName || '', row.passengerNames || '')
    }
    if (allowCompHours.value) {
      line.push(row.compHours != null ? row.compHours : '')
    }
    if (allowReturnFuel.value) {
      line.push(row.returnFuel != null ? row.returnFuel : '')
    }
    if (allowLaborPlace.value) {
      line.push(row.laborPlace || '')
    }
    if (allowEffectiveOn.value) {
      line.push(row.effectiveOn || '')
    }
    if (allowCertIssueNo.value) {
      line.push(row.certIssueNo || '')
    }
    if (allowDocRev.value) {
      line.push(row.docRev || '')
    }
    if (allowFitoutQuiet.value) {
      line.push([row.workStart, row.workEnd].filter(Boolean).join('-'))
    }
    if (allowIssueCopies.value) {
      line.push(row.issueCopies ?? '')
    }
    if (allowSignParties.value) {
      line.push(row.signParties || '')
    }
    if (allowTrainHours.value) {
      line.push(row.trainHours ?? '')
    }
    if (allowMemberChange.value) {
      line.push(row.memberChangeNote || '')
    }
    if (allowProcureBudget.value) {
      line.push(row.procureAmount ?? '')
    }
    if (allowCheckinException.value) {
      line.push(row.exceptionType || '')
    }
    if (allowVisitPurpose.value) {
      line.push(row.visitPurpose || '')
    }
    if (allowFitoutRectify.value) {
      line.push(row.rectifyNote || '')
    }
    if (allowFleetViolation.value) {
      line.push(row.violationPerson || '')
    }
    if (allowProjFundUse.value) {
      line.push(row.fundUseYuan ?? '', row.fundUseNote || '')
    }
    if (allowVisitSlotRemain.value) {
      line.push(row.visitOn || '')
    }
    if (allowPlagiarismUrl.value) {
      line.push(row.plagiarismUrl || '')
    }
    if (allowPartyStage.value) {
      line.push(row.partyStage || '', row.stageOn || '')
    }
    if (allowEvalObserve.value) {
      line.push(row.observeOn || '', row.observeNote || '')
    }
    if (allowScheduleImpact.value) {
      line.push(row.scheduleImpactNote || '')
    }
    if (allowContractAmount.value) {
      line.push(row.contractAmount ?? '')
    }
    if (allowExpenseLines.value) {
      line.push(formatExpenseLines(row.expenseLines))
    }
    if (allowTripLegs.value) {
      line.push(formatTripLegs(row.tripLegs))
    }
    if (allowProjChangeLog.value) {
      line.push(row.changeLogNote || '')
    }
    if (allowCertVerify.value) {
      line.push(row.verifyCode || '')
    }
    if (allowVisitWalkIn.value) {
      line.push(row.walkIn ? '是' : '')
    }
    if (allowCheckinProxy.value) {
      line.push(row.checkinProxyBy || '')
    }
    if (allowClubRoster.value) {
      line.push(formatClubMembers(row.clubMembers))
    }
    if (allowCarpassParkingMutex.value) {
      line.push(row.parkingOn || '')
    }
    if (allowContractRenew.value) {
      line.push(row.renewOn || '', row.renewNote || '')
    }
    if (allowCertPickupRedeem.value) {
      line.push(row.pickupRedeemCode || '', row.pickupRedeemed ? '是' : '否')
    }
    if (allowProcureReturn.value) {
      line.push(row.returnFail ? '是' : '否', row.returnNote || '')
    }
    if (allowMoralObjection.value) {
      line.push(row.objectionNote || '')
    }
    if (issuePassCode.value && allowPassExpire.value) {
      line.push(row.passExpireAt || '')
    }
    line.push(
      person,
      row.assigneeUsername || '',
      statusLabel(row),
    )
    if (allowQty.value) line.push(row.qty ?? 1)
    if (pickLoanPeriod.value) line.push(row.dueAt || '')
    if (showFine.value) {
      line.push(Number(row.fineYuan) > 0 ? `¥${row.fineYuan} · ${row.fineStatus || ''}` : '')
    }
    if (showPickup.value) {
      line.push(row.pickupPlace || '', row.pickupAt || '')
      if (allowQty.value) line.push(row.actualQty ?? '')
    }
    if (showScheduleCols.value) line.push(row.startAt, row.endAt)
    line.push(remarkText(row.remark), row.attachUrl || '')
    if (exportAttachUrls.value) line.push(row.closeAttachUrl || '')
    if (showFollowCols.value) {
      line.push(row.contactChannel || '', row.nextFollowAt || '')
    }
    line.push(row.applyAt, row.approveAt)
    if (allowCheckin.value) line.push(row.checkedInAt || '')
    line.push(row.returnAt)
    if (allowRating.value) {
      line.push(row.rating || '', row.ratingRemark || '', row.ratedAt || '')
    }
    return line
  })
  const tag = ratedOnly.value ? 'rated' : (status.value || 'all')
  downloadCsv(`tickets_${tag}_${Date.now()}.csv`, headers, data)
  ElMessage.success(`已导出 ${rows.length} 条（UTF-8，可用 Excel 直接打开）`)
}

onMounted(() => {
  if (allowRating.value && String(route.query.rated || '') === '1') {
    ratedOnly.value = true
  }
  const st = String(route.query.status || '').trim()
  if (st && Object.prototype.hasOwnProperty.call(states.value, st)) {
    status.value = st
  }
  load()
})
