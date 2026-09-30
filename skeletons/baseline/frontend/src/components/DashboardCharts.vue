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
      <div v-if="monthOpt" class="chart-box">
        <div class="chart-title">近 6 个月销量</div>
        <div ref="monthEl" class="chart" />
      </div>
      <div v-if="stockOpt" class="chart-box wide">
        <div class="chart-title">{{ stockTitle }}</div>
        <div ref="stockEl" class="chart" />
      </div>
      <div v-if="hotOpt" class="chart-box wide">
        <div class="chart-title">{{ hotTitle }}</div>
        <div ref="hotEl" class="chart" />
      </div>
      <div v-if="stockIoOpt" class="chart-box">
        <div class="chart-title">入出库分布</div>
        <div ref="stockIoEl" class="chart" />
      </div>
      <div v-if="channelOpt" class="chart-box">
        <div class="chart-title">{{ channelTitle }}</div>
        <div ref="channelEl" class="chart" />
      </div>
      <div v-if="stageOpt" class="chart-box">
        <div class="chart-title">{{ stageTitle }}</div>
        <div ref="stageEl" class="chart" />
      </div>
      <div v-if="leadOpt" class="chart-box">
        <div class="chart-title">{{ leadTitle }}</div>
        <div ref="leadEl" class="chart" />
      </div>
      <div v-if="funnelOpt" class="chart-box">
        <div class="chart-title">{{ funnelTitle }}</div>
        <div ref="funnelEl" class="chart" />
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
const monthEl = ref(null)
const stockEl = ref(null)
const hotEl = ref(null)
const stockIoEl = ref(null)
const channelEl = ref(null)
const stageEl = ref(null)
const leadEl = ref(null)
const funnelEl = ref(null)
let statusChart
let trendChart
let monthChart
let stockChart
let hotChart
let stockIoChart
let channelChart
let stageChart
let leadChart
let funnelChart

const labels = computed(() => getSchema()?.labels || {})
const channelTitle = computed(() => {
  const hint = labels.value.channelPieHint || ''
  return hint ? '跟进方式分布' : '联系渠道'
})
const stageTitle = computed(() => {
  if (labels.value.stageFunnelHint) return '客户阶段漏斗'
  return '档案阶段分布'
})
const leadTitle = computed(() => '线索来源分布')
const funnelTitle = computed(() => {
  if (labels.value.listingFunnelHint) return '成交漏斗'
  return '阶段分布'
})

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

const hotTitle = computed(() => {
  if (props.mode === 'order') return '热销商品'
  const lab = ticketCopy().label || '办理'
  if (/借阅|借用/.test(lab) || /图书|设备/.test(archiveCopy()?.label || '')) return '热门排行'
  return `${lab}排行`
})

function labelOf(name) {
  return stateLabels.value[name] || name || '未知'
}

/** 图表文字/轴线跟门户 token，避免深色皮肤轴标发黑不可读 */
function portalChartInk() {
  const s = getComputedStyle(document.documentElement)
  return {
    ink: s.getPropertyValue('--portal-ink').trim() || '#15202b',
    muted: s.getPropertyValue('--portal-muted').trim() || '#6b7c8a',
    line: s.getPropertyValue('--portal-line').trim() || '#d5dde3',
    accent: s.getPropertyValue('--portal-accent').trim() || '#0b6e75',
  }
}

function withPortalChartTheme(opt) {
  if (!opt) return opt
  const c = portalChartInk()
  const out = {
    ...opt,
    color: opt.color || [c.accent, '#60a5fa', '#f59e0b', '#34d399', '#f472b6'],
    textStyle: { ...(opt.textStyle || {}), color: c.ink },
  }
  if (opt.legend) {
    out.legend = {
      ...opt.legend,
      textStyle: { ...(opt.legend.textStyle || {}), color: c.muted },
    }
  }
  if (opt.xAxis) {
    const xa = { ...opt.xAxis }
    xa.axisLabel = { ...(xa.axisLabel || {}), color: c.muted }
    xa.axisLine = { ...(xa.axisLine || {}), lineStyle: { color: c.line } }
    out.xAxis = xa
  }
  if (opt.yAxis) {
    const ya = { ...opt.yAxis }
    ya.axisLabel = { ...(ya.axisLabel || {}), color: c.muted }
    ya.splitLine = {
      ...(ya.splitLine || {}),
      lineStyle: { color: c.line },
    }
    out.yAxis = ya
  }
  return out
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

function fillMonth(raw) {
  const map = {}
  for (const r of raw || []) {
    if (r?.month) map[r.month] = Number(r.value) || 0
  }
  const months = []
  const now = new Date()
  for (let i = 5; i >= 0; i--) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1)
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
    months.push({ month: key, value: map[key] || 0 })
  }
  return months
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

const monthOpt = computed(() => {
  const filled = fillMonth(props.charts?.monthSeries)
  const hasData = filled.some((x) => x.value > 0) || (props.charts?.monthSeries || []).length > 0
  if (!hasData) return null
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 16, top: 24, bottom: 28 },
    xAxis: {
      type: 'category',
      data: filled.map((x) => x.month),
    },
    yAxis: { type: 'value', minInterval: 1 },
    series: [
      {
        type: 'bar',
        data: filled.map((x) => x.value),
        barMaxWidth: 28,
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

const hotOpt = computed(() => {
  const series = (props.charts?.hotItemSeries || []).filter((x) => x?.name)
  if (!series.length) return null
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 48, right: 16, top: 24, bottom: 48 },
    xAxis: {
      type: 'category',
      data: series.map((x) => x.name),
      axisLabel: { interval: 0, rotate: series.length > 4 ? 28 : 0 },
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

const stockIoOpt = computed(() => {
  const series = (props.charts?.stockIoSeries || []).filter((x) => x?.name)
  if (!series.length) return null
  return {
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [
      {
        type: 'pie',
        radius: ['36%', '62%'],
        data: series.map((x) => ({ name: x.name, value: Number(x.value) || 0 })),
      },
    ],
  }
})

function pieFromSeries(series) {
  const rows = (series || []).filter((x) => x?.name && Number(x.value) > 0)
  if (!rows.length) return null
  return {
    tooltip: { trigger: 'item' },
    legend: { bottom: 0, type: 'scroll' },
    series: [
      {
        type: 'pie',
        radius: ['36%', '62%'],
        data: rows.map((x) => ({ name: x.name, value: Number(x.value) || 0 })),
      },
    ],
  }
}

function barFunnelFromSeries(series) {
  const rows = (series || []).filter((x) => x?.name)
  if (!rows.length) return null
  // 漏斗视觉：柱状按数量降序（后端已 ORDER BY value DESC）
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 48, right: 16, top: 24, bottom: 48 },
    xAxis: {
      type: 'category',
      data: rows.map((x) => x.name),
      axisLabel: { interval: 0, rotate: rows.length > 4 ? 28 : 0 },
    },
    yAxis: { type: 'value', minInterval: 1 },
    series: [
      {
        type: 'bar',
        data: rows.map((x) => Number(x.value) || 0),
        barMaxWidth: 36,
      },
    ],
  }
}

const channelOpt = computed(() => {
  if (!labels.value.channelPieHint && !(props.charts?.channelSeries || []).length) return null
  return pieFromSeries(props.charts?.channelSeries)
})

const stageOpt = computed(() => {
  // 有阶段漏斗文案，或有 stage 数据时展示
  if (!labels.value.stageFunnelHint && !(props.charts?.stageSeries || []).length) return null
  if (labels.value.stageFunnelHint) return barFunnelFromSeries(props.charts?.stageSeries)
  return pieFromSeries(props.charts?.stageSeries)
})

const leadOpt = computed(() => {
  const series = props.charts?.leadSourceSeries || []
  if (!series.length) return null
  return pieFromSeries(series)
})

const funnelOpt = computed(() => {
  if (!labels.value.listingFunnelHint) return null
  return barFunnelFromSeries(props.charts?.listingFunnelSeries)
})

const hasAny = computed(
  () =>
    !!(
      statusOpt.value
      || trendOpt.value
      || monthOpt.value
      || stockOpt.value
      || hotOpt.value
      || stockIoOpt.value
      || channelOpt.value
      || stageOpt.value
      || leadOpt.value
      || funnelOpt.value
    ),
)

function render() {
  if (statusOpt.value && statusEl.value) {
    if (!statusChart) statusChart = echarts.init(statusEl.value)
    statusChart.setOption(withPortalChartTheme(statusOpt.value), true)
  } else if (statusChart) {
    statusChart.dispose()
    statusChart = null
  }
  if (trendOpt.value && trendEl.value) {
    if (!trendChart) trendChart = echarts.init(trendEl.value)
    trendChart.setOption(withPortalChartTheme(trendOpt.value), true)
  } else if (trendChart) {
    trendChart.dispose()
    trendChart = null
  }
  if (monthOpt.value && monthEl.value) {
    if (!monthChart) monthChart = echarts.init(monthEl.value)
    monthChart.setOption(withPortalChartTheme(monthOpt.value), true)
  } else if (monthChart) {
    monthChart.dispose()
    monthChart = null
  }
  if (stockOpt.value && stockEl.value) {
    if (!stockChart) stockChart = echarts.init(stockEl.value)
    stockChart.setOption(withPortalChartTheme(stockOpt.value), true)
  } else if (stockChart) {
    stockChart.dispose()
    stockChart = null
  }
  if (hotOpt.value && hotEl.value) {
    if (!hotChart) hotChart = echarts.init(hotEl.value)
    hotChart.setOption(withPortalChartTheme(hotOpt.value), true)
  } else if (hotChart) {
    hotChart.dispose()
    hotChart = null
  }
  if (stockIoOpt.value && stockIoEl.value) {
    if (!stockIoChart) stockIoChart = echarts.init(stockIoEl.value)
    stockIoChart.setOption(withPortalChartTheme(stockIoOpt.value), true)
  } else if (stockIoChart) {
    stockIoChart.dispose()
    stockIoChart = null
  }
  if (channelOpt.value && channelEl.value) {
    if (!channelChart) channelChart = echarts.init(channelEl.value)
    channelChart.setOption(withPortalChartTheme(channelOpt.value), true)
  } else if (channelChart) {
    channelChart.dispose()
    channelChart = null
  }
  if (stageOpt.value && stageEl.value) {
    if (!stageChart) stageChart = echarts.init(stageEl.value)
    stageChart.setOption(withPortalChartTheme(stageOpt.value), true)
  } else if (stageChart) {
    stageChart.dispose()
    stageChart = null
  }
  if (leadOpt.value && leadEl.value) {
    if (!leadChart) leadChart = echarts.init(leadEl.value)
    leadChart.setOption(withPortalChartTheme(leadOpt.value), true)
  } else if (leadChart) {
    leadChart.dispose()
    leadChart = null
  }
  if (funnelOpt.value && funnelEl.value) {
    if (!funnelChart) funnelChart = echarts.init(funnelEl.value)
    funnelChart.setOption(withPortalChartTheme(funnelOpt.value), true)
  } else if (funnelChart) {
    funnelChart.dispose()
    funnelChart = null
  }
}

function onResize() {
  statusChart?.resize()
  trendChart?.resize()
  monthChart?.resize()
  stockChart?.resize()
  hotChart?.resize()
  stockIoChart?.resize()
  channelChart?.resize()
  stageChart?.resize()
  leadChart?.resize()
  funnelChart?.resize()
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
  monthChart?.dispose()
  stockChart?.dispose()
  hotChart?.dispose()
  stockIoChart?.dispose()
  channelChart?.dispose()
  stageChart?.dispose()
  leadChart?.dispose()
  funnelChart?.dispose()
})
</script>

<style scoped>
.card {
  background: var(--portal-surface, #fff);
  border: var(--portal-border-width, 1px) solid var(--portal-line, #e4eaf0);
  border-radius: var(--portal-radius, 10px);
  box-shadow: var(--portal-shadow, none);
  padding: 16px;
  margin-top: 16px;
}
.card h3 { margin: 0 0 12px; font-size: 15px; }
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--portal-gap, 12px);
}
.chart-box {
  border: var(--portal-border-width, 1px) solid var(--portal-line, #f0f3f6);
  border-radius: var(--portal-radius-sm, 8px);
  padding: 8px 8px 4px;
  min-height: 260px;
}
.chart-box.wide { grid-column: 1 / -1; }
.chart-title { font-size: 13px; color: var(--portal-muted, #8a9aa6); margin: 0 4px 4px; }
.chart { width: 100%; height: 240px; }
@media (max-width: 900px) {
  .grid { grid-template-columns: 1fr; }
  .chart-box.wide { grid-column: auto; }
}
</style>
