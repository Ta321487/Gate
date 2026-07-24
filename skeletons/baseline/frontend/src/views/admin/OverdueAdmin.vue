<template>
  <div>
    <div class="toolbar">
      <el-alert
        type="warning"
        :closable="false"
        show-icon
        :title="`逾期按 ${finePerDay} 元/天登记预估${fineLabel}；可${remindVerb}或办理${returnVerb}。`"
      />
    </div>
    <div class="toolbar">
      <el-button type="primary" @click="load">刷新逾期</el-button>
    </div>
    <el-table :data="list" stripe>
      <el-table-column prop="id" label="编号" width="70" />
      <el-table-column prop="title" :label="archiveLabel" min-width="160" />
      <el-table-column :label="userLabel" width="110">
        <template #default="{ row }">{{ personLabel(row) }}</template>
      </el-table-column>
      <el-table-column prop="dueAt" :label="dueLabel" width="170" />
      <el-table-column prop="fineYuan" :label="`预估${fineLabel}`" width="110">
        <template #default="{ row }">{{ row.fineYuan > 0 ? row.fineYuan + ' 元' : '—' }}</template>
      </el-table-column>
      <el-table-column prop="remindedAt" :label="`最近${remindVerb}`" width="170" />
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button link type="warning" @click="remind(row)">{{ remindVerb }}</el-button>
          <el-button link type="primary" @click="ret(row)">{{ returnVerb }}</el-button>
        </template>
      </el-table-column>
      <template #empty>当前无逾期记录</template>
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
import {
  archiveCopy,
  getSchema,
  personLabel,
  roleLabel,
  ticketDueLabel,
  ticketFineLabel,
  ticketRemindVerb,
  ticketReturnVerb,
} from '../../utils/domainSchema.js'

const archive = archiveCopy()
const archiveLabel = computed(() => archive.label || '对象')
const userLabel = computed(() => roleLabel('user', '用户'))
const dueLabel = computed(() => ticketDueLabel())
const fineLabel = computed(() => ticketFineLabel())
const remindVerb = computed(() => ticketRemindVerb())
const returnVerb = computed(() => ticketReturnVerb())

const list = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const finePerDay = ref(0.5)

async function load() {
  const res = await http.get('/api/tickets', {
    params: { page: page.value, size: size.value, status: 'overdue' },
  })
  list.value = res.data.list
  total.value = res.data.total
  if (list.value[0]?.finePerDay != null) finePerDay.value = list.value[0].finePerDay
}

async function remind(row) {
  await http.post(`/api/tickets/${row.id}/remind`)
  ElMessage.success(`已${remindVerb.value}`)
  load()
}

async function ret(row) {
  await ElMessageBox.confirm(
    `确认${returnVerb.value}？登记${fineLabel.value} ${row.fineYuan || 0} 元。`,
    returnVerb.value,
  )
  await http.post(`/api/tickets/${row.id}/return`)
  ElMessage.success(`已${returnVerb.value}`)
  load()
}

onMounted(load)
</script>

<style scoped>
.toolbar { margin-bottom: 12px; }
.pager { margin-top: 16px; display: flex; justify-content: flex-end; }
</style>
