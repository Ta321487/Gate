<template>
  <div>
    <header class="hd">
      <div>
        <h2>{{ pageTitle }}</h2>
        <p class="lead">{{ pageLead }}</p>
      </div>
      <el-button type="primary" plain @click="loadMissing">{{ missingTitle }}</el-button>
    </header>

    <el-form :inline="true" class="filters" @submit.prevent>
      <el-form-item label="类型">
        <el-select v-model="logType" clearable placeholder="全部" style="width:140px" @change="reload">
          <el-option v-for="t in typeOptions" :key="t.value" :label="t.label" :value="t.value" />
        </el-select>
      </el-form-item>
      <el-form-item label="日期">
        <el-date-picker
          v-model="logDate"
          type="date"
          value-format="YYYY-MM-DD"
          clearable
          placeholder="全部"
          @change="reload"
        />
      </el-form-item>
      <el-form-item>
        <el-checkbox v-model="abnormalOnly" @change="reload">仅异常</el-checkbox>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="reload">查询</el-button>
      </el-form-item>
    </el-form>

    <el-table :data="list" stripe>
      <el-table-column prop="itemTitle" label="对象" min-width="140" show-overflow-tooltip>
        <template #default="{ row }">{{ row.itemTitle || ('#' + row.itemId) }}</template>
      </el-table-column>
      <el-table-column prop="logDate" label="日期" width="120" />
      <el-table-column prop="logType" label="类型" width="100">
        <template #default="{ row }">{{ typeLabel(row.logType) }}</template>
      </el-table-column>
      <el-table-column label="指标" min-width="200" show-overflow-tooltip>
        <template #default="{ row }">{{ payloadSummary(row) }}</template>
      </el-table-column>
      <el-table-column prop="abnormal" label="异常" width="80">
        <template #default="{ row }">
          <el-tag :type="row.abnormal ? 'danger' : 'info'" size="small" effect="plain">
            {{ row.abnormal ? '是' : '否' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="username" label="记录人" width="110" />
      <el-table-column prop="createdAt" label="时间" width="170" />
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

    <el-dialog v-model="missingVisible" :title="missingTitle" width="560px">
      <p class="tip">共 {{ missingList.length }} 条（默认 checkin）</p>
      <el-table :data="missingList" max-height="360" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="title" label="对象" min-width="200" show-overflow-tooltip />
      </el-table>
      <template #footer>
        <el-button @click="missingVisible = false">关闭</el-button>
        <el-button type="primary" @click="$router.push('/admin/archive')">去档案</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import http from '../../api/http'
import { getSchema } from '../../utils/domainSchema.js'

const labels = computed(() => getSchema()?.labels || {})
const logEnt = computed(() => getSchema()?.entities?.archiveLog || {})
const pageTitle = computed(() => labels.value.archiveLogPageTitle || logEnt.value.labelPlural || '监测记录')
const pageLead = computed(
  () => labels.value.archiveLogPageLead || '按对象查看打卡与随访；可筛选今日未打卡。',
)
const missingTitle = computed(() => labels.value.archiveLogMissingTitle || '今日未打卡')
const typeOptions = computed(() => logEnt.value.typeOptions || [
  { value: 'checkin', label: '健康打卡' },
  { value: 'followup', label: '随访记录' },
  { value: 'assess', label: '评估记录' },
])
const fields = computed(() => logEnt.value.fields || [])

const list = ref([])
const page = ref(1)
const size = ref(20)
const total = ref(0)
const logType = ref('')
const logDate = ref('')
const abnormalOnly = ref(false)
const missingVisible = ref(false)
const missingList = ref([])

function typeLabel(v) {
  const hit = typeOptions.value.find((t) => t.value === v)
  return hit?.label || v || '—'
}

function payloadSummary(row) {
  const p = row.payload || {}
  const parts = []
  for (const f of fields.value) {
    const val = p[f.key]
    if (val != null && String(val).trim() !== '') parts.push(`${f.label || f.key}:${val}`)
  }
  if (!parts.length && row.remark) return row.remark
  return parts.join(' · ') || '—'
}

async function load() {
  const params = { page: page.value, size: size.value }
  if (logType.value) params.logType = logType.value
  if (logDate.value) params.logDate = logDate.value
  if (abnormalOnly.value) params.abnormalOnly = true
  const res = await http.get('/api/admin/archive-logs', { params })
  list.value = res.data?.list || []
  total.value = res.data?.total || 0
}

function reload() {
  page.value = 1
  load()
}

async function loadMissing() {
  const res = await http.get('/api/admin/archive-logs/missing-today', {
    params: { logType: logType.value || 'checkin' },
  })
  missingList.value = res.data?.list || []
  missingVisible.value = true
}

onMounted(load)
</script>

<style scoped>
.hd {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
}
.hd h2 { margin: 0 0 4px; font-size: 18px; }
.lead { margin: 0; color: var(--el-text-color-secondary); font-size: 13px; }
.filters { margin-bottom: 8px; }
.pager { margin-top: 16px; display: flex; justify-content: flex-end; }
.tip { margin: 0 0 10px; font-size: 13px; color: var(--el-text-color-secondary); }
</style>
