<template>
  <div>
    <div class="toolbar">
      <h2>成绩登记</h2>
      <div>
        <el-button @click="reload">刷新</el-button>
        <el-button @click="downloadTemplate">下载导入模板</el-button>
        <input
          ref="csvInput"
          type="file"
          accept=".csv,text/csv"
          style="display: none"
          @change="onImportFile"
        />
        <el-button type="warning" :loading="importing" @click="csvInput && csvInput.click()">
          导入 CSV
        </el-button>
        <el-button :disabled="!list.length" @click="exportCsv">导出 CSV</el-button>
      </div>
    </div>
    <el-form :inline="true" class="filters">
      <el-form-item label="学期">
        <el-select v-model="filter.termId" clearable placeholder="全部" style="width: 160px" @change="reload">
          <el-option v-for="t in terms" :key="t.id" :label="t.name" :value="t.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="课程">
        <el-select v-model="filter.courseId" clearable placeholder="全部" style="width: 180px" @change="reload">
          <el-option v-for="c in courses" :key="c.id" :label="c.title" :value="c.id" />
        </el-select>
      </el-form-item>
    </el-form>
    <el-alert
      v-if="importErrors.length"
      type="warning"
      :closable="true"
      show-icon
      class="import-alert"
      title="部分行未导入（已跳过，其余行已保存）"
    >
      <p v-for="item in importErrors" :key="`${item.line}-${item.reason}`" class="import-line">
        第 {{ item.line }} 行：{{ item.reason }}
      </p>
    </el-alert>
    <el-table :data="list" stripe>
      <el-table-column prop="termName" label="学期" width="140" />
      <el-table-column prop="courseTitle" label="课程" />
      <el-table-column prop="username" label="学生账号" width="140" />
      <el-table-column prop="score" label="分数" width="90" />
      <el-table-column prop="rankNo" label="课内名次" width="100" />
      <el-table-column label="操作" width="150">
        <template #default="{ row }">
          <el-button link type="primary" @click="openHistory(row)">改分记录</el-button>
          <el-button link type="danger" @click="remove(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <p v-if="!list.length" class="empty">当前筛选下没有成绩。</p>

    <section class="stats">
      <h3>分布与及格率</h3>
      <p v-if="stat && stat.total" class="stats-line">
        共 {{ stat.total }} 条 · 及格 {{ stat.passCount }} 条 ·
        <strong>及格率 {{ stat.passRate }}%</strong>
        <span v-if="stat.avgScore != null"> · 平均 {{ stat.avgScore }}</span>
        <span v-if="stat.maxScore != null"> · 最高 {{ stat.maxScore }}</span>
        <span v-if="stat.minScore != null"> · 最低 {{ stat.minScore }}</span>
      </p>
      <p v-else class="empty">当前筛选下暂无成绩，无法统计。</p>
      <div ref="chartEl" class="chart" />
    </section>

    <el-drawer v-model="historyOpen" :title="historyTitle" size="46%">
      <el-table :data="history" stripe>
        <el-table-column label="动作" width="80">
          <template #default="{ row }">{{ actionLabel(row.action) }}</template>
        </el-table-column>
        <el-table-column label="原分数" width="90">
          <template #default="{ row }">{{ row.oldScore == null ? '—' : row.oldScore }}</template>
        </el-table-column>
        <el-table-column label="新分数" width="90">
          <template #default="{ row }">{{ row.newScore == null ? '—' : row.newScore }}</template>
        </el-table-column>
        <el-table-column prop="operator" label="操作人" width="120" />
        <el-table-column prop="createdAt" label="时间" />
      </el-table>
      <p v-if="!history.length" class="empty">这条成绩还没有改分记录。</p>
    </el-drawer>

    <h3>录入或更正</h3>
    <el-form label-width="90px" class="form">
      <el-form-item label="学生账号">
        <el-input v-model="form.username" placeholder="登录账号，如 user" />
      </el-form-item>
      <el-form-item label="学期">
        <el-select v-model="form.termId" style="width: 100%">
          <el-option v-for="t in terms" :key="t.id" :label="t.name" :value="t.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="课程">
        <el-select v-model="form.courseId" style="width: 100%">
          <el-option v-for="c in courses" :key="c.id" :label="c.title" :value="c.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="分数">
        <el-input-number v-model="form.score" :min="0" :max="100" :precision="2" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import http from '../../api/http'
import { downloadCsv, stripBom } from '../../utils/csvDownload.js'

echarts.use([BarChart, GridComponent, TooltipComponent, CanvasRenderer])

const terms = ref([])
const courses = ref([])
const list = ref([])
const saving = ref(false)
const importing = ref(false)
const importErrors = ref([])
const stat = ref(null)
const csvInput = ref(null)
const chartEl = ref(null)
const historyOpen = ref(false)
const history = ref([])
const historyRow = ref(null)
let chart = null
const filter = reactive({ termId: null, courseId: null })
const form = reactive({ username: '', termId: null, courseId: null, score: 60 })

const historyTitle = ref('改分记录')

function unwrap(res) {
  return res.data?.data ?? res.data
}

async function loadMeta() {
  const res = await http.get('/api/grade-scores/meta')
  const data = unwrap(res) || {}
  terms.value = data.terms || []
  courses.value = data.courses || []
  if (!form.termId && terms.value.length) form.termId = terms.value[0].id
  if (!form.courseId && courses.value.length) form.courseId = courses.value[0].id
}

async function load() {
  const res = await http.get('/api/grade-scores/admin', {
    params: {
      termId: filter.termId || undefined,
      courseId: filter.courseId || undefined,
    },
  })
  list.value = unwrap(res) || []
}

async function reload() {
  await Promise.all([load(), loadStats()])
}

async function loadStats() {
  const res = await http.get('/api/grade-scores/admin/stats', {
    params: {
      termId: filter.termId || undefined,
      courseId: filter.courseId || undefined,
    },
  })
  stat.value = unwrap(res) || null
  await nextTick()
  renderChart()
}

function renderChart() {
  if (!chartEl.value || !stat.value) return
  if (!chart) chart = echarts.init(chartEl.value)
  const bands = stat.value.bands || []
  chart.setOption(
    {
      tooltip: { trigger: 'axis' },
      grid: { left: 48, right: 16, top: 24, bottom: 32 },
      xAxis: { type: 'category', data: bands.map((b) => b.label) },
      yAxis: { type: 'value', minInterval: 1, name: '人数' },
      series: [
        {
          type: 'bar',
          name: '人数',
          barMaxWidth: 48,
          data: bands.map((b) => ({
            value: b.count,
            itemStyle: { color: b.pass ? '#409eff' : '#f56c6c' },
          })),
        },
      ],
    },
    true
  )
}

function onResize() {
  chart && chart.resize()
}

async function openHistory(row) {
  historyRow.value = row
  historyTitle.value = `${row.username || '学生'} · ${row.termName || ''}${row.courseTitle || ''} 改分记录`
  historyOpen.value = true
  try {
    const res = await http.get('/api/grade-scores/admin/history', { params: { scoreId: row.id } })
    history.value = unwrap(res) || []
  } catch (e) {
    history.value = []
    ElMessage.error(e?.response?.data?.message || e.message || '读取改分记录失败')
  }
}

function actionLabel(action) {
  return action === 'delete' ? '删除' : '改分'
}

function downloadTemplate() {
  downloadCsv('成绩导入模板.csv', ['学生账号', '课程ID', '学期ID', '分数'], [
    ['user', String(courses.value[0]?.id || 1), String(terms.value[0]?.id || 1), '86'],
    ['peer', String(courses.value[0]?.id || 1), String(terms.value[0]?.id || 1), '92'],
  ])
}

async function onImportFile(e) {
  const file = e?.target?.files?.[0]
  if (!file) return
  importing.value = true
  try {
    const text = stripBom(await file.text())
    const res = await http.post('/api/grade-scores/admin/import', { csv: text })
    const data = unwrap(res) || {}
    const failed = data.failed || []
    importErrors.value = failed
    if (failed.length) {
      ElMessage.warning(`成功 ${data.ok || 0} 行，跳过 ${failed.length} 行`)
    } else {
      ElMessage.success(`已导入 ${data.ok || 0} 行`)
    }
    await reload()
  } catch (err) {
    ElMessage.error(err?.response?.data?.message || err.message || '导入失败')
  } finally {
    importing.value = false
    if (e?.target) e.target.value = ''
  }
}

async function save() {
  saving.value = true
  try {
    await http.post('/api/grade-scores/admin', { ...form })
    ElMessage.success('已保存')
    await load()
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function remove(id) {
  await http.delete(`/api/grade-scores/admin/${id}`)
  ElMessage.success('已删除')
  load()
}

function exportCsv() {
  if (!list.value.length) {
    ElMessage.warning('当前无数据可导出')
    return
  }
  downloadCsv(
    `成绩排名_${Date.now()}.csv`,
    ['学期', '课程', '学生账号', '分数', '课内名次'],
    list.value.map((row) => [row.termName, row.courseTitle, row.username, row.score, row.rankNo])
  )
  ElMessage.success(`已导出 ${list.value.length} 条（UTF-8，可用 Excel 直接打开）`)
}

onMounted(async () => {
  await loadMeta()
  await reload()
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  if (chart) {
    chart.dispose()
    chart = null
  }
})
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem; }
.toolbar h2 { margin: 0; }
.filters { margin-bottom: 0.5rem; }
.form { max-width: 420px; margin-top: 0.5rem; }
.empty { color: var(--el-text-color-secondary); }
h3 { margin: 1.25rem 0 0.5rem; font-size: 1rem; }
.import-alert { margin-bottom: 0.75rem; }
.import-line { margin: 0.15rem 0; font-size: 0.85rem; }
.stats { margin-top: 1.25rem; }
.stats-line { margin: 0 0 0.5rem; color: var(--el-text-color-regular); }
.chart { width: 100%; height: 260px; }
</style>
