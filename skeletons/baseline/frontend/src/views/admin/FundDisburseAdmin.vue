<template>
  <div>
    <div class="toolbar">
      <h2>{{ title }}</h2>
      <el-button @click="reload">刷新</el-button>
    </div>
    <p class="lead">{{ lead }}</p>

    <el-table :data="list" stripe empty-text="还没有发放记录">
      <el-table-column prop="id" label="单号" width="80" />
      <el-table-column prop="ticketId" label="申请单" width="100" />
      <el-table-column prop="username" label="申请人" width="130" />
      <el-table-column prop="amount" label="发放金额(元)" width="130" />
      <el-table-column prop="paidAt" label="发放日期" width="130" />
      <el-table-column prop="operator" label="经办人" width="120" />
      <el-table-column prop="remark" label="备注" min-width="160" />
      <el-table-column label="操作" width="90">
        <template #default="{ row }">
          <el-button link type="danger" @click="removeRow(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <h3>登记发放</h3>
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
      <el-form-item label="发放金额" required>
        <el-input-number v-model="form.amount" :min="0" :precision="2" :step="100" />
      </el-form-item>
      <el-form-item label="发放日期">
        <el-date-picker v-model="form.paidAt" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="form.remark" placeholder="如：一次性发放 / 分两次发放第一笔" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="saving" @click="save">登记发放</el-button>
        <el-button @click="loadTotal">查看该单已发合计</el-button>
        <span v-if="total !== null" class="total">合计 {{ total }} 元</span>
      </el-form-item>
    </el-form>
    <p class="hint">台账只记发放事实，不做额度扣减；申请单须先审核通过。</p>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'
import { getSchema } from '../../utils/domainSchema.js'

const labels = getSchema()?.labels || {}
const title = labels.fundDisburseTitle || '发放登记'
const lead = labels.fundDisburseLead || '按已通过的申请登记发放金额与日期；台账只记事实。'

const list = ref([])
const tickets = ref([])
const saving = ref(false)
const total = ref(null)
const form = reactive({ ticketId: null, amount: 0, paidAt: '', remark: '' })

function unwrap(res) {
  return res.data?.data ?? res.data
}

async function load() {
  const res = await http.get('/api/fund-disburse/admin')
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
  total.value = null
  await Promise.all([load(), loadTickets()])
}

async function save() {
  if (!form.ticketId) {
    ElMessage.warning('请选择申请单')
    return
  }
  saving.value = true
  try {
    await http.post('/api/fund-disburse/admin', {
      ticketId: form.ticketId,
      amount: form.amount,
      paidAt: form.paidAt || '',
      remark: form.remark || '',
    })
    ElMessage.success('已登记发放')
    form.remark = ''
    await load()
    await loadTotal()
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '登记失败')
  } finally {
    saving.value = false
  }
}

async function loadTotal() {
  if (!form.ticketId) {
    ElMessage.warning('请先选择申请单')
    return
  }
  try {
    const res = await http.get('/api/fund-disburse/admin/total', { params: { ticketId: form.ticketId } })
    total.value = unwrap(res)
  } catch (e) {
    total.value = null
    ElMessage.error(e?.response?.data?.message || e.message || '读取合计失败')
  }
}

async function removeRow(row) {
  try {
    await ElMessageBox.confirm('删除后不可恢复，确认删除这条发放记录？', '提示', { type: 'warning' })
  } catch (e) {
    return
  }
  try {
    await http.delete(`/api/fund-disburse/admin/${row.id}`)
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
.total { margin-left: 12px; color: #0f766e; font-weight: 600; }
h3 { margin: 1.25rem 0 0.5rem; font-size: 1rem; }
</style>
