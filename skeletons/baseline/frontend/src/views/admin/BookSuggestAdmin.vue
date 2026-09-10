<template>
  <div>
    <p class="lead">{{ pageLead }}</p>
    <div class="toolbar">
      <el-radio-group v-model="status" size="default" @change="onStatus">
        <el-radio-button value="">全部</el-radio-button>
        <el-radio-button value="pending">待审核</el-radio-button>
        <el-radio-button value="approved">已通过</el-radio-button>
        <el-radio-button value="rejected">已驳回</el-radio-button>
      </el-radio-group>
      <el-input
        v-model="keyword"
        clearable
        placeholder="读者用户名"
        style="width: 160px"
        @keyup.enter="reload"
      />
      <el-button type="primary" @click="reload">查询</el-button>
    </div>
    <div class="table-scroll">
      <el-table :data="list" stripe>
        <el-table-column prop="id" label="编号" width="80" />
        <el-table-column prop="username" label="读者" width="110" />
        <el-table-column prop="title" label="书名" min-width="160" show-overflow-tooltip />
        <el-table-column prop="isbn" label="ISBN" width="120" show-overflow-tooltip />
        <el-table-column prop="author" label="作者" width="110" show-overflow-tooltip />
        <el-table-column prop="reason" label="理由" min-width="140" show-overflow-tooltip />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">{{ statusLabel(row.status) }}</template>
        </el-table-column>
        <el-table-column prop="createdAt" label="提交时间" width="170" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <div v-if="row.status === 'pending'" class="table-ops">
              <el-button link type="success" @click="resolve(row, 'approve')">通过</el-button>
              <el-button link type="danger" @click="resolve(row, 'reject')">驳回</el-button>
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
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'
import { getSchema } from '../../utils/domainSchema.js'

const labels = computed(() => getSchema()?.labels || {})
const pageLead = computed(
  () => labels.value.bookSuggestAdminLead || '审核读者荐购申请：通过记台账，驳回须填写说明。',
)

const list = ref([])
const page = ref(1)
const size = ref(20)
const total = ref(0)
const status = ref('pending')
const keyword = ref('')

function statusLabel(s) {
  if (s === 'pending') return '待审核'
  if (s === 'approved') return '已通过'
  if (s === 'rejected') return '已驳回'
  return s || '—'
}

function onStatus() {
  page.value = 1
  load()
}

function reload() {
  page.value = 1
  load()
}

async function load() {
  const params = { page: page.value, size: size.value }
  if (status.value) params.status = status.value
  if (keyword.value.trim()) params.username = keyword.value.trim()
  const res = await http.get('/api/admin/book-suggest', { params })
  list.value = res.data?.list || []
  total.value = res.data?.total || 0
}

async function resolve(row, action) {
  let note = ''
  if (action === 'reject') {
    const { value } = await ElMessageBox.prompt('请填写驳回说明', '驳回荐购', {
      inputPattern: /.{1,}/,
      inputErrorMessage: '请填写说明',
    })
    note = value
  } else {
    await ElMessageBox.confirm('确认通过该荐购并记入台账？', '通过荐购', { type: 'success' })
  }
  await http.post(`/api/admin/book-suggest/${row.id}/resolve`, { action, note })
  ElMessage.success(action === 'approve' ? '已通过' : '已驳回')
  await load()
}

onMounted(load)
</script>

<style scoped>
.lead { margin: 0 0 10px; color: var(--portal-muted, #606266); font-size: 13px; }
.toolbar { margin-bottom: 12px; display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.pager { margin-top: 12px; display: flex; justify-content: flex-end; }
.table-ops { display: flex; gap: 4px; flex-wrap: wrap; }
.muted { color: var(--portal-muted, #94a3b8); font-size: 13px; }
</style>
