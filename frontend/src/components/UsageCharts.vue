<template>
  <div ref="boxEl" class="usage-chart-box">
    <div class="usage-chart-title">
      按日 Token 趋势
      <span class="muted mono">· 合计 {{ fmtK(totalTokens) }}</span>
    </div>
    <svg
      v-if="line.points.length"
      class="usage-chart-svg"
      :viewBox="`0 0 ${W} ${H}`"
      preserveAspectRatio="xMidYMid meet"
      role="img"
      :aria-label="`按日 Token 趋势，共 ${totalTokens} tokens`"
    >
      <defs>
        <linearGradient id="usageLineFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="var(--teal)" stop-opacity="0.28" />
          <stop offset="100%" stop-color="var(--teal)" stop-opacity="0" />
        </linearGradient>
      </defs>
      <line
        v-for="(g, i) in line.gridYs"
        :key="'g'+i"
        :x1="PAD.l"
        :x2="W - PAD.r"
        :y1="g"
        :y2="g"
        class="usage-grid"
      />
      <path :d="line.area" class="usage-area" />
      <path :d="line.path" class="usage-line" fill="none" />
      <circle
        v-for="(p, i) in line.dots"
        :key="'d'+i"
        :cx="p.x"
        :cy="p.y"
        r="2.5"
        class="usage-dot"
      >
        <title>{{ p.label }}</title>
      </circle>
      <text
        v-for="(t, i) in line.xLabels"
        :key="'x'+i"
        :x="t.x"
        :y="H - 6"
        class="usage-axis"
        text-anchor="middle"
      >{{ t.text }}</text>
      <text
        v-for="(t, i) in line.yLabels"
        :key="'y'+i"
        :x="PAD.l - 6"
        :y="t.y + 3"
        class="usage-axis"
        text-anchor="end"
      >{{ t.text }}</text>
    </svg>
    <div v-else class="empty-hint usage-chart-empty">
      <div class="empty-title">暂无用量数据</div>
      <div class="empty-desc">尚未产生调用，或当前筛选范围内没有记录</div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'

const props = defineProps({
  daily: { type: Array, default: () => [] },
})

const H = 168
const PAD = { t: 12, r: 10, b: 24, l: 40 }
const boxEl = ref(null)
const boxW = ref(640)
let ro = null

const W = computed(() => Math.max(320, Math.round(boxW.value)))

const totalTokens = computed(() =>
  (props.daily || []).reduce((s, d) => s + (Number(d.tokens) || 0), 0),
)

function fmtK(n) {
  const v = Number(n) || 0
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`
  if (v >= 1000) return `${(v / 1000).toFixed(v >= 10000 ? 0 : 1)}k`
  return String(v)
}

const line = computed(() => {
  const rows = props.daily || []
  const w = W.value
  if (!rows.length) {
    return { points: [], dots: [], path: '', area: '', gridYs: [], xLabels: [], yLabels: [] }
  }
  const values = rows.map((r) => Number(r.tokens) || 0)
  const maxV = Math.max(...values, 1)
  const innerW = w - PAD.l - PAD.r
  const innerH = H - PAD.t - PAD.b
  const n = rows.length
  const pts = rows.map((r, i) => {
    const x = PAD.l + (n === 1 ? innerW / 2 : (i / (n - 1)) * innerW)
    const y = PAD.t + innerH - (values[i] / maxV) * innerH
    return {
      x,
      y,
      label: `${r.date} · ${values[i]} tokens · ${r.calls || 0} 次`,
    }
  })
  const path = pts.map((p, i) => `${i ? 'L' : 'M'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')
  const area = pts.length
    ? `${path} L${pts[pts.length - 1].x.toFixed(1)},${(PAD.t + innerH).toFixed(1)} L${pts[0].x.toFixed(1)},${(PAD.t + innerH).toFixed(1)} Z`
    : ''
  const gridYs = [0, 0.5, 1].map((t) => PAD.t + innerH * (1 - t))
  const yLabels = [
    { y: PAD.t, text: fmtK(maxV) },
    { y: PAD.t + innerH / 2, text: fmtK(maxV / 2) },
    { y: PAD.t + innerH, text: '0' },
  ]
  const xLabels = []
  if (n === 1) {
    xLabels.push({ x: pts[0].x, text: String(rows[0].date).slice(5) })
  } else {
    const idxs = n <= 7
      ? rows.map((_, i) => i)
      : [0, Math.floor((n - 1) / 2), n - 1]
    const seen = new Set()
    for (const i of idxs) {
      if (seen.has(i)) continue
      seen.add(i)
      xLabels.push({ x: pts[i].x, text: String(rows[i].date).slice(5) })
    }
  }
  return { points: pts, dots: pts, path, area, gridYs, xLabels, yLabels }
})

onMounted(() => {
  if (!boxEl.value || typeof ResizeObserver === 'undefined') return
  const measure = () => {
    const w = boxEl.value?.clientWidth
    if (w) boxW.value = w
  }
  measure()
  ro = new ResizeObserver(measure)
  ro.observe(boxEl.value)
})
onUnmounted(() => {
  ro?.disconnect()
  ro = null
})
</script>
