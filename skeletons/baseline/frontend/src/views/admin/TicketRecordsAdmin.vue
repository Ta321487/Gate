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
      <el-button type="primary" @click="load">查询</el-button>
      <el-button :disabled="!list.length" @click="exportCsv">导出 CSV</el-button>
    </div>
    <el-table :data="list" stripe>
      <el-table-column prop="id" label="编号" width="70" />
      <el-table-column prop="title" :label="ticket.label || '标题'" min-width="140" />
      <el-table-column prop="typeName" label="类型" width="100" />
      <el-table-column prop="location" label="地点" width="140" />
      <el-table-column prop="username" :label="userLabel" width="110" />
      <el-table-column prop="assigneeUsername" label="处理人" width="110">
        <template #default="{ row }">{{ row.assigneeUsername || '—' }}</template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">{{ states[row.status] || row.status }}</template>
      </el-table-column>
      <el-table-column v-if="allowQty" prop="qty" label="数量" width="70" />
      <el-table-column v-if="pickLoanPeriod" prop="dueAt" :label="dueLabel" width="170" />
      <el-table-column v-if="showFine" :label="fineLabel" width="100">
        <template #default="{ row }">
          <span v-if="row.fineYuan > 0">¥{{ row.fineYuan }} · {{ row.fineStatus || '—' }}</span>
          <span v-else>—</span>
        </template>
      </el-table-column>
      <el-table-column v-if="showPickup" label="领取" width="140">
        <template #default="{ row }">
          <span v-if="row.pickupAt">{{ row.pickupPlace || '已领' }} · {{ row.pickupAt }}</span>
          <span v-else>—</span>
        </template>
      </el-table-column>
      <el-table-column prop="startAt" label="开始" width="160" />
      <el-table-column prop="endAt" label="结束" width="160" />
      <el-table-column prop="remark" :label="richRemark ? '内容/说明' : '审核说明'" min-width="160" show-overflow-tooltip>
        <template #default="{ row }">{{ remarkText(row.remark) }}</template>
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
      <el-table-column prop="returnAt" label="完成时间" width="170" />
      <el-table-column v-if="allowRating" label="评分" width="90" fixed="right">
        <template #default="{ row }">
          <span v-if="row.rating" class="rating">{{ row.rating }} 分</span>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
      <el-table-column v-if="allowRating" label="短评" min-width="140" show-overflow-tooltip>
        <template #default="{ row }">{{ row.ratingRemark || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="allowRating" label="评价时间" width="170">
        <template #default="{ row }">{{ row.ratedAt || '—' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="260" fixed="right">
        <template #default="{ row }">
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
            v-if="row.status === 'approved' || row.status === 'overdue'"
            link
            type="primary"
            @click="finish(row)"
          >{{ verbs.return || '完成' }}</el-button>
        </template>
      </el-table-column>
    </el-table>
    <div class="pager">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="size"
        background
        layout="total, prev, pager, next"
        :total="total"
        @current-change="load"
      />
    </div>

    <TicketProgressDialog v-model="progressVisible" :ticket-id="progressId" />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'
import TicketProgressDialog from '../../components/TicketProgressDialog.vue'
import { hasTrait, getSchema, ticketCopy, ticketDueLabel, ticketFineLabel, ticketFinePaidLabel } from '../../utils/domainSchema.js'
import { plainFromHtml } from '../../utils/richHtml.js'
import { downloadCsv } from '../../utils/csvDownload.js'

const route = useRoute()
const ticket = ticketCopy()
const verbs = computed(() => ticket.verbs || {})
const states = computed(() => ticket.states || {})
const richRemark = computed(() => !!ticket.richRemark)
const allowRating = computed(() => !!ticket.allowRating)
const allowCheckin = computed(() => !!ticket.allowCheckin)
const allowQty = computed(() => !!ticket.allowQty)
const pickLoanPeriod = computed(() => !!ticket.pickLoanPeriod)
const dueLabel = computed(() => ticketDueLabel())
const fineLabel = computed(() => ticketFineLabel())
const finePaidLabel = computed(() => ticketFinePaidLabel())
const userLabel = computed(() => getSchema()?.roles?.user?.label || '申请人')
const showPickup = computed(() => hasTrait('pickupFlow'))
const showFine = computed(
  () => hasTrait('loanFine') || !!ticket.fineLabel || Number(ticket.noShowPenaltyYuan) > 0,
)

function remarkText(v) {
  if (!v) return '—'
  return plainFromHtml(String(v)) || '—'
}

function canPickup(row) {
  if (!showPickup.value || !row) return false
  if (row.pickupAt) return false
  return row.status === 'approved' || row.status === 'returned'
}

function canFinePaid(row) {
  if (!showFine.value || !row) return false
  if (!(Number(row.fineYuan) > 0)) return false
  return row.fineStatus !== 'paid'
}

const list = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const status = ref(null)
const ratedOnly = ref(false)
const progressVisible = ref(false)
const progressId = ref(null)

function listParams(extra = {}) {
  const params = {
    page: page.value,
    size: size.value,
    status: status.value || undefined,
    ...extra,
  }
  if (allowRating.value && ratedOnly.value) params.rated = true
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
  await ElMessageBox.confirm(`确认标记「${row.title}」为已完成？`, '完成')
  await http.post(`/api/tickets/${row.id}/complete`)
  ElMessage.success('已完成')
  load()
}

function openProgress(row) {
  progressId.value = row.id
  progressVisible.value = true
}

async function doPickup(row) {
  const { value } = await ElMessageBox.prompt('领取地点（可留空用系统默认）', '领取登记', {
    confirmButtonText: '登记',
    cancelButtonText: '取消',
    inputPlaceholder: '如 行政楼一楼服务台',
    inputValue: row.pickupPlace || '',
  }).catch(() => ({ value: null }))
  if (value === null) return
  const body = { pickupPlace: String(value || '').trim() }
  if (allowQty.value) {
    const { value: qty } = await ElMessageBox.prompt('实发数量', '领取登记', {
      confirmButtonText: '确定',
      inputValue: String(row.qty || 1),
      inputPattern: /^[1-9]\d*$/,
      inputErrorMessage: '请输入正整数',
    }).catch(() => ({ value: null }))
    if (qty === null) return
    body.actualQty = Number(qty)
  }
  await http.post(`/api/tickets/${row.id}/pickup`, body)
  ElMessage.success('已登记领取')
  load()
}

async function doFinePaid(row) {
  await ElMessageBox.confirm(`确认「${row.title || row.id}」${finePaidLabel.value}？`, finePaidLabel.value)
  await http.post(`/api/tickets/${row.id}/fine-paid`)
  ElMessage.success(`已标记${finePaidLabel.value}`)
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
  const headers = ['编号', '标题', '类型', '地点', userLabel.value, '处理人', '状态']
  if (allowQty.value) headers.push('数量')
  if (pickLoanPeriod.value) headers.push(dueLabel.value)
  if (showFine.value) headers.push(fineLabel.value)
  if (showPickup.value) headers.push('领取地点', '领取时间')
  headers.push('开始', '结束', '说明', '附件')
  headers.push('申请时间', '受理时间')
  if (allowCheckin.value) headers.push('签到时间')
  headers.push('完成时间')
  if (allowRating.value) headers.push('评分', '短评', '评价时间')

  const data = rows.map((row) => {
    const line = [
      row.id,
      row.title,
      row.typeName,
      row.location,
      row.username,
      row.assigneeUsername || '',
      states.value[row.status] || row.status,
    ]
    if (allowQty.value) line.push(row.qty ?? 1)
    if (pickLoanPeriod.value) line.push(row.dueAt || '')
    if (showFine.value) {
      line.push(Number(row.fineYuan) > 0 ? `¥${row.fineYuan} · ${row.fineStatus || ''}` : '')
    }
    if (showPickup.value) {
      line.push(row.pickupPlace || '', row.pickupAt || '')
    }
    line.push(row.startAt, row.endAt, remarkText(row.remark), row.attachUrl || '')
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
  load()
})
</script>

<style scoped>
.toolbar { margin-bottom: 12px; display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.pager { margin-top: 16px; display: flex; justify-content: flex-end; }
.rating { color: #b45309; font-weight: 600; }
.muted { color: #94a3b8; }
</style>
