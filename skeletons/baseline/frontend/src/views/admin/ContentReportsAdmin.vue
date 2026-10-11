<template>
  <div>
    <p class="lead">{{ pageLead }}</p>
    <div class="toolbar">
      <el-radio-group v-model="status" size="default" @change="onStatus">
        <el-radio-button value="">全部</el-radio-button>
        <el-radio-button value="pending">待处理</el-radio-button>
        <el-radio-button value="ignored">已忽略</el-radio-button>
        <el-radio-button value="takedown">已下架</el-radio-button>
      </el-radio-group>
    </div>
    <div class="table-scroll">
      <el-table :data="list" stripe>
        <el-table-column prop="id" label="编号" width="80" />
        <el-table-column prop="username" label="举报人" width="120" />
        <el-table-column label="对象" width="140">
          <template #default="{ row }">{{ targetLabel(row) }}</template>
        </el-table-column>
        <el-table-column prop="reason" label="理由" min-width="200" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">{{ statusLabel(row.status) }}</template>
        </el-table-column>
        <el-table-column prop="createdAt" label="提交时间" width="170" />
        <el-table-column v-if="reportDeadlineOn" :label="reportDeadlineLabel" width="120">
          <template #default="{ row }">
            <span :class="{ warn: isOverdue(row) }">{{ deadlineText(row) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <div v-if="row.status === 'pending'" class="table-ops">
              <el-button link type="primary" @click="resolve(row, 'ignore')">忽略</el-button>
              <el-button link type="danger" @click="resolve(row, 'takedown')">下架</el-button>
              <el-button
                v-if="muteOn"
                link
                type="warning"
                @click="resolve(row, 'takedown_mute')"
              >下架并禁言</el-button>
            </div>
            <span v-else class="muted">{{ row.handler || '—' }}</span>
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
  </div>
</template>

<script setup>
/** 举报管理：用户举报 → 忽略或下架（E-03） */
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'
import { getSchema, hasCap } from '../../utils/domainSchema.js'

const labels = computed(() => getSchema()?.labels || {})
const pageLead = computed(() => {
  const base = labels.value.contentReportsPageLead || '查看用户举报并处理（忽略或下架相关内容）。'
  const th = getSchema()?.interactThicken || {}
  const hint =
    labels.value.datingReportDeadlineHint || labels.value.reportDeadlineHint || ''
  if (
    hint &&
    (th.datingReportDeadline || th.reportDeadlineIsland)
  ) {
    return `${base} ${hint}`
  }
  return base
})
const muteOn = computed(() => hasCap('post_mute'))
const reportHandleDays = computed(() => Math.max(0, Number(getSchema()?.reportHandleDays) || 0))
const reportDeadlineOn = computed(
  () =>
    reportHandleDays.value > 0 &&
    !!(
      getSchema()?.contentThicken?.reportDeadline ||
      getSchema()?.interactThicken?.datingReportDeadline ||
      getSchema()?.interactThicken?.reportDeadlineIsland
    ),
)
const reportDeadlineLabel = computed(() => labels.value.reportDeadlineLabel || '处理时限')
const reportOverdueLabel = computed(() => labels.value.reportOverdueLabel || '已超时')

const list = ref([])
const page = ref(1)
const size = ref(20)
const total = ref(0)
const status = ref('pending')

function statusLabel(s) {
  if (s === 'pending') return '待处理'
  if (s === 'ignored') return '已忽略'
  if (s === 'takedown') return '已下架'
  return s || '—'
}

function targetLabel(row) {
  const t = row.targetType === 'ticket' ? '单据' : '档案'
  return `${t} #${row.targetId}`
}

function parseCreated(row) {
  const raw = String(row?.createdAt || '').replace('T', ' ').trim()
  if (!raw) return null
  const d = new Date(raw.replace(/-/g, '/'))
  return Number.isNaN(d.getTime()) ? null : d
}

function isOverdue(row) {
  if (row.status !== 'pending' || !reportHandleDays.value) return false
  const created = parseCreated(row)
  if (!created) return false
  const due = new Date(created.getTime() + reportHandleDays.value * 86400000)
  return Date.now() > due.getTime()
}

function deadlineText(row) {
  if (row.status !== 'pending') return '—'
  if (isOverdue(row)) return reportOverdueLabel.value
  const created = parseCreated(row)
  if (!created || !reportHandleDays.value) return '—'
  const due = new Date(created.getTime() + reportHandleDays.value * 86400000)
  const left = Math.ceil((due.getTime() - Date.now()) / 86400000)
  return left > 0 ? `${left} 日内` : reportOverdueLabel.value
}

function onStatus() {
  page.value = 1
  load()
}

async function load() {
  const params = { page: page.value, size: size.value }
  if (status.value) params.status = status.value
  const res = await http.get('/api/admin/content-reports', { params })
  list.value = res.data?.list || []
  total.value = res.data?.total || 0
}

async function resolve(row, action) {
  const tip =
    action === 'takedown_mute'
      ? '确认下架该内容并对作者禁言 7 天？'
      : action === 'takedown'
        ? '确认下架该内容？'
        : '确认忽略该举报？'
  await ElMessageBox.confirm(tip, '处理举报', { type: 'warning' })
  const body = { action, note: '' }
  if (action === 'takedown_mute') body.muteDays = 7
  await http.post(`/api/admin/content-reports/${row.id}/resolve`, body)
  ElMessage.success(
    action === 'takedown_mute' ? '已下架并禁言' : action === 'takedown' ? '已下架' : '已忽略',
  )
  await load()
}

onMounted(load)
</script>

<style scoped>
.lead { margin: 0 0 10px; color: var(--portal-muted, #606266); font-size: 13px; }
.toolbar { margin-bottom: 12px; }
.pager { margin-top: 12px; display: flex; justify-content: flex-end; }
.table-ops { display: flex; gap: 4px; flex-wrap: wrap; }
.muted { color: var(--portal-muted, #94a3b8); font-size: 13px; }
.warn { color: #c45656; font-weight: 600; }
</style>
