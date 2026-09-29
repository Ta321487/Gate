<template>
  <div>
    <div class="toolbar">
      <h2>{{ title }}</h2>
      <el-button @click="reload">刷新</el-button>
    </div>
    <p class="lead">{{ lead }}</p>

    <el-table :data="list" stripe empty-text="还没有公示记录">
      <el-table-column prop="id" label="单号" width="80" />
      <el-table-column prop="ticketId" label="申请单" width="100" />
      <el-table-column prop="username" label="申请人" width="130" />
      <el-table-column prop="title" label="公示标题" min-width="180" />
      <el-table-column label="公示期" min-width="190">
        <template #default="{ row }">
          {{ row.startAt || '—' }} ~ {{ row.endAt || '—' }}
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 'closed' ? 'info' : 'success'" size="small">
            {{ statusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="operator" label="经办人" width="120" />
      <el-table-column label="操作" width="150">
        <template #default="{ row }">
          <el-button link type="primary" :disabled="row.status === 'closed'" @click="closeRow(row)">
            结束公示
          </el-button>
          <el-button link type="danger" @click="removeRow(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <h3>登记公示</h3>
    <el-form label-width="90px" class="form">
      <el-form-item label="申请单" required>
        <el-select
          v-model="form.ticketId"
          filterable
          allow-create
          default-first-option
          placeholder="选已通过的申请单（或直接填单号）"
          style="width: 100%"
        >
          <el-option
            v-for="t in tickets"
            :key="t.id"
            :label="`#${t.id} · ${t.username || ''} · ${t.title || ''}`"
            :value="t.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="公示标题" required>
        <el-input v-model="form.title" placeholder="如：2025 年秋季助学金拟资助名单公示" />
      </el-form-item>
      <el-form-item label="公示起止">
        <el-date-picker
          v-model="form.range"
          type="daterange"
          value-format="YYYY-MM-DD"
          range-separator="至"
          start-placeholder="开始"
          end-placeholder="结束"
          style="width: 100%"
        />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="saving" @click="save">登记公示</el-button>
      </el-form-item>
    </el-form>
    <p class="hint">只有审核通过的申请才能登记公示；公示与发放都挂在申请之后，不改申请单状态。</p>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'
import { getSchema } from '../../utils/domainSchema.js'

const labels = getSchema()?.labels || {}
const title = labels.fundPublicityTitle || '公示登记'
const lead = labels.fundPublicityLead || '申请通过后登记公示期；公示结束可标记结束。'

const list = ref([])
const tickets = ref([])
const saving = ref(false)
const form = reactive({ ticketId: null, title: '', range: null })

function unwrap(res) {
  return res.data?.data ?? res.data
}

function statusLabel(status) {
  return status === 'closed' ? '已结束' : '公示中'
}

async function load() {
  const res = await http.get('/api/fund-publicity/admin')
  list.value = unwrap(res) || []
}

async function loadTickets() {
  try {
    const res = await http.get('/api/tickets')
    const data = unwrap(res)
    const rows = Array.isArray(data) ? data : data?.records || data?.list || data?.rows || []
    tickets.value = (rows || []).filter(
      (r) => !['pending', 'pending_mid', 'pending_final', 'rejected'].includes(String(r.status || ''))
    )
  } catch (e) {
    tickets.value = []
  }
}

async function reload() {
  await Promise.all([load(), loadTickets()])
}

async function save() {
  if (!form.ticketId) {
    ElMessage.warning('请选择申请单')
    return
  }
  if (!form.title.trim()) {
    ElMessage.warning('请填写公示标题')
    return
  }
  saving.value = true
  try {
    await http.post('/api/fund-publicity/admin', {
      ticketId: form.ticketId,
      title: form.title.trim(),
      startAt: form.range?.[0] || '',
      endAt: form.range?.[1] || '',
    })
    ElMessage.success('已登记公示')
    form.title = ''
    form.range = null
    await load()
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '登记失败')
  } finally {
    saving.value = false
  }
}

async function closeRow(row) {
  try {
    await http.post(`/api/fund-publicity/admin/${row.id}/close`)
    ElMessage.success('已结束公示')
    load()
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '操作失败')
  }
}

async function removeRow(row) {
  try {
    await ElMessageBox.confirm('删除后不可恢复，确认删除这条公示记录？', '提示', { type: 'warning' })
  } catch (e) {
    return
  }
  try {
    await http.delete(`/api/fund-publicity/admin/${row.id}`)
    ElMessage.success('已删除')
    load()
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '删除失败')
  }
}

onMounted(reload)
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }
.toolbar h2 { margin: 0; }
.lead { color: var(--el-text-color-secondary); margin: 0 0 0.75rem; }
.form { max-width: 520px; margin-top: 0.5rem; }
.hint { color: var(--el-text-color-secondary); font-size: 0.85rem; }
h3 { margin: 1.25rem 0 0.5rem; font-size: 1rem; }
</style>
