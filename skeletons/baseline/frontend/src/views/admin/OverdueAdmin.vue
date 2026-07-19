<template>
  <div>
    <div class="toolbar">
      <el-alert
        type="warning"
        :closable="false"
        show-icon
        :title="`逾期按 ${finePerDay} 元/天登记预估罚款；可催还或办理归还。`"
      />
    </div>
    <div class="toolbar">
      <el-button type="primary" @click="load">刷新逾期</el-button>
    </div>
    <el-table :data="list" stripe>
      <el-table-column prop="id" label="单号" width="70" />
      <el-table-column prop="title" :label="archiveLabel" min-width="160" />
      <el-table-column prop="username" label="借用人" width="110" />
      <el-table-column prop="dueAt" label="应还" width="170" />
      <el-table-column prop="fineYuan" label="预估罚款" width="110">
        <template #default="{ row }">{{ row.fineYuan > 0 ? row.fineYuan + ' 元' : '—' }}</template>
      </el-table-column>
      <el-table-column prop="remindedAt" label="最近催还" width="170" />
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button link type="warning" @click="remind(row)">{{ verbs.remind || '催还' }}</el-button>
          <el-button link type="primary" @click="ret(row)">{{ verbs.return || '归还' }}</el-button>
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
import { archiveCopy, ticketCopy } from '../../utils/domainSchema.js'

const archive = archiveCopy()
const ticket = ticketCopy()
const verbs = computed(() => ticket.verbs || {})
const archiveLabel = computed(() => archive.label || '对象')

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
  ElMessage.success('已催还')
  load()
}

async function ret(row) {
  await ElMessageBox.confirm(
    `确认${verbs.value.return || '归还'}？登记罚款 ${row.fineYuan || 0} 元。`,
    verbs.value.return || '归还',
  )
  await http.post(`/api/tickets/${row.id}/return`)
  ElMessage.success('已归还')
  load()
}

onMounted(load)
</script>

<style scoped>
.toolbar { margin-bottom: 12px; }
.pager { margin-top: 16px; display: flex; justify-content: flex-end; }
</style>
