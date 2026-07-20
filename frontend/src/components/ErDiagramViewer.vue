<template>
  <div class="er-viewer" :class="{ 'is-dark': isDark }">
    <div class="er-toolbar row mb-12">
      <div class="er-zoom-btns row">
        <n-button size="small" @click="zoomOut">缩小</n-button>
        <span class="er-zoom-label">{{ Math.round(scale * 100) }}%</span>
        <n-button size="small" @click="zoomIn">放大</n-button>
        <n-button size="small" @click="resetView">重置视口</n-button>
        <n-button size="small" @click="$emit('reload')">重置布局</n-button>
        <n-button size="small" type="primary" @click="download">下载 SVG</n-button>
      </div>
    </div>
    <div
      ref="frameRef"
      class="er-frame"
      :class="{ 'is-dragging-node': !!dragNode, 'is-panning': panning }"
      @wheel.prevent="onWheel"
      @pointerdown="onPointerDown"
      @pointermove="onPointerMove"
      @pointerup="onPointerUp"
      @pointercancel="onPointerUp"
      @pointerleave="onPointerUp"
    >
      <div class="er-canvas" :style="canvasStyle" v-html="svgHtml" />
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { isDark } from '../theme'

const props = defineProps({
  /** 后端初始 SVG（可含 xml 声明） */
  svgSource: { type: String, default: '' },
  downloadName: { type: String, default: 'er.svg' },
})

defineEmits(['reload'])

const frameRef = ref(null)
const svgHtml = ref('')
const scale = ref(1)
const panX = ref(0)
const panY = ref(0)
const panning = ref(false)
const dragNode = ref(null)

/** nodeId -> { dx, dy } 相对初始坐标的位移 */
const offsets = new Map()

let panLastX = 0
let panLastY = 0
let dragLastX = 0
let dragLastY = 0
/** 拖实体时跟随的 attr 节点 */
let dragFollowers = []

const SCALE_MIN = 0.25
const SCALE_MAX = 4
const SCALE_STEP = 0.15

const canvasStyle = computed(() => ({
  transform: `translate(${panX.value}px, ${panY.value}px) scale(${scale.value})`,
  transformOrigin: '0 0',
}))

function clampScale(s) {
  return Math.min(SCALE_MAX, Math.max(SCALE_MIN, s))
}

function getSvg() {
  return frameRef.value?.querySelector('svg') || null
}

function parseSvg(raw) {
  return (raw || '').replace(/^<\?xml[^>]*>\s*/i, '')
}

function applyOffsetsToDom() {
  const svg = getSvg()
  if (!svg) return
  svg.querySelectorAll('.er-node').forEach((g) => {
    const id = g.getAttribute('data-id')
    const o = offsets.get(id) || { dx: 0, dy: 0 }
    if (o.dx || o.dy) g.setAttribute('transform', `translate(${o.dx},${o.dy})`)
    else g.removeAttribute('transform')
  })
  refreshAllEdges(svg)
}

function loadSource(raw) {
  offsets.clear()
  dragNode.value = null
  dragFollowers = []
  svgHtml.value = parseSvg(raw)
  nextTick(() => {
    const svg = getSvg()
    if (!svg) return
    svg.querySelectorAll('.er-node').forEach((g) => {
      g.style.cursor = 'move'
      g.style.pointerEvents = 'all'
    })
    // 连线不抢事件，便于点到节点
    svg.querySelectorAll('.er-edge, .er-card, .er-title, .er-legend').forEach((el) => {
      el.style.pointerEvents = 'none'
    })
    const bg = svg.querySelector('rect')
    if (bg && !bg.classList.contains('er-bg-hit')) {
      bg.classList.add('er-bg-hit', 'er-paper')
      bg.style.pointerEvents = 'none'
    }
  })
}

watch(
  () => props.svgSource,
  (v) => {
    scale.value = 1
    panX.value = 0
    panY.value = 0
    loadSource(v)
  },
  { immediate: true },
)

function nodeCenter(g) {
  const id = g.getAttribute('data-id')
  const o = offsets.get(id) || { dx: 0, dy: 0 }
  const cx = Number(g.getAttribute('data-cx')) || 0
  const cy = Number(g.getAttribute('data-cy')) || 0
  return { x: cx + o.dx, y: cy + o.dy, g, id }
}

function shapeEdge(center, towardX, towardY) {
  const shape = center.g.getAttribute('data-shape') || 'rect'
  const cx = center.x
  const cy = center.y
  const tx = towardX
  const ty = towardY
  if (shape === 'ellipse') {
    const rx = Number(center.g.getAttribute('data-rx')) || 28
    const ry = Number(center.g.getAttribute('data-ry')) || 14
    const ox = tx - cx
    const oy = ty - cy
    if (Math.abs(ox) < 1e-9 && Math.abs(oy) < 1e-9) return { x: cx, y: cy - ry }
    const s = Math.hypot(ox / rx, oy / ry) || 1
    return { x: cx + ox / s, y: cy + oy / s }
  }
  if (shape === 'diamond') {
    const hw = Number(center.g.getAttribute('data-hw')) || 36
    const hh = Number(center.g.getAttribute('data-hh')) || 22
    const ox = tx - cx
    const oy = ty - cy
    if (Math.abs(ox) < 1e-9 && Math.abs(oy) < 1e-9) return { x: cx, y: cy - hh }
    const denom = Math.abs(ox) / hw + Math.abs(oy) / hh
    if (denom < 1e-9) return { x: cx, y: cy - hh }
    const t = 1 / denom
    return { x: cx + ox * t, y: cy + oy * t }
  }
  // rect
  const hw = Number(center.g.getAttribute('data-hw')) || 40
  const hh = Number(center.g.getAttribute('data-hh')) || 22
  const dx = tx - cx
  const dy = ty - cy
  if (Math.abs(dx) < 1e-9 && Math.abs(dy) < 1e-9) return { x: cx, y: cy - hh }
  const sx = Math.abs(dx) > 1e-9 ? hw / Math.abs(dx) : Infinity
  const sy = Math.abs(dy) > 1e-9 ? hh / Math.abs(dy) : Infinity
  const t = Math.min(sx, sy)
  return { x: cx + dx * t, y: cy + dy * t }
}

function cardPos(a, b, t = 0.35) {
  const px = a.x * (1 - t) + b.x * t
  const py = a.y * (1 - t) + b.y * t
  const dx = b.x - a.x
  const dy = b.y - a.y
  const L = Math.hypot(dx, dy) || 1
  return { x: px - (dy / L) * 12, y: py + (dx / L) * 12 }
}

function refreshEdge(line, byId) {
  const fromId = line.getAttribute('data-from')
  const toId = line.getAttribute('data-to')
  const a = byId.get(fromId)
  const b = byId.get(toId)
  if (!a || !b) return null
  const p0 = shapeEdge(a, b.x, b.y)
  const p1 = shapeEdge(b, a.x, a.y)
  line.setAttribute('x1', p0.x.toFixed(1))
  line.setAttribute('y1', p0.y.toFixed(1))
  line.setAttribute('x2', p1.x.toFixed(1))
  line.setAttribute('y2', p1.y.toFixed(1))
  return { p0, p1, fromId, toId }
}

function refreshAllEdges(svg) {
  const byId = new Map()
  svg.querySelectorAll('.er-node').forEach((g) => {
    const c = nodeCenter(g)
    byId.set(c.id, c)
  })
  const edgeEnds = new Map()
  svg.querySelectorAll('line.er-edge').forEach((line) => {
    const ends = refreshEdge(line, byId)
    if (!ends) return
    const key = `${ends.fromId}|${ends.toId}`
    const key2 = `${ends.toId}|${ends.fromId}`
    edgeEnds.set(key, ends)
    edgeEnds.set(key2, { p0: ends.p1, p1: ends.p0, fromId: ends.toId, toId: ends.fromId })
  })
  svg.querySelectorAll('text.er-card').forEach((txt) => {
    const fromId = txt.getAttribute('data-from')
    const toId = txt.getAttribute('data-to')
    const ends = edgeEnds.get(`${fromId}|${toId}`)
    if (!ends) return
    // 基数靠近实体侧：from 是实体，to 是 rel
    const pos = cardPos(ends.p0, ends.p1, 0.35)
    txt.setAttribute('x', pos.x.toFixed(1))
    txt.setAttribute('y', pos.y.toFixed(1))
  })
}

function bumpOffset(id, ddx, ddy) {
  const cur = offsets.get(id) || { dx: 0, dy: 0 }
  offsets.set(id, { dx: cur.dx + ddx, dy: cur.dy + ddy })
}

function setNodeTransform(g, id) {
  const o = offsets.get(id) || { dx: 0, dy: 0 }
  if (o.dx || o.dy) g.setAttribute('transform', `translate(${o.dx},${o.dy})`)
  else g.removeAttribute('transform')
}

function findNode(target) {
  if (!target) return null
  if (typeof target.closest === 'function') return target.closest('.er-node')
  let el = target
  while (el && el !== frameRef.value) {
    if (el.classList?.contains('er-node')) return el
    el = el.parentElement || el.parentNode
  }
  return null
}

function onPointerDown(e) {
  if (e.button !== 0) return
  const node = findNode(e.target)
  if (node) {
    dragNode.value = node
    dragLastX = e.clientX
    dragLastY = e.clientY
    dragFollowers = []
    const kind = node.getAttribute('data-kind')
    const id = node.getAttribute('data-id')
    if (kind === 'entity') {
      const svg = getSvg()
      svg?.querySelectorAll('.er-node[data-parent]').forEach((g) => {
        if (g.getAttribute('data-parent') === id) dragFollowers.push(g)
      })
    }
    node.classList.add('er-node-active')
    e.currentTarget.setPointerCapture?.(e.pointerId)
    e.stopPropagation()
    return
  }
  panning.value = true
  panLastX = e.clientX
  panLastY = e.clientY
  e.currentTarget.setPointerCapture?.(e.pointerId)
}

function onPointerMove(e) {
  if (dragNode.value) {
    const ddx = (e.clientX - dragLastX) / scale.value
    const ddy = (e.clientY - dragLastY) / scale.value
    dragLastX = e.clientX
    dragLastY = e.clientY
    const id = dragNode.value.getAttribute('data-id')
    bumpOffset(id, ddx, ddy)
    setNodeTransform(dragNode.value, id)
    for (const g of dragFollowers) {
      const fid = g.getAttribute('data-id')
      bumpOffset(fid, ddx, ddy)
      setNodeTransform(g, fid)
    }
    const svg = getSvg()
    if (svg) refreshAllEdges(svg)
    return
  }
  if (!panning.value) return
  panX.value += e.clientX - panLastX
  panY.value += e.clientY - panLastY
  panLastX = e.clientX
  panLastY = e.clientY
}

function onPointerUp(e) {
  if (dragNode.value) {
    dragNode.value.classList.remove('er-node-active')
    dragNode.value = null
    dragFollowers = []
  }
  panning.value = false
  try {
    e.currentTarget?.releasePointerCapture?.(e.pointerId)
  } catch {
    /* ignore */
  }
}

function onWheel(e) {
  const frame = frameRef.value
  if (!frame) return
  const rect = frame.getBoundingClientRect()
  const mx = e.clientX - rect.left
  const my = e.clientY - rect.top
  const prev = scale.value
  const next = clampScale(prev * (e.deltaY < 0 ? 1.1 : 1 / 1.1))
  if (next === prev) return
  const wx = (mx - panX.value) / prev
  const wy = (my - panY.value) / prev
  scale.value = next
  panX.value = mx - wx * next
  panY.value = my - wy * next
}

function zoomIn() {
  scale.value = clampScale(scale.value + SCALE_STEP)
}

function zoomOut() {
  scale.value = clampScale(scale.value - SCALE_STEP)
}

function resetView() {
  scale.value = 1
  panX.value = 0
  panY.value = 0
}

function serializeSvg() {
  const svg = getSvg()
  if (!svg) return ''
  applyOffsetsToDom()
  const clone = svg.cloneNode(true)
  clone.querySelectorAll('.er-node-active').forEach((el) => el.classList.remove('er-node-active'))
  clone.querySelectorAll('[style]').forEach((el) => el.removeAttribute('style'))
  // bake transforms into data-cx/cy for a cleaner export? keep transform is fine for SVG viewers
  const xml = new XMLSerializer().serializeToString(clone)
  if (xml.startsWith('<?xml')) return xml
  return `<?xml version="1.0" encoding="UTF-8"?>\n${xml}`
}

function download() {
  const xml = serializeSvg()
  if (!xml) return
  const blob = new Blob([xml], { type: 'image/svg+xml;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = props.downloadName
  a.click()
  URL.revokeObjectURL(url)
}

defineExpose({ serializeSvg, download, resetView })
</script>

<style scoped>
.er-toolbar {
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 8px;
}
.er-zoom-btns {
  gap: 8px;
  align-items: center;
}
.er-zoom-label {
  min-width: 48px;
  text-align: center;
  font-variant-numeric: tabular-nums;
  font-size: 13px;
  color: var(--muted);
}
.er-frame {
  height: 72vh;
  overflow: hidden;
  border: 1px solid var(--line);
  background: var(--er-bg, #fafafa);
  cursor: grab;
  touch-action: none;
  user-select: none;
}
.er-frame.is-panning,
.er-frame:active:not(.is-dragging-node) {
  cursor: grabbing;
}
.er-frame.is-dragging-node {
  cursor: move;
}
.er-canvas {
  display: inline-block;
  will-change: transform;
}
.er-canvas :deep(svg) {
  display: block;
  max-width: none;
  height: auto;
}
.er-canvas :deep(.er-node-active) rect,
.er-canvas :deep(.er-node-active) ellipse,
.er-canvas :deep(.er-node-active) polygon {
  stroke: #2563eb;
  stroke-width: 2;
}

/* 夜间：黑白线框图直接反相，避免半套 CSS 盖属性导致浅字白底 */
.er-viewer.is-dark .er-frame {
  background: #0f161e;
}
.er-viewer.is-dark .er-canvas {
  filter: invert(1) hue-rotate(180deg);
}
.er-viewer.is-dark .er-canvas :deep(.er-node-active) rect,
.er-viewer.is-dark .er-canvas :deep(.er-node-active) ellipse,
.er-viewer.is-dark .er-canvas :deep(.er-node-active) polygon {
  stroke: #1d4ed8;
}
</style>
