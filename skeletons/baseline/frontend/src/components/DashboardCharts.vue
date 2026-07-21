<template>
  <section v-if="hasAny" class="charts card">
    <h3>统计分析</h3>
    <div class="grid">
      <div v-if="statusOpt" class="chart-box">
        <div class="chart-title">{{ statusTitle }}</div>
        <div ref="statusEl" class="chart" />
      </div>
      <div v-if="trendOpt" class="chart-box">
        <div class="chart-title">近 7 日趋势</div>
        <div ref="trendEl" class="chart" />
      </div>
      <div v-if="stockOpt" class="chart-box wide">
        <div class="chart-title">{{ stockTitle }}</div>
        <div ref="stockEl" class="chart" />
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts/core'
import { PieChart, BarChart, LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { ticketCopy, getSchema, archiveCopy, reservationCopy } from '../utils/domainSchema.js'

echarts.use([PieChart, BarChart, LineChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

const props = defineProps({
  charts: { type: Object, default: () => ({}) },
  /** ticket | order | reservation | auto */
  mode: { type: String, default: 'auto' },
})

const statusEl = ref(null)
const trendEl = ref(null)
const stockEl = ref(null)
let statusChart
let trendChart
let stockChart

const stateLabels = computed(() => {
  const schema = getSchema() || {}
  if (props.mode === 'order' || (props.mode === 'auto' && schema.entities?.order)) {
    return schema.entities?.order?.states || {}
  }
  if (props.mode === 'reservation' || (props.mode === 'auto' && schema.entities?.reservation && !schema.entities?.ticket)) {
    return schema.entities?.reservation?.states || {}
  }
  return ticketCopy().states || {}
})

const statusTitle = computed(() => {
  if (props.mode === 'order') {
    const lab = getSchema()?.entities?.order?.label || '订单'
    return `${lab}状态`
  }
  if (props.mode === 'reservation') {
    const lab = reservationCopy().label || '预约'
    return `${lab}状态`
  }
  const lab = ticketCopy().label || '申请'
  return `${lab}状态`
})

/** 跟领域 archive.stock 文案，避免活动域还写「分类库存」 */
const stockTitle = computed(() => {
  const arch = archiveCopy() || {}
  const fields = arch.fields || []
  const stock = fields.find((f) => f && f.key === 'stock')
  const cat = fields.find((f) => f && f.key === 'category')
  const stockLab = (stock?.label || '').trim() || '余量'
  const catLab = (cat?.label || '').trim() || '分类'
  if (stockLab.startsWith(catLab)) return stockLab
  return `${catLab}${stockLab}`
})

function labelOf(name) {
  return stateLabels.value[name] || name || '未知'
}

function fillTrend(raw) {
  const map = {}
  for (const r of raw || []) {
    if (r?.day) map[r.day] = Number(r.value) || 0
  }
  const days = []
  const now = new Date()
  for (let i = 6; i >= 0; i--) {
    const d = new Date(now)
    d.setDate(now.getDate() - i)
    const key = d.toISOString().slice(0, 10)
    days.push({ day: key, value: map[key] || 0 })
  }
  return days
}

const statusOpt = computed(() => {
  const series = (props.charts?.statusSeries || []).filter((x) => Number(x.value) > 0)
  if (!series.length) return null
  return {
    tooltip: { trigger: 'item' },
    legend: { bottom: 0, type: 'scroll' },
    series: [
      {
        type: 'pie',
        radius: ['36%', '62%'],
        data: series.map((x) => ({ name: labelOf(x.name), value: Number(x.value) || 0 })),
      },
    ],
  }
})

const trendOpt = computed(() => {
  const filled = fillTrend(props.charts?.trendSeries)
  if (!filled.some((x) => x.value > 0) && !(props.charts?.trendSeries || []).length) {
    // 仍展示空轴，避免「有模块无图」困惑；若完全无 charts 则外层 hasAny 控制
  }
  const hasData = filled.some((x) => x.value > 0) || (props.charts?.trendSeries || []).length > 0
  if (!hasData && !statusOpt.value && !(props.charts?.stockSeries || []).length) return null
  if (!hasData && !statusOpt.value) return null
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 16, top: 24, bottom: 28 },
    xAxis: {
      type: 'category',
      data: filled.map((x) => x.day.slice(5)),
    },
    yAxis: { type: 'value', minInterval: 1 },
    series: [
      {
        type: 'line',
        smooth: true,
        areaStyle: { opacity: 0.12 },
        data: filled.map((x) => x.value),
      },
    ],
  }
})

const stockOpt = computed(() => {
  const series = (props.charts?.stockSeries || []).filter((x) => x?.name)
  if (!series.length) return null
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 48, right: 16, top: 24, bottom: 48 },
    xAxis: {
      type: 'category',
      data: series.map((x) => x.name),
      axisLabel: { interval: 0, rotate: series.length > 5 ? 28 : 0 },
    },
    yAxis: { type: 'value', minInterval: 1 },
    series: [
      {
        type: 'bar',
        data: series.map((x) => Number(x.value) || 0),
        barMaxWidth: 36,
      },
    ],
  }
})

const hasAny = computed(() => !!(statusOpt.value || trendOpt.value || stockOpt.value))

function render() {
  if (statusOpt.value && statusEl.value) {
    if (!statusChart) statusChart = echarts.init(statusEl.value)
    statusChart.setOption(statusOpt.value, true)
  } else if (statusChart) {
    statusChart.dispose()
    statusChart = null
  }
  if (trendOpt.value && trendEl.value) {
    if (!trendChart) trendChart = echarts.init(trendEl.value)
    trendChart.setOption(trendOpt.value, true)
  } else if (trendChart) {
    trendChart.dispose()
    trendChart = null
  }
  if (stockOpt.value && stockEl.value) {
    if (!stockChart) stockChart = echarts.init(stockEl.value)
    stockChart.setOption(stockOpt.value, true)
  } else if (stockChart) {
    stockChart.dispose()
    stockChart = null
  }
}

function onResize() {
  statusChart?.resize()
  trendChart?.resize()
  stockChart?.resize()
}

watch(
  () => props.charts,
  async () => {
    await nextTick()
    render()
  },
  { deep: true },
)

onMounted(async () => {
  await nextTick()
  render()
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  statusChart?.dispose()
  trendChart?.dispose()
  stockChart?.dispose()
})
</script>

<style scoped>
.card {
  background: #fff;
  border: 1px solid #e4eaf0;
  border-radius: 10px;
  padding: 16px;
  margin-top: 16px;
}
.card h3 { margin: 0 0 12px; font-size: 15px; }
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.chart-box {
  border: 1px solid #f0f3f6;
  border-radius: 8px;
  padding: 8px 8px 4px;
  min-height: 260px;
}
.chart-box.wide { grid-column: 1 / -1; }
.chart-title { font-size: 13px; color: #8a9aa6; margin: 0 4px 4px; }
.chart { width: 100%; height: 240px; }
@media (max-width: 900px) {
  .grid { grid-template-columns: 1fr; }
  .chart-box.wide { grid-column: auto; }
}
</style>
