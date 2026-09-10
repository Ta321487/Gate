<template>
  <div>
    <p class="lead">{{ pageLead }}</p>
    <div class="toolbar">
      <el-input
        v-model="keyword"
        clearable
        placeholder="操作者 / 对象 / 说明"
        style="width: 220px"
        @keyup.enter="onSearch"
      />
      <el-select v-model="action" clearable placeholder="动作" style="width: 160px" @change="onSearch">
        <el-option label="全部" value="" />
        <el-option label="登录" value="login" />
        <el-option label="审单通过" value="ticket_approve" />
        <el-option label="审单驳回" value="ticket_reject" />
        <el-option label="改档案" value="archive_update" />
        <el-option label="删档案" value="archive_delete" />
        <el-option label="改用户" value="user_update" />
        <el-option label="重置密码" value="user_reset_password" />
        <el-option label="任命岗位" value="user_appoint" />
        <el-option label="撤销岗位" value="user_revoke" />
      </el-select>
      <el-button type="primary" @click="onSearch">查询</el-button>
    </div>
    <div class="table-scroll">
      <el-table :data="list" stripe>
        <el-table-column prop="id" label="编号" width="80" />
        <el-table-column prop="createdAt" label="时间" width="170" />
        <el-table-column prop="username" label="操作者" width="120" />
        <el-table-column label="动作" width="120">
          <template #default="{ row }">{{ actionLabel(row.action) }}</template>
        </el-table-column>
        <el-table-column label="对象" width="160">
          <template #default="{ row }">{{ targetLabel(row) }}</template>
        </el-table-column>
        <el-table-column prop="detail" label="说明" min-width="200" show-overflow-tooltip />
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
/** 操作审计日志：总管只读查询（E-04） */
import { computed, onMounted, ref } from 'vue'
import http from '../../api/http'
import { getSchema } from '../../utils/domainSchema.js'

const labels = computed(() => getSchema()?.labels || {})
const pageLead = computed(
  () => labels.value.auditLogsPageLead || '查看管理端关键写操作与登录记录（时间、操作者、动作、对象）。',
)

const list = ref([])
const page = ref(1)
const size = ref(20)
const total = ref(0)
const keyword = ref('')
const action = ref('')

const ACTION_LABELS = {
  login: '登录',
  ticket_approve: '审单通过',
  ticket_reject: '审单驳回',
  archive_update: '改档案',
  archive_delete: '删档案',
  user_update: '改用户',
  user_reset_password: '重置密码',
  user_appoint: '任命岗位',
  user_revoke: '撤销岗位',
}

function actionLabel(a) {
  return ACTION_LABELS[a] || a || '—'
}

function targetLabel(row) {
  const t = row.targetType || ''
  const id = row.targetId || ''
  if (!t && !id) return '—'
  const typeMap = { ticket: '单据', archive: '档案', user: '用户', session: '会话' }
  const type = typeMap[t] || t || '对象'
  return id ? `${type} #${id}` : type
}

function onSearch() {
  page.value = 1
  load()
}

async function load() {
  const params = { page: page.value, size: size.value }
  if (keyword.value.trim()) params.keyword = keyword.value.trim()
  if (action.value) params.action = action.value
  const res = await http.get('/api/admin/audit-logs', { params })
  list.value = res.data?.list || []
  total.value = res.data?.total || 0
}

onMounted(load)
</script>

<style scoped>
.lead { margin: 0 0 10px; color: var(--portal-muted, #606266); font-size: 13px; }
.toolbar { margin-bottom: 12px; display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.pager { margin-top: 12px; display: flex; justify-content: flex-end; }
</style>
