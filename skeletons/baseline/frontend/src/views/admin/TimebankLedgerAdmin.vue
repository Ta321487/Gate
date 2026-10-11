<template>
  <div>
    <h2>时长流水</h2>
    <p v-if="exportHint" class="hint">{{ exportHint }}</p>
    <el-form inline class="filter" @submit.prevent>
      <el-form-item label="用户">
        <el-input v-model="username" clearable placeholder="可选筛选" style="width: 160px" />
      </el-form-item>
      <el-button type="primary" @click="() => { page = 1; load() }">查询</el-button>
      <el-button v-if="exportOn" @click="exportCsv">{{ exportLabel }}</el-button>
    </el-form>
    <el-table :data="list" stripe>
      <el-table-column prop="createdAt" label="时间" width="180" />
      <el-table-column prop="username" label="用户" width="120" />
      <el-table-column prop="deltaHours" label="变动" width="100" />
      <el-table-column prop="reason" label="说明" />
      <el-table-column prop="refType" label="类型" width="100" />
      <el-table-column prop="refId" label="关联ID" width="90" />
    </el-table>
    <el-pagination
      v-if="total > size"
      class="pager"
      layout="prev, pager, next"
      :total="total"
      :page-size="size"
      v-model:current-page="page"
      @current-change="load"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/http'
import { getSchema } from '../../utils/domainSchema'

const labels = computed(() => getSchema()?.labels || {})
const exportOn = computed(() => !!getSchema()?.interactThicken?.timebankLedgerExport)
const exportLabel = computed(() => labels.value.tbLedgerExportLabel || '导出流水')
const exportHint = computed(() => labels.value.tbLedgerExportHint || '')
const list = ref([])
const total = ref(0)
const page = ref(1)
const size = 20
const username = ref('')

async function load() {
  const res = await http.get('/api/timebank/admin/ledger', {
    params: { page: page.value, size, username: username.value || undefined },
  })
  const data = res.data?.data || res.data || {}
  list.value = data.list || []
  total.value = data.total || 0
}

async function exportCsv() {
  try {
    const res = await http.get('/api/timebank/admin/ledger/export', {
      params: { username: username.value || undefined },
      responseType: 'blob',
    })
    const blob = new Blob([res.data], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'tb_ledger.csv'
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('已导出')
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '导出失败')
  }
}

watch(page, load)
onMounted(load)
</script>

<style scoped>
.filter { margin: 1rem 0; }
.pager { margin-top: 1rem; }
.hint { color: var(--el-text-color-secondary); font-size: 13px; }
</style>
