<template>
  <div>
    <div class="toolbar">
      <el-select v-model="status" clearable placeholder="全部状态" style="width:140px" @change="onFilter">
        <el-option v-for="(lab, key) in states" :key="key" :label="lab" :value="key" />
      </el-select>
      <el-checkbox
        v-if="allowRating"
        v-model="ratedOnly"
        style="margin-left:4px"
        @change="onFilter"
      >仅已评分</el-checkbox>
      <el-checkbox
        v-if="todayBoardOn"
        v-model="todayOnly"
        style="margin-left:4px"
        @change="onFilter"
      >今日处理中</el-checkbox>
      <el-button type="primary" @click="load">查询</el-button>
      <el-button :disabled="!list.length" @click="exportCsv">{{ exportBtnLabel }}</el-button>
      <el-checkbox
        v-if="stuNoMaskOn"
        v-model="maskStuNo"
        style="margin-left:4px"
      >{{ stuNoMaskHint || '学号脱敏导出' }}</el-checkbox>
    </div>
    <SchemaLabelHints :keys="recordsHintKeys" />
    <p v-if="todayBoardOn && todayBoardHint" class="board-hint">{{ todayBoardHint }}</p>
    <div class="table-scroll">
    <el-table :data="list" stripe>
      <el-table-column prop="id" label="编号" width="70" />
      <el-table-column prop="title" :label="ticket.label || '标题'" min-width="140" show-overflow-tooltip />
      <el-table-column v-if="showTypeCol" prop="typeName" :label="typeColLabel" width="110" show-overflow-tooltip>
        <template #default="{ row }">
          <span v-if="categoryColorOn" class="type-dot" :style="{ background: typeColor(row.typeName || row.typeId) }" />
          {{ row.typeName || '—' }}
        </template>
      </el-table-column>
      <el-table-column v-if="showLocationCol" prop="location" :label="locationColLabel" min-width="140" show-overflow-tooltip />
      <el-table-column v-if="showPriorityCols" prop="priority" label="优先级" width="90" />
      <el-table-column v-if="showPriorityCols" prop="contactPhone" label="联系电话" width="120" show-overflow-tooltip />
      <el-table-column
        v-if="allowEmergencyContact"
        prop="emergencyContact"
        :label="emergencyContactLabel"
        width="120"
        show-overflow-tooltip
      />
      <el-table-column
        v-if="allowEmergencyContact"
        prop="emergencyPhone"
        :label="emergencyPhoneLabel"
        width="120"
        show-overflow-tooltip
      />
      <el-table-column
        v-if="requireInsuranceAck"
        prop="insuranceAck"
        label="保险声明"
        width="100"
      >
        <template #default="{ row }">{{ row.insuranceAck ? '已勾选' : '—' }}</template>
      </el-table-column>
      <el-table-column :label="userLabel" width="110">
        <template #default="{ row }">{{ personLabel(row) }}</template>
      </el-table-column>
      <el-table-column prop="assigneeUsername" label="处理人" width="110">
        <template #default="{ row }">{{ row.assigneeUsername || '—' }}</template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">{{ statusLabel(row) }}</template>
      </el-table-column>
      <el-table-column v-if="allowQty" prop="qty" label="数量" width="70" />
      <el-table-column v-if="pickLoanPeriod" prop="dueAt" :label="dueLabel" width="170" />
      <el-table-column v-if="showFine" :label="fineLabel" width="100">
        <template #default="{ row }">
          <span v-if="row.fineYuan > 0">¥{{ row.fineYuan }} · {{ row.fineStatus || '—' }}</span>
          <span v-else>—</span>
        </template>
      </el-table-column>
      <el-table-column v-if="showPickup" label="领取" width="180">
        <template #default="{ row }">
          <span v-if="row.pickupAt">
            {{ row.pickupPlace || '已领' }}
            <template v-if="row.actualQty != null"> · 实发{{ row.actualQty }}</template>
            · {{ row.pickupAt }}
          </span>
          <span v-else class="muted">待登记</span>
        </template>
      </el-table-column>
      <el-table-column v-if="showScheduleCols" prop="startAt" label="开始" width="160" />
      <el-table-column v-if="showScheduleCols" prop="endAt" label="结束" width="160" />
      <el-table-column prop="remark" :label="richRemark ? '内容/说明' : '审核说明'" min-width="160" show-overflow-tooltip>
        <template #default="{ row }">{{ remarkText(row.remark) }}</template>
      </el-table-column>
      <el-table-column v-if="showFollowCols" :label="channelLabel" width="100" show-overflow-tooltip>
        <template #default="{ row }">{{ row.contactChannel || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="showFollowCols" :label="nextAtLabel" width="170">
        <template #default="{ row }">{{ row.nextFollowAt || '—' }}</template>
      </el-table-column>
      <el-table-column label="附件" width="90">
        <template #default="{ row }">
          <a v-if="row.attachUrl" :href="row.attachUrl" target="_blank" rel="noopener noreferrer">查看</a>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
      <el-table-column prop="applyAt" label="申请时间" width="170" />
      <el-table-column prop="approveAt" label="受理时间" width="170" />
      <el-table-column v-if="allowCheckin" label="签到" width="170">
        <template #default="{ row }">{{ row.checkedInAt || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="issuePassCode" :label="passCodeLabel" width="140">
        <template #default="{ row }">{{ row.passCode || '—' }}</template>
      </el-table-column>
      <el-table-column prop="returnAt" label="完成时间" width="170" />
      <el-table-column v-if="allowRating" label="评分" width="110">
        <template #default="{ row }">
          <span v-if="row.rating" class="rating">
            {{ row.rating }} 分
            <template v-if="row.ratingAnonymous"> · 匿名</template>
          </span>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
      <el-table-column v-if="allowRating && hasRatingDims" label="维度" min-width="160" show-overflow-tooltip>
        <template #default="{ row }">{{ formatDims(row.ratingDimsJson) }}</template>
      </el-table-column>
      <el-table-column v-if="allowRating" label="短评" min-width="140" show-overflow-tooltip>
        <template #default="{ row }">{{ row.ratingRemark || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="allowRating" label="评价时间" width="170">
        <template #default="{ row }">{{ row.ratedAt || '—' }}</template>
      </el-table-column>
      <el-table-column label="操作" min-width="200" fixed="right">
        <template #default="{ row }">
          <div class="table-ops">
          <el-button link type="info" @click="openProgress(row)">进度</el-button>
          <el-button
            v-if="canPickup(row)"
            link
            type="success"
            @click="doPickup(row)"
          >领取登记</el-button>
          <el-button
            v-if="canFinePaid(row)"
            link
            type="warning"
            @click="doFinePaid(row)"
          >{{ finePaidLabel }}</el-button>
          <el-button
            v-if="canFineWaive(row)"
            link
            type="info"
            @click="doFineWaive(row)"
          >{{ fineWaiveLabel }}</el-button>
          <el-button
            v-if="canConfirmProcure(row)"
            link
            type="primary"
            @click="doConfirmProcure(row)"
          >{{ confirmProcureLabel }}</el-button>
          <el-button
            v-if="canToStockIn(row)"
            link
            type="success"
            @click="doToStockIn(row)"
          >{{ toStockInLabel }}</el-button>
          <el-button
            v-if="canFinish(row)"
            link
            type="primary"
            @click="finish(row)"
          >{{ verbs.return || '完成' }}</el-button>
          <el-button
            v-if="printTicketOn"
            link
            @click="printTicket(row)"
          >{{ printTicketLabel }}</el-button>
          <el-button
            v-if="canCompensate(row)"
            link
            type="warning"
            @click="doCompensate(row)"
          >{{ compensateVerb }}</el-button>
          <el-button
            v-if="canHold(row)"
            link
            type="warning"
            @click="doHold(row)"
          >挂起</el-button>
          <el-button
            v-if="canResume(row)"
            link
            type="success"
            @click="doResume(row)"
          >恢复</el-button>
          <el-button
            v-if="canRejectAssign(row)"
            link
            type="danger"
            @click="doRejectAssign(row)"
          >拒单回池</el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>
    </div>
    <div class="pager">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="size"
        background
        layout="total, sizes, prev, pager, next"
        :page-sizes="[10, 20, 50]"
        :total="total"
        @current-change="load"
        @size-change="load"
      />
    </div>

    <TicketProgressDialog v-model="progressVisible" :ticket-id="progressId" />
    <RepairFinishDialog
      v-model="finishVisible"
      :row="finishRow"
      @done="load"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
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
const todayBoardOn = computed(() => !!ticket.todayBoard)
const todayBoardHint = computed(() => labels.value.todayBoardHint || '')
const printTicketOn = computed(
  () =>
    !!ticket.printTicket
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
const exportBtnLabel = computed(
  () => monthExportHint.value || checkExportHint.value || '导出 CSV',
)
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
  const w = window.open('', '_blank')
  if (!w) {
    ElMessage.warning('请允许弹出窗口以打印工单')
    return
  }
  const noun = ticket.label || '工单'
  const hint = labels.value.gradePrintHint || labels.value.bedPrintHint
    || labels.value.closedStackPrintHint || labels.value.equipQrPrintHint || ''
  w.document.write(`<!doctype html><html><head><title>${noun} ${row.id}</title>
<style>body{font-family:sans-serif;padding:24px;color:#111}h1{font-size:18px}p{margin:6px 0}.hint{color:#64748b;font-size:12px}</style>
</head><body>
<h1>${noun} #${row.id}</h1>
${hint ? `<p class="hint">${hint}</p>` : ''}
<p>标题：${row.title || '—'}</p>
<p>地点：${row.location || '—'}</p>
<p>状态：${statusLabel(row)}</p>
<p>申请人：${personLabel(row, '')}</p>
<p>处理人：${row.assigneeUsername || '—'}</p>
<p>期望上门：${row.preferredSlot || '—'}</p>
<p>响应时限：${row.responseDueAt || '—'}</p>
<p>完结时限：${row.dueAt || '—'}</p>
<p>说明：${remarkText(row.remark)}</p>
<script>window.onload=()=>{window.print()}<\/script>
</body></html>`)
  w.document.close()
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
</script>

<style scoped>
.toolbar { margin-bottom: 12px; display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.board-hint { margin: 0 0 10px; color: #64748b; font-size: 13px; }
.pager { margin-top: 16px; display: flex; justify-content: flex-end; }
.rating { color: #b45309; font-weight: 600; }
.muted { color: var(--portal-muted, #94a3b8); }
.type-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 6px;
  vertical-align: middle;
}
</style>
