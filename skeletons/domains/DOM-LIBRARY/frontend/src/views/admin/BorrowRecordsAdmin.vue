<template>
  <div>
    <div class="toolbar">
      <el-select v-model="status" clearable placeholder="全部状态" style="width:140px" @change="onFilter">
        <el-option label="待审核" value="pending" />
        <el-option label="已借出" value="approved" />
        <el-option label="已驳回" value="rejected" />
        <el-option label="已归还" value="returned" />
        <el-option label="逾期" value="overdue" />
      </el-select>
      <el-button @click="load">刷新</el-button>
    </div>
    <el-table :data="list" stripe>
      <el-table-column prop="id" label="单号" width="70" />
      <el-table-column prop="bookTitle" label="书名" min-width="140" />
      <el-table-column prop="username" label="读者" width="100" />
      <el-table-column prop="assigneeUsername" label="处理人" width="100">
        <template #default="{ row }">{{ row.assigneeUsername || '—' }}</template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="90">
        <template #default="{ row }">{{ statusText(row.status) }}</template>
      </el-table-column>
      <el-table-column prop="remark" label="审核说明" min-width="120" show-overflow-tooltip>
        <template #default="{ row }">{{ row.remark || '—' }}</template>
      </el-table-column>
      <el-table-column prop="dueAt" label="应还" width="170" />
      <el-table-column prop="fineYuan" label="罚款" width="80">
        <template #default="{ row }">{{ row.fineYuan > 0 ? row.fineYuan + ' 元' : '—' }}</template>
      </el-table-column>
      <el-table-column prop="applyAt" label="申请时间" width="170" />
      <el-table-column prop="returnAt" label="归还时间" width="170" />
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="row.status === 'approved' || row.status === 'overdue'"
            link
            type="warning"
            @click="remind(row)"
          >催还</el-button>
          <el-button
            v-if="row.status === 'approved' || row.status === 'overdue'"
            link
            type="primary"
            @click="ret(row)"
          >归还</el-button>
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
/** 借阅记录：全量查询与催还/归还 */
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'

const list = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const status = ref(null)
const map = { pending: '待审核', approved: '已借出', rejected: '已驳回', returned: '已归还', overdue: '逾期' }
function statusText(s) { return map[s] || s }

function onFilter() {
  page.value = 1
  load()
}

async function load() {
  const res = await http.get('/api/borrows', {
    params: { page: page.value, size: size.value, status: status.value || undefined },
  })
  list.value = res.data.list
  total.value = res.data.total
}

async function remind(row) {
  await http.post(`/api/borrows/${row.id}/remind`)
  ElMessage.success('已发送催还提醒')
  load()
}

async function ret(row) {
  const tip = row.fineYuan > 0 ? `确认归还？登记罚款 ${row.fineYuan} 元。` : '确认归还？'
  await ElMessageBox.confirm(tip, '归还')
  await http.post(`/api/borrows/${row.id}/return`)
  ElMessage.success('已归还')
  load()
}

onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; gap: 8px; margin-bottom: 12px; }
.pager { margin-top: 16px; display: flex; justify-content: flex-end; }
</style>
