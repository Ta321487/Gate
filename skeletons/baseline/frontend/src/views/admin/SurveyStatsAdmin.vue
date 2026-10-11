<template>
  <div>
    <div class="toolbar">
      <h2>回收统计</h2>
      <el-select v-model="formId" placeholder="选择问卷" style="width: 240px" @change="load">
        <el-option v-for="f in forms" :key="f.id" :label="f.title" :value="f.id" />
      </el-select>
    </div>
    <div v-if="formId" class="recycle card block">
      <div class="recycle-hd">
        <span>已回收 {{ responses.length }} 份</span>
        <span class="muted">目标 {{ recycleGoal }} 份</span>
      </div>
      <el-progress :percentage="recyclePct" :stroke-width="10" />
    </div>
    <el-table :data="responses" stripe class="mb">
      <el-table-column prop="username" label="填写人" width="140" />
      <el-table-column prop="submittedAt" label="提交时间" />
    </el-table>
    <template v-if="chartsOn">
      <h3 class="chart-title">{{ labels.surveyChartTitle || '结果图表' }}</h3>
      <div v-for="s in chartable" :key="'c-' + s.questionId" class="card block chart-block">
        <h4>{{ s.stem }}</h4>
        <div class="chart-row">
          <div :ref="(el) => setChartEl(s.questionId, 'bar', el)" class="chart" />
          <div :ref="(el) => setChartEl(s.questionId, 'pie', el)" class="chart" />
        </div>
      </div>
    </template>
    <article v-for="s in stats" :key="s.questionId" class="card block">
      <h3>{{ s.stem }}</h3>
      <p v-if="s.type === 'text'" class="muted">有效填空 {{ s.filledCount }} 份</p>
      <ul v-else>
        <li v-for="o in s.options || []" :key="o.key">{{ o.key }}. {{ o.label }} — {{ o.count }}</li>
      </ul>
    </article>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts/core'
import { PieChart, BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import http from '../../api/http'
import { getSchema } from '../../utils/domainSchema.js'

echarts.use([PieChart, BarChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

const schema = computed(() => getSchema() || {})
const labels = computed(() => schema.value.labels || {})
const chartsOn = computed(() => !!(schema.value.interactThicken || {}).surveyResultCharts)

const forms = ref([])
const formId = ref(null)
const responses = ref([])
const stats = ref([])
const chartEls = {}
const chartInst = {}

const recycleGoal = computed(() => {
  const f = forms.value.find((x) => x.id === formId.value)
  const n = Number(f?.targetCount || f?.goalCount || f?.stock || 0)
  return Number.isFinite(n) && n > 0 ? n : 20
})
const recyclePct = computed(() =>
  Math.min(100, Math.round((responses.value.length / recycleGoal.value) * 100)),
)
const chartable = computed(() =>
  (stats.value || []).filter((s) => s.type !== 'text' && (s.options || []).length),
)

function setChartEl(qid, kind, el) {
  if (!el) return
  chartEls[`${qid}-${kind}`] = el
}

function renderCharts() {
  if (!chartsOn.value) return
  for (const s of chartable.value) {
    const cats = (s.options || []).map((o) => o.label || o.key)
    const vals = (s.options || []).map((o) => o.count || 0)
    const barEl = chartEls[`${s.questionId}-bar`]
    const pieEl = chartEls[`${s.questionId}-pie`]
    if (barEl) {
      const key = `b-${s.questionId}`
      if (!chartInst[key]) chartInst[key] = echarts.init(barEl)
      chartInst[key].setOption({
        tooltip: { trigger: 'axis' },
        xAxis: { type: 'category', data: cats },
        yAxis: { type: 'value', minInterval: 1 },
        series: [{ type: 'bar', data: vals, name: labels.value.surveyChartBarLabel || '柱状图' }],
      })
    }
    if (pieEl) {
      const key = `p-${s.questionId}`
      if (!chartInst[key]) chartInst[key] = echarts.init(pieEl)
      chartInst[key].setOption({
        tooltip: { trigger: 'item' },
        series: [{
          type: 'pie',
          radius: '65%',
          name: labels.value.surveyChartPieLabel || '饼图',
          data: (s.options || []).map((o) => ({ name: o.label || o.key, value: o.count || 0 })),
        }],
      })
    }
  }
}

async function loadForms() {
  const res = await http.get('/api/survey/admin/forms')
  forms.value = res.data?.data || res.data || []
  if (forms.value.length && !formId.value) {
    formId.value = forms.value[0].id
    await load()
  }
}

async function load() {
  if (!formId.value) return
  const r = await http.get(`/api/survey/admin/forms/${formId.value}/responses`, {
    params: { page: 1, size: 50 },
  })
  responses.value = (r.data?.data || r.data || {}).list || []
  const s = await http.get(`/api/survey/admin/forms/${formId.value}/stats`)
  stats.value = s.data?.data || s.data || []
  await nextTick()
  renderCharts()
}

watch(chartable, async () => {
  await nextTick()
  renderCharts()
})

onMounted(loadForms)
onBeforeUnmount(() => {
  Object.values(chartInst).forEach((c) => c.dispose())
})
</script>

<style scoped>
.toolbar { display: flex; gap: 0.75rem; align-items: center; margin-bottom: 1rem; }
.mb { margin-bottom: 1rem; }
.block { padding: 1rem; margin-bottom: 0.75rem; }
.muted { color: var(--el-text-color-secondary); }
.recycle-hd {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 14px;
}
.chart-title { margin: 1rem 0 0.5rem; }
.chart-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.chart { height: 240px; }
@media (max-width: 800px) {
  .chart-row { grid-template-columns: 1fr; }
}
</style>
