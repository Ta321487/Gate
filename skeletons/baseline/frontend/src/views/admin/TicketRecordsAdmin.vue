<template>
  <div>
    <div class="toolbar">
      <el-select v-model="status" clearable placeholder="全部状态" style="width:140px" @change="load">
        <el-option v-for="(lab, key) in states" :key="key" :label="lab" :value="key" />
      </el-select>
      <el-button type="primary" @click="load">查询</el-button>
      <el-button :disabled="!list.length" @click="exportCsv">导出 CSV</el-button>
    </div>
    <el-table :data="list" stripe>
      <el-table-column prop="id" label="单号" width="70" />
      <el-table-column prop="title" label="标题" min-width="140" />
      <el-table-column prop="typeName" label="类型" width="100" />
      <el-table-column prop="location" label="地点" width="140" />
      <el-table-column prop="username" label="申请人" width="110" />
      <el-table-column prop="assigneeUsername" label="处理人" width="110">
        <template #default="{ row }">{{ row.assigneeUsername || '—' }}</template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">{{ states[row.status] || row.status }}</template>
      </el-table-column>
      <el-table-column v-if="allowQty" prop="qty" label="数量" width="70" />
      <el-table-column v-if="pickLoanPeriod" prop="dueAt" label="应还" width="170" />
      <el-table-column prop="startAt" label="开始" width="160" />
      <el-table-column prop="endAt" label="结束" width="160" />
      <el-table-column prop="remark" :label="richRemark ? '内容/说明' : '审核说明'" min-width="160" show-overflow-tooltip>
        <template #default="{ row }">{{ remarkText(row.remark) }}</template>
      </el-table-column>
      <el-table-column prop="applyAt" label="申请时间" width="170" />
      <el-table-column prop="approveAt" label="受理时间" width="170" />
      <el-table-column prop="returnAt" label="完成时间" width="170" />
      <el-table-column v-if="allowRating" label="评分" width="90">
        <template #default="{ row }">{{ row.rating ? `${row.rating} 分` : '—' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
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
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'
import { ticketCopy } from '../../utils/domainSchema.js'
import { plainFromHtml } from '../../utils/richHtml.js'
import { downloadCsv } from '../../utils/csvDownload.js'

const ticket = ticketCopy()
const verbs = computed(() => ticket.verbs || {})
const states = computed(() => ticket.states || {})
const richRemark = computed(() => !!ticket.richRemark)
const allowRating = computed(() => !!ticket.allowRating)
const allowQty = computed(() => !!ticket.allowQty)
const pickLoanPeriod = computed(() => !!ticket.pickLoanPeriod)

function remarkText(v) {
  if (!v) return '—'
  return plainFromHtml(String(v)) || '—'
}

const list = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const status = ref(null)

async function load() {
  const res = await http.get('/api/tickets', {
    params: { page: page.value, size: size.value, status: status.value || undefined },
  })
  list.value = res.data.list
  total.value = res.data.total
}

async function finish(row) {
  await ElMessageBox.confirm(`确认标记「${row.title}」为已完成？`, '完成')
  await http.post(`/api/tickets/${row.id}/complete`)
  ElMessage.success('已完成')
  load()
}

async function exportCsv() {
  const res = await http.get('/api/tickets', {
    params: { page: 1, size: 5000, status: status.value || undefined },
  })
  const rows = res.data?.list || []
  if (!rows.length) {
    ElMessage.warning('当前筛选无数据可导出')
    return
  }
  const headers = [
    '单号', '标题', '类型', '地点', '申请人', '处理人', '状态',
    '数量', '应还', '开始', '结束', '说明', '申请时间', '受理时间', '完成时间',
  ]
  if (allowRating.value) headers.push('评分', '短评')
  const data = rows.map((row) => {
    const line = [
      row.id,
      row.title,
      row.typeName,
      row.location,
      row.username,
      row.assigneeUsername,
      states.value[row.status] || row.status,
      row.qty ?? 1,
      row.dueAt,
      row.startAt,
      row.endAt,
      remarkText(row.remark),
      row.applyAt,
      row.approveAt,
      row.returnAt,
    ]
    if (allowRating.value) {
      line.push(row.rating || '', row.ratingRemark || '')
    }
    return line
  })
  downloadCsv(`tickets_${status.value || 'all'}_${Date.now()}.csv`, headers, data)
  ElMessage.success(`已导出 ${rows.length} 条（UTF-8，可用 Excel 直接打开）`)
}

onMounted(load)
</script>

<style scoped>
.toolbar { margin-bottom: 12px; display: flex; gap: 8px; }
.pager { margin-top: 16px; display: flex; justify-content: flex-end; }
</style>
