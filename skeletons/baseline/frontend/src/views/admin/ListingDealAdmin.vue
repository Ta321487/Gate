<template>
  <div>
    <div class="toolbar">
      <h2>{{ title }}</h2>
      <el-button @click="reload">刷新</el-button>
    </div>
    <p class="lead">{{ lead }}</p>

    <el-table :data="list" stripe empty-text="还没有成交记录">
      <el-table-column prop="id" label="单号" width="80" />
      <el-table-column prop="ticketId" label="跟进单" width="100" />
      <el-table-column prop="username" label="看房客户" width="130" />
      <el-table-column prop="dealPrice" label="成交价(元)" width="130" />
      <el-table-column prop="dealAt" label="成交日期" width="130" />
      <el-table-column prop="operator" label="经办人" width="120" />
      <el-table-column prop="remark" label="备注" min-width="160" />
      <el-table-column label="操作" width="90">
        <template #default="{ row }">
          <el-button link type="danger" @click="removeRow(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <h3>登记成交</h3>
    <el-form label-width="90px" class="form">
      <el-form-item label="跟进单" required>
        <el-select
          v-model="form.ticketId"
          filterable
          allow-create
          default-first-option
          placeholder="选已办结的带看跟进（或直接填单号）"
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
      <el-form-item label="成交价" required>
        <el-input-number v-model="form.dealPrice" :min="0" :precision="2" :step="1000" />
      </el-form-item>
      <el-form-item label="成交日期">
        <el-date-picker v-model="form.dealAt" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="form.remark" placeholder="如：全款成交 / 分期首付" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="saving" @click="save">登记成交</el-button>
        <el-button @click="loadTotal">查看成交总额</el-button>
        <span v-if="total !== null" class="total">合计 {{ total }} 元</span>
      </el-form-item>
    </el-form>
    <p class="hint">只有已办结的带看跟进可登记成交；台账只记成交事实，房源档案状态另在档案里维护。</p>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'
import { getSchema } from '../../utils/domainSchema.js'

const labels = getSchema()?.labels || {}
const title = labels.listingDealTitle || '成交登记'
const lead = labels.listingDealLead || '带看跟进办结后登记成交价与成交日；台账只记成交事实。'

const list = ref([])
const tickets = ref([])
const saving = ref(false)
const total = ref(null)
const form = reactive({ ticketId: null, dealPrice: 0, dealAt: '', remark: '' })

function unwrap(res) {
  return res.data?.data ?? res.data
}

async function load() {
  const res = await http.get('/api/listing-deal/admin')
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
    ElMessage.warning('请选择带看跟进单')
    return
  }
  saving.value = true
  try {
    await http.post('/api/listing-deal/admin', {
      ticketId: form.ticketId,
      dealPrice: form.dealPrice,
      dealAt: form.dealAt || '',
      remark: form.remark || '',
    })
    ElMessage.success('已登记成交')
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
  try {
    const res = await http.get('/api/listing-deal/admin/total')
    total.value = unwrap(res)
  } catch (e) {
    total.value = null
    ElMessage.error(e?.response?.data?.message || e.message || '读取总额失败')
  }
}

async function removeRow(row) {
  try {
    await ElMessageBox.confirm('删除后不可恢复，确认删除这条成交记录？', '提示', { type: 'warning' })
  } catch (e) {
    return
  }
  try {
    await http.delete(`/api/listing-deal/admin/${row.id}`)
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
