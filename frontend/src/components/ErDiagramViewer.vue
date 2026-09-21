<template>
  <div class="er-viewer" :class="{ 'is-dark': isDark }">
    <div class="er-toolbar row mb-12">
      <div class="er-zoom-btns row">
        <n-radio-group v-model:value="modeLocal" size="small" :disabled="loading" @update:value="onModeChange">
          <n-radio-button value="total">总图</n-radio-button>
          <n-radio-button value="part">实体属性图</n-radio-button>
        </n-radio-group>
        <n-select
          v-if="modeLocal === 'part'"
          v-model:value="entityLocal"
          size="small"
          :options="entityOptions"
          :loading="loading"
          :disabled="loading"
          placeholder="选择实体"
          style="width:160px"
          @update:value="onEntityChange"
        />
        <n-button
          v-if="modeLocal === 'part'"
          size="small"
          secondary
          :loading="loading"
          @click="$emit('export-all-parts')"
        >导出全部属性图</n-button>
        <n-button size="small" @click="zoomOut">缩小</n-button>
        <span class="er-zoom-label">{{ Math.round(scale * 100) }}%</span>
        <n-button size="small" @click="zoomIn">放大</n-button>
        <n-button size="small" @click="resetView">重置视口</n-button>
        <n-button size="small" :loading="loading" @click="onResetLayout">重置布局</n-button>
        <n-button size="small" :type="showGrid ? 'primary' : 'default'" secondary @click="showGrid = !showGrid">网格</n-button>
        <n-select
          v-model:value="strokePreset"
          size="small"
          :options="strokeOptions"
          :consistent-menu-width="false"
          style="width:148px"
          @update:value="applyStrokePreset"
        />
        <n-button size="small" type="primary" :loading="busy" @click="copyPng">复制图片</n-button>
        <n-button size="small" type="primary" secondary :loading="busy" @click="downloadPng">下载 PNG</n-button>
        <n-button size="small" quaternary @click="downloadSvg">下载矢量源</n-button>
      </div>
    </div>
    <p class="small muted er-hint mb-8">
      {{
        modeLocal === 'total'
          ? '概念 E-R：实体 + 动词联系 + 基数（不含属性；中间表已画成 N:M）'
          : '实体属性图：仅自身属性（不含外键）；按概念实体各导出一张'
      }}
    </p>
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
      <ContentLoading v-if="loading && !svgSource" :rows="1" block compact />
      <div v-else class="er-canvas" :style="canvasStyle">
        <svg
          v-if="showGrid"
          class="er-grid"
          :style="{ width: paperW + 'px', height: paperH + 'px' }"
          aria-hidden="true"
        >
          <defs>
            <pattern id="er-grid-pat" width="10" height="10" patternUnits="userSpaceOnUse">
              <path d="M 10 0 L 0 0 0 10" fill="none" stroke="#c5c5c5" stroke-width="1" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#er-grid-pat)" />
        </svg>
        <div class="er-svg-host" v-html="svgHtml" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { message } from '../api'
import { isDark } from '../theme'
import ContentLoading from './ContentLoading.vue'

const props = defineProps({
  /** 后端初始 SVG（可含 xml 声明） */
  svgSource: { type: String, default: '' },
  /** 下载文件名（可带 .svg/.png，导出时自动换扩展名） */
  downloadName: { type: String, default: 'er' },
  /** total | part */
  mode: { type: String, default: 'total' },
  /** 分图实体表名 */
  entity: { type: String, default: '' },
  /** [{ value, label }] */
  entityOptions: { type: Array, default: () => [] },
  /** 后端重新拉 SVG 中 */
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['reload', 'update:mode', 'update:entity', 'export-all-parts', 'save-view', 'reset-layout'])

const PNG_SCALE = 2.5

const strokeOptions = [
  { label: '线宽 · 细', value: 'thin' },
  { label: '线宽 · 标准', value: 'normal' },
  { label: '线宽 · 粗', value: 'thick' },
]
const STROKE_SCALE = { thin: 0.75, normal: 1, thick: 1.5 }

const frameRef = ref(null)
const svgHtml = ref('')
const scale = ref(1)
const panX = ref(0)
const panY = ref(0)
const panning = ref(false)
const dragNode = ref(null)
const strokePreset = ref('normal')
const showGrid = ref(true)
const paperW = ref(800)
const paperH = ref(600)
const GRID = 10
const busy = ref(false)
const modeLocal = ref(props.mode === 'part' ? 'part' : 'total')
const entityLocal = ref(props.entity || '')

/** nodeId -> { dx, dy } 相对初始坐标的位移 */
const offsets = new Map()
const relGrab = new Map()

let panLastX = 0
let panLastY = 0
let dragLastX = 0
let dragLastY = 0
/** 拖实体时跟随的 attr 节点 */
let dragFollowers = []
let dragPins = []
let dragCards = []
let dragNodeEls = new Map()
let dragRelEls = []
let dragFrame = 0
let pendingDX = 0
let pendingDY = 0
let grabX = 0
let grabY = 0
let grabOrigin = null
let dragMoved = false
let viewDirty = false
let lastPinRel = ''
let loadedMode = props.mode === 'part' ? 'part' : 'total'
let loadedEntity = props.entity || ''

const SCALE_MIN = 0.25
const SCALE_MAX = 4
const SCALE_STEP = 0.15

const canvasStyle = computed(() => ({
  transform: `translate(${panX.value}px, ${panY.value}px) scale(${scale.value})`,
  transformOrigin: '0 0',
}))

const fileBase = computed(() =>
  String(props.downloadName || 'er').replace(/\.(svg|png)$/i, '') || 'er',
)

watch(
  () => props.mode,
  (v) => {
    modeLocal.value = v === 'part' ? 'part' : 'total'
  },
)
watch(
  () => props.entity,
  (v) => {
    entityLocal.value = v || ''
  },
)

function onResetLayout() {
  viewDirty = false
  emit('reset-layout')
}

function seedOffsetsFromDom(svg) {
  offsets.clear()
  svg.querySelectorAll('.er-node').forEach((g) => {
    const id = g.getAttribute('data-id')
    const tr = g.getAttribute('transform') || ''
    const m = /translate\(\s*([-\d.]+)(?:[,\s]+)([-\d.]+)\s*\)/.exec(tr)
    if (id && m) offsets.set(id, { dx: Number(m[1]) || 0, dy: Number(m[2]) || 0 })
  })
}

function syncPaperSize() {
  const svg = getSvg()
  if (!svg) return
  const { w, h } = svgSize(svg)
  paperW.value = w
  paperH.value = h
}

function snapGrid(v) {
  return Math.round(v / GRID) * GRID
}

function onModeChange(v) {
  emit('update:mode', v)
}
function onEntityChange(v) {
  emit('update:entity', v || '')
}

function clampScale(s) {
  return Math.min(SCALE_MAX, Math.max(SCALE_MIN, s))
}

function getSvg() {
  return frameRef.value?.querySelector('svg:not(.er-grid)') || null
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
}

function snapshotBaseStrokes(svg) {
  svg.querySelectorAll('[stroke-width]').forEach((el) => {
    if (!el.hasAttribute('data-base-sw')) {
      el.setAttribute('data-base-sw', el.getAttribute('stroke-width') || '1')
    }
  })
}

function applyStrokePreset() {
  const svg = getSvg()
  if (!svg) return
  snapshotBaseStrokes(svg)
  const mul = STROKE_SCALE[strokePreset.value] ?? 1
  svg.querySelectorAll('[data-base-sw]').forEach((el) => {
    const base = Number(el.getAttribute('data-base-sw')) || 1
    const next = Math.round(base * mul * 100) / 100
    el.setAttribute('stroke-width', String(next))
  })
}

function loadSource(raw) {
  loadedMode = props.mode === 'part' ? 'part' : 'total'
  loadedEntity = props.entity || ''
  offsets.clear()
  relGrab.clear()
  dragNode.value = null
  dragFollowers = []
  svgHtml.value = parseSvg(raw)
  nextTick(() => {
    const svg = getSvg()
    if (!svg) return
    seedOffsetsFromDom(svg)
    svg.querySelectorAll('.er-node').forEach((g) => {
      g.style.cursor = 'move'
      g.style.pointerEvents = 'all'
    })
    svg.querySelectorAll('.er-node[data-kind="rel"]').forEach((g) => {
      if (g.querySelector('.er-hit')) return
      const hw = (Number(g.getAttribute('data-hw')) || 36) + 14
      const hh = (Number(g.getAttribute('data-hh')) || 22) + 10
      const cx = Number(g.getAttribute('data-cx')) || 0
      const cy = Number(g.getAttribute('data-cy')) || 0
      const hit = document.createElementNS('http://www.w3.org/2000/svg', 'polygon')
      hit.setAttribute('class', 'er-hit')
      hit.setAttribute('fill', 'transparent')
      hit.setAttribute('stroke', 'none')
      hit.setAttribute('points', `${cx},${cy - hh} ${cx + hw},${cy} ${cx},${cy + hh} ${cx - hw},${cy}`)
      g.insertBefore(hit, g.firstChild)
    })
    // 连线不抢事件，便于点到节点
    svg.querySelectorAll('.er-edge, .er-card').forEach((el) => {
      el.style.pointerEvents = 'none'
    })
    const bg = svg.querySelector('rect')
    if (bg && !bg.classList.contains('er-bg-hit')) {
      bg.classList.add('er-bg-hit', 'er-paper')
      bg.style.pointerEvents = 'none'
    }
    applyStrokePreset()
    rememberRelGrab(svg)
    syncPaperSize()
    fitToFrame()
  })
}

watch(
  () => props.svgSource,
  (v) => {
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

function nodeById(svg, id) {
  if (!svg || !id) return null
  return svg.querySelector(`.er-node[data-id="${CSS.escape(id)}"]`)
}

function indexNodes(svg) {
  const byId = new Map()
  svg.querySelectorAll('.er-node').forEach((g) => {
    const c = nodeCenter(g)
    byId.set(c.id, c)
  })
  return byId
}

/** 端点是否贴在该节点边上（折线中间点不算）。 */
function pinNode(x, y, fromId, toId, byId) {
  let best = null
  let bestD = 14
  for (const id of [fromId, toId]) {
    const n = byId.get(id)
    if (!n) continue
    const edge = shapeEdge(n, x, y)
    const d = Math.hypot(edge.x - x, edge.y - y)
    if (d < bestD) {
      bestD = d
      best = id
    }
  }
  return best
}

/** 菱形相对两端实体中点的偏移，拖实体时保持这个错开。 */
function rememberRelGrab(svg) {
  relGrab.clear()
  if (!svg) return
  const byId = indexNodes(svg)
  svg.querySelectorAll('.er-node[data-kind="rel"]').forEach((g) => {
    const left = g.getAttribute('data-left')
    const right = g.getAttribute('data-right')
    const id = g.getAttribute('data-id')
    const a = byId.get(left)
    const b = byId.get(right)
    const c = byId.get(id)
    if (!a || !b || !c || !id) return
    relGrab.set(id, {
      dx: c.x - (a.x + b.x) / 2,
      dy: c.y - (a.y + b.y) / 2,
    })
  })
}

function syncRelGrab(svg, relId) {
  const g = nodeById(svg, relId)
  if (!g) return
  const left = g.getAttribute('data-left')
  const right = g.getAttribute('data-right')
  const a = nodeById(svg, left)
  const b = nodeById(svg, right)
  if (!a || !b) return
  const ca = nodeCenter(a)
  const cb = nodeCenter(b)
  const c = nodeCenter(g)
  relGrab.set(relId, {
    dx: c.x - (ca.x + cb.x) / 2,
    dy: c.y - (ca.y + cb.y) / 2,
  })
}

/** 实体挪了之后，相连菱形落到新中点（加上按下时记下的错开）。 */
function diamondDeltas(svg, oldBy, entityDelta, relNodes) {
  const out = new Map()
  const list = relNodes || svg.querySelectorAll('.er-node[data-kind="rel"]')
  list.forEach((g) => {
    const left = g.getAttribute('data-left')
    const right = g.getAttribute('data-right')
    const rid = g.getAttribute('data-id')
    if (!left || !right || !rid) return
    const dl = entityDelta.get(left) || { ddx: 0, ddy: 0 }
    const dr = entityDelta.get(right) || { ddx: 0, ddy: 0 }
    if (!dl.ddx && !dl.ddy && !dr.ddx && !dr.ddy) return
    const a = oldBy.get(left)
    const b = oldBy.get(right)
    const rel = oldBy.get(rid)
    if (!a || !b || !rel) return
    const grab = relGrab.get(rid) || { dx: 0, dy: 0 }
    const nx = (a.x + dl.ddx + b.x + dr.ddx) / 2 + grab.dx
    const ny = (a.y + dl.ddy + b.y + dr.ddy) / 2 + grab.dy
    out.set(rid, { ddx: nx - rel.x, ddy: ny - rel.y })
  })
  return out
}

/** 只移动贴在被挪节点上的端点，折线中间点保持原路径。 */
function shiftEndpoints(svg, oldBy, delta) {
  const movedPts = []
  svg.querySelectorAll('line.er-edge').forEach((line) => {
    const fromId = line.getAttribute('data-from')
    const toId = line.getAttribute('data-to')
    for (const [attrX, attrY] of [['x1', 'y1'], ['x2', 'y2']]) {
      const x = Number(line.getAttribute(attrX))
      const y = Number(line.getAttribute(attrY))
      const nid = pinNode(x, y, fromId, toId, oldBy)
      if (!nid || !delta.has(nid)) continue
      const d = delta.get(nid)
      line.setAttribute(attrX, (x + d.ddx).toFixed(1))
      line.setAttribute(attrY, (y + d.ddy).toFixed(1))
      movedPts.push({ x, y, ddx: d.ddx, ddy: d.ddy })
    }
  })
  svg.querySelectorAll('text.er-card').forEach((txt) => {
    const x = Number(txt.getAttribute('x'))
    const y = Number(txt.getAttribute('y'))
    let best = null
    let bestD = 40
    for (const p of movedPts) {
      const dist = Math.hypot(p.x - x, p.y - y)
      if (dist < bestD) {
        bestD = dist
        best = p
      }
    }
    if (!best) return
    txt.setAttribute('x', (x + best.ddx).toFixed(1))
    txt.setAttribute('y', (y + best.ddy).toFixed(1))
  })
}

function applyDelta(svg, delta) {
  if (!svg || !delta.size) return
  const oldBy = indexNodes(svg)
  shiftEndpoints(svg, oldBy, delta)
  for (const [id, d] of delta) {
    if (!d.ddx && !d.ddy) continue
    bumpOffset(id, d.ddx, d.ddy)
    const g = nodeById(svg, id)
    if (g) setNodeTransform(g, id)
  }
}

function translateFigure(svg, dx, dy) {
  if (!svg || (!dx && !dy)) return
  svg.querySelectorAll('.er-node').forEach((g) => {
    const id = g.getAttribute('data-id')
    bumpOffset(id, dx, dy)
    setNodeTransform(g, id)
  })
  svg.querySelectorAll('line.er-edge').forEach((line) => {
    for (const [attrX, attrY] of [['x1', 'y1'], ['x2', 'y2']]) {
      line.setAttribute(attrX, (Number(line.getAttribute(attrX)) + dx).toFixed(1))
      line.setAttribute(attrY, (Number(line.getAttribute(attrY)) + dy).toFixed(1))
    }
  })
  svg.querySelectorAll('text.er-card').forEach((txt) => {
    txt.setAttribute('x', (Number(txt.getAttribute('x')) + dx).toFixed(1))
    txt.setAttribute('y', (Number(txt.getAttribute('y')) + dy).toFixed(1))
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

const CANVAS_PAD = 48
const CANVAS_MAX_W = 2200
const CANVAS_MAX_H = 1600

function nodeExtent(g) {
  const c = nodeCenter(g)
  const shape = g.getAttribute('data-shape') || 'rect'
  let hw = 40
  let hh = 22
  if (shape === 'ellipse') {
    hw = Number(g.getAttribute('data-rx')) || 28
    hh = Number(g.getAttribute('data-ry')) || 14
  } else {
    hw = Number(g.getAttribute('data-hw')) || 40
    hh = Number(g.getAttribute('data-hh')) || 22
  }
  return { minX: c.x - hw, maxX: c.x + hw, minY: c.y - hh, maxY: c.y + hh }
}

function clampNodesToCanvas(svg, w, h) {
  const xMax = w - CANVAS_PAD
  const yMax = h - CANVAS_PAD
  const oldBy = indexNodes(svg)
  const delta = new Map()
  svg.querySelectorAll('.er-node').forEach((g) => {
    const e = nodeExtent(g)
    let ddx = 0
    let ddy = 0
    if (e.minX < CANVAS_PAD) ddx = CANVAS_PAD - e.minX
    else if (e.maxX > xMax) ddx = xMax - e.maxX
    if (e.minY < CANVAS_PAD) ddy = CANVAS_PAD - e.minY
    else if (e.maxY > yMax) ddy = yMax - e.maxY
    if (!ddx && !ddy) return
    const id = g.getAttribute('data-id')
    if (g.getAttribute('data-kind') === 'rel') return
    delta.set(id, { ddx, ddy })
  })
  if (!delta.size) return
  const entDelta = new Map()
  for (const [id, d] of delta) {
    const g = nodeById(svg, id)
    if (g && g.getAttribute('data-kind') === 'entity') entDelta.set(id, d)
  }
  for (const [id, d] of diamondDeltas(svg, oldBy, entDelta)) {
    delta.set(id, d)
  }
  applyDelta(svg, delta)
}

/** 四向扩画布，但有上限；到顶后卡住，不再无限变大 */
function expandCanvasToFit(svg) {
  let minX = Infinity
  let minY = Infinity
  let maxX = -Infinity
  let maxY = -Infinity
  svg.querySelectorAll('.er-node').forEach((g) => {
    const e = nodeExtent(g)
    minX = Math.min(minX, e.minX)
    maxX = Math.max(maxX, e.maxX)
    minY = Math.min(minY, e.minY)
    maxY = Math.max(maxY, e.maxY)
  })
  if (!Number.isFinite(minX)) return

  let shiftX = 0
  let shiftY = 0
  if (minX < CANVAS_PAD) {
    const want = CANVAS_PAD - minX
    if (maxX + want + CANVAS_PAD <= CANVAS_MAX_W) shiftX = want
  }
  if (minY < CANVAS_PAD) {
    const want = CANVAS_PAD - minY
    if (maxY + want + CANVAS_PAD <= CANVAS_MAX_H) shiftY = want
  }

  if (shiftX || shiftY) {
    translateFigure(svg, shiftX, shiftY)
    maxX += shiftX
    maxY += shiftY
  }

  const { w, h } = svgSize(svg)
  const nw = Math.min(Math.max(Math.ceil(maxX + CANVAS_PAD), w), CANVAS_MAX_W)
  const nh = Math.min(Math.max(Math.ceil(maxY + CANVAS_PAD), h), CANVAS_MAX_H)
  if (nw !== w || nh !== h) {
    svg.setAttribute('width', String(nw))
    svg.setAttribute('height', String(nh))
    svg.setAttribute('viewBox', `0 0 ${nw} ${nh}`)
  }
  clampNodesToCanvas(svg, nw, nh)
  syncPaperSize()
}

/** 拖到预览窗口边缘时跟手平移（右/下也适用，不只是左上） */
function autoPanWhileDrag(clientX, clientY) {
  const frame = frameRef.value
  if (!frame) return
  const rect = frame.getBoundingClientRect()
  const margin = 36
  const step = 14
  let dx = 0
  let dy = 0
  if (clientX <= rect.left + margin) dx = step
  else if (clientX >= rect.right - margin) dx = -step
  if (clientY <= rect.top + margin) dy = step
  else if (clientY >= rect.bottom - margin) dy = -step
  if (dx || dy) {
    panX.value += dx
    panY.value += dy
  }
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
    pendingDX = 0
    pendingDY = 0
    grabX = 0
    grabY = 0
    grabOrigin = nodeCenter(node)
    const kind = node.getAttribute('data-kind')
    const id = node.getAttribute('data-id')
    if (kind === 'entity') {
      const svg = getSvg()
      svg?.querySelectorAll('.er-node[data-parent]').forEach((g) => {
        if (g.getAttribute('data-parent') === id) dragFollowers.push(g)
      })
    }
    captureDragBindings(getSvg(), id, kind)
    dragMoved = false
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

function captureDragBindings(svg, rootId, kind) {
  dragPins = []
  dragCards = []
  dragNodeEls = new Map()
  dragRelEls = []
  if (!svg || !rootId) return
  const involved = new Set([rootId])
  svg.querySelectorAll('.er-node').forEach((g) => {
    const id = g.getAttribute('data-id')
    if (id) dragNodeEls.set(id, g)
  })
  if (kind === 'entity') {
    for (const g of dragFollowers) {
      const fid = g.getAttribute('data-id')
      if (fid) involved.add(fid)
    }
    svg.querySelectorAll('.er-node[data-kind="rel"]').forEach((g) => {
      const rid = g.getAttribute('data-id')
      if (!rid) return
      dragRelEls.push(g)
      const left = g.getAttribute('data-left')
      const right = g.getAttribute('data-right')
      if (left === rootId || right === rootId) involved.add(rid)
    })
  }
  const byId = indexNodes(svg)
  const seeds = []
  svg.querySelectorAll('line.er-edge').forEach((line) => {
    const fromId = line.getAttribute('data-from')
    const toId = line.getAttribute('data-to')
    for (const [attrX, attrY] of [['x1', 'y1'], ['x2', 'y2']]) {
      const x = Number(line.getAttribute(attrX))
      const y = Number(line.getAttribute(attrY))
      const nid = pinNode(x, y, fromId, toId, byId)
      if (!nid || !involved.has(nid)) continue
      dragPins.push({ line, attrX, attrY, nodeId: nid, x, y })
      seeds.push({ x, y, nodeId: nid })
    }
  })
  svg.querySelectorAll('text.er-card').forEach((txt) => {
    const x = Number(txt.getAttribute('x'))
    const y = Number(txt.getAttribute('y'))
    let best = null
    let bestD = 40
    for (const p of seeds) {
      const dist = Math.hypot(p.x - x, p.y - y)
      if (dist < bestD) {
        bestD = dist
        best = p
      }
    }
    if (best) dragCards.push({ el: txt, nodeId: best.nodeId, x, y })
  })
}

function centersFromCache() {
  const byId = new Map()
  for (const [id, g] of dragNodeEls) byId.set(id, nodeCenter(g))
  return byId
}

function applyDragDelta(delta) {
  for (const pin of dragPins) {
    const d = delta.get(pin.nodeId)
    if (!d || (!d.ddx && !d.ddy)) continue
    pin.x += d.ddx
    pin.y += d.ddy
    pin.line.setAttribute(pin.attrX, pin.x.toFixed(1))
    pin.line.setAttribute(pin.attrY, pin.y.toFixed(1))
  }
  for (const card of dragCards) {
    const d = delta.get(card.nodeId)
    if (!d || (!d.ddx && !d.ddy)) continue
    card.x += d.ddx
    card.y += d.ddy
    card.el.setAttribute('x', card.x.toFixed(1))
    card.el.setAttribute('y', card.y.toFixed(1))
  }
  for (const [id, d] of delta) {
    if (!d.ddx && !d.ddy) continue
    bumpOffset(id, d.ddx, d.ddy)
    const g = dragNodeEls.get(id)
    if (g) setNodeTransform(g, id)
  }
}

function flushDragFrame() {
  dragFrame = 0
  const node = dragNode.value
  const svg = getSvg()
  let ddx = pendingDX
  let ddy = pendingDY
  pendingDX = 0
  pendingDY = 0
  if (!node || !svg) return
  grabX += ddx
  grabY += ddy
  if (showGrid.value && grabOrigin) {
    const c = nodeCenter(node)
    ddx = snapGrid(grabOrigin.x + grabX) - c.x
    ddy = snapGrid(grabOrigin.y + grabY) - c.y
  }
  if (!ddx && !ddy) return
  const id = node.getAttribute('data-id')
  const kind = node.getAttribute('data-kind')
  const oldBy = centersFromCache()
  const delta = new Map()
  delta.set(id, { ddx, ddy })
  if (kind === 'entity') {
    for (const g of dragFollowers) {
      const fid = g.getAttribute('data-id')
      if (fid) delta.set(fid, { ddx, ddy })
    }
    for (const [rid, d] of diamondDeltas(svg, oldBy, new Map([[id, { ddx, ddy }]]), dragRelEls)) {
      delta.set(rid, d)
    }
  }
  applyDragDelta(delta)
  dragMoved = true
  if (kind === 'rel') syncRelGrab(svg, id)
}

function onPointerMove(e) {
  if (dragNode.value) {
    const ddx = (e.clientX - dragLastX) / scale.value
    const ddy = (e.clientY - dragLastY) / scale.value
    dragLastX = e.clientX
    dragLastY = e.clientY
    if (ddx || ddy) {
      pendingDX += ddx
      pendingDY += ddy
      if (!dragFrame) dragFrame = requestAnimationFrame(flushDragFrame)
    }
    autoPanWhileDrag(e.clientX, e.clientY)
    return
  }
  if (!panning.value) return
  panX.value += e.clientX - panLastX
  panY.value += e.clientY - panLastY
  panLastX = e.clientX
  panLastY = e.clientY
}

function orient2(ax, ay, bx, by, cx, cy) {
  return (by - ay) * (cx - bx) - (bx - ax) * (cy - by)
}

function segsCross(a, b) {
  const [ax, ay, bx, by] = a
  const [cx, cy, dx, dy] = b
  const key = (x, y) => `${x.toFixed(1)},${y.toFixed(1)}`
  const pa = new Set([key(ax, ay), key(bx, by)])
  if (pa.has(key(cx, cy)) || pa.has(key(dx, dy))) return false
  const o1 = orient2(ax, ay, bx, by, cx, cy)
  const o2 = orient2(ax, ay, bx, by, dx, dy)
  const o3 = orient2(cx, cy, dx, dy, ax, ay)
  const o4 = orient2(cx, cy, dx, dy, bx, by)
  return o1 * o2 < 0 && o3 * o4 < 0
}

function pointInNode(n, x, y) {
  const shape = n.g.getAttribute('data-shape') || 'rect'
  const pad = 3
  if (shape === 'ellipse') {
    const rx = (Number(n.g.getAttribute('data-rx')) || 28) + pad
    const ry = (Number(n.g.getAttribute('data-ry')) || 14) + pad
    const nx = (x - n.x) / rx
    const ny = (y - n.y) / ry
    return nx * nx + ny * ny < 1
  }
  const hw = (Number(n.g.getAttribute('data-hw')) || 40) + pad
  const hh = (Number(n.g.getAttribute('data-hh')) || 22) + pad
  if (shape === 'diamond') {
    return Math.abs(x - n.x) / hw + Math.abs(y - n.y) / hh < 1
  }
  return Math.abs(x - n.x) < hw && Math.abs(y - n.y) < hh
}

function segHitsNode(n, seg) {
  const [x1, y1, x2, y2] = seg
  for (let i = 1; i < 8; i += 1) {
    const t = i / 8
    if (pointInNode(n, x1 + (x2 - x1) * t, y1 + (y2 - y1) * t)) return true
  }
  return false
}

function relEnds(svg, g) {
  const leftAttr = g.getAttribute('data-left')
  const rightAttr = g.getAttribute('data-right')
  if (leftAttr && rightAttr) return [leftAttr, rightAttr]
  const relId = g.getAttribute('data-id')
  const ends = []
  svg.querySelectorAll('line.er-edge').forEach((line) => {
    const f = line.getAttribute('data-from')
    const t = line.getAttribute('data-to')
    const other = f === relId ? t : t === relId ? f : null
    if (other && String(other).startsWith('entity:') && !ends.includes(other)) ends.push(other)
  })
  if (ends.length >= 2) return [ends[0], ends[1]]
  return [leftAttr, rightAttr]
}

function relLineGroups(svg, leftId, rightId, relId) {
  const left = []
  const right = []
  svg.querySelectorAll('line.er-edge').forEach((line) => {
    const f = line.getAttribute('data-from')
    const t = line.getAttribute('data-to')
    const hit = (a, b) => (f === a && t === b) || (f === b && t === a)
    if (hit(leftId, relId)) left.push(line)
    else if (hit(rightId, relId)) right.push(line)
  })
  return { left, right }
}

function readSeg(line) {
  return [
    Number(line.getAttribute('x1')),
    Number(line.getAttribute('y1')),
    Number(line.getAttribute('x2')),
    Number(line.getAttribute('y2')),
  ]
}

function otherSegs(svg, relId, leftId, rightId) {
  const segs = []
  svg.querySelectorAll('line.er-edge').forEach((line) => {
    const f = line.getAttribute('data-from')
    const t = line.getAttribute('data-to')
    const mine = (f === leftId && t === relId) || (f === relId && t === leftId)
      || (f === rightId && t === relId) || (f === relId && t === rightId)
    if (mine) return
    if (String(f).startsWith('attr:') || String(t).startsWith('attr:')) return
    segs.push(readSeg(line))
  })
  return segs
}

function writeRelSegment(lines, fromId, toId, x1, y1, x2, y2) {
  if (!lines.length) return
  const keep = lines[0]
  for (const extra of lines.slice(1)) extra.remove()
  keep.setAttribute('data-from', fromId)
  keep.setAttribute('data-to', toId)
  keep.setAttribute('x1', x1.toFixed(1))
  keep.setAttribute('y1', y1.toFixed(1))
  keep.setAttribute('x2', x2.toFixed(1))
  keep.setAttribute('y2', y2.toFixed(1))
}

function placeCard(svg, fromId, toId, ax, ay, bx, by) {
  svg.querySelectorAll('text.er-card').forEach((txt) => {
    const f = txt.getAttribute('data-from')
    const t = txt.getAttribute('data-to')
    if (!((f === fromId && t === toId) || (f === toId && t === fromId))) return
    const px = ax * 0.65 + bx * 0.35
    const py = ay * 0.65 + by * 0.35
    const dx = bx - ax
    const dy = by - ay
    const L = Math.hypot(dx, dy) || 1
    txt.setAttribute('data-from', fromId)
    txt.setAttribute('data-to', toId)
    txt.setAttribute('x', (px - (dy / L) * 12).toFixed(1))
    txt.setAttribute('y', (py + (dx / L) * 12).toFixed(1))
  })
}

function setNodeCenter(g, x, y) {
  const id = g.getAttribute('data-id')
  const bx = Number(g.getAttribute('data-cx')) || 0
  const by = Number(g.getAttribute('data-cy')) || 0
  offsets.set(id, { dx: x - bx, dy: y - by })
  setNodeTransform(g, id)
}

function routeAt(a, b, rel, cx, cy) {
  const ghost = { ...rel, x: cx, y: cy }
  const pA = shapeEdge(a, cx, cy)
  const pR1 = shapeEdge(ghost, a.x, a.y)
  const pR2 = shapeEdge(ghost, b.x, b.y)
  const pB = shapeEdge(b, cx, cy)
  return {
    pA,
    pR1,
    pR2,
    pB,
    segs: [
      [pA.x, pA.y, pR1.x, pR1.y],
      [pR2.x, pR2.y, pB.x, pB.y],
    ],
  }
}

function scoreRoute(route, cx, cy, midX, midY, obstacles, frozen) {
  let pen = Math.hypot(cx - midX, cy - midY) * 0.01
  if (obstacles.some((o) => pointInNode(o, cx, cy))) pen += 100
  for (const seg of route.segs) {
    for (const o of obstacles) {
      if (segHitsNode(o, seg)) pen += 100
    }
    for (const f of frozen) {
      if (segsCross(seg, f)) pen += 100
    }
  }
  return pen
}

function commitRoute(svg, g, relId, leftId, rightId, a, b, cx, cy, route) {
  const midX = (a.x + b.x) / 2
  const midY = (a.y + b.y) / 2
  setNodeCenter(g, cx, cy)
  relGrab.set(relId, { dx: cx - midX, dy: cy - midY })
  const groups = relLineGroups(svg, leftId, rightId, relId)
  const removed = groups.left.length > 1 || groups.right.length > 1
  writeRelSegment(groups.left, leftId, relId, route.pA.x, route.pA.y, route.pR1.x, route.pR1.y)
  writeRelSegment(groups.right, relId, rightId, route.pR2.x, route.pR2.y, route.pB.x, route.pB.y)
  placeCard(svg, leftId, relId, route.pA.x, route.pA.y, route.pR1.x, route.pR1.y)
  placeCard(svg, rightId, relId, route.pB.x, route.pB.y, route.pR2.x, route.pR2.y)
  return removed
}

/** 松手后：实体不动。刚拖过的那颗菱形留在松手处，其余联系再避开交叉。 */
function rerouteAllRelations(svg, pinRelId = '') {
  const usable = []
  svg.querySelectorAll('.er-node[data-kind="rel"]').forEach((g) => {
    const [leftId, rightId] = relEnds(svg, g)
    const relId = g.getAttribute('data-id')
    if (leftId && rightId && relId) usable.push({ g, relId, leftId, rightId })
  })
  if (!usable.length) return
  const byId = indexNodes(svg)
  const lineNodes = [...svg.querySelectorAll('line.er-edge')]
  const offsetsTry = [0, 48, -48, 96, -96, 144, -144, 208, -208, 288, -288, 400, -400]

  function liveLines() {
    return lineNodes.filter((line) => line.isConnected)
  }

  function frozenFor(item) {
    const segs = []
    for (const line of liveLines()) {
      const f = line.getAttribute('data-from')
      const t = line.getAttribute('data-to')
      const mine = (f === item.leftId && t === item.relId) || (f === item.relId && t === item.leftId)
        || (f === item.rightId && t === item.relId) || (f === item.relId && t === item.rightId)
      if (mine || String(f).startsWith('attr:') || String(t).startsWith('attr:')) continue
      segs.push(readSeg(line))
    }
    return segs
  }

  function collapseAt(item, rel) {
    const route = routeAt(byId.get(item.leftId), byId.get(item.rightId), rel, rel.x, rel.y)
    return commitRoute(svg, item.g, item.relId, item.leftId, item.rightId, byId.get(item.leftId), byId.get(item.rightId), rel.x, rel.y, route)
  }

  for (const item of usable) {
    const rel = byId.get(item.relId)
    const a = byId.get(item.leftId)
    const b = byId.get(item.rightId)
    if (!rel || !a || !b) continue
    collapseAt(item, rel)
  }

  for (let pass = 0; pass < 3; pass += 1) {
    let dirty = false
    for (const item of usable) {
      if (item.relId === pinRelId) continue
      const a = byId.get(item.leftId)
      const b = byId.get(item.rightId)
      const rel = byId.get(item.relId)
      if (!a || !b || !rel) continue
      const dx = b.x - a.x
      const dy = b.y - a.y
      const L = Math.hypot(dx, dy) || 1
      const nx = -dy / L
      const ny = dx / L
      const midX = (a.x + b.x) / 2
      const midY = (a.y + b.y) / 2
      const obstacles = []
      for (const n of byId.values()) {
        if (n.id !== item.leftId && n.id !== item.rightId && n.id !== item.relId) obstacles.push(n)
      }
      const frozen = frozenFor(item)
      const candidates = [{ x: rel.x, y: rel.y }]
      for (const off of offsetsTry) candidates.push({ x: midX + nx * off, y: midY + ny * off })
      let best = null
      for (const cand of candidates) {
        const route = routeAt(a, b, rel, cand.x, cand.y)
        const pen = scoreRoute(route, cand.x, cand.y, midX, midY, obstacles, frozen)
        if (!best || pen < best.pen) best = { pen, x: cand.x, y: cand.y, route }
        if (pen < 1) break
      }
      if (!best) continue
      if (Math.hypot(best.x - rel.x, best.y - rel.y) <= 0.8) continue
      dirty = true
      rel.x = best.x
      rel.y = best.y
      commitRoute(svg, item.g, item.relId, item.leftId, item.rightId, a, b, best.x, best.y, best.route)
    }
    if (!dirty) break
  }
}

function commitView() {
  const svg = getSvg()
  if (!svg || !viewDirty) return
  rerouteAllRelations(svg, lastPinRel)
  expandCanvasToFit(svg)
  viewDirty = false
  lastPinRel = ''
  emit('save-view', {
    mode: loadedMode,
    entity: loadedMode === 'part' ? loadedEntity : '',
    svg: serializeSvg(),
  })
}

function onPointerUp(e) {
  if (e.type === 'pointerleave' && frameRef.value?.hasPointerCapture?.(e.pointerId)) return
  if (dragFrame) {
    cancelAnimationFrame(dragFrame)
    dragFrame = 0
    flushDragFrame()
  }
  if (dragNode.value) {
    const kind = dragNode.value.getAttribute('data-kind')
    const movedId = dragNode.value.getAttribute('data-id')
    const moved = dragMoved
    dragNode.value.classList.remove('er-node-active')
    dragNode.value = null
    dragFollowers = []
    dragPins = []
    dragCards = []
    dragRelEls = []
    dragNodeEls = new Map()
    if (moved) {
      viewDirty = true
      lastPinRel = kind === 'rel' ? (movedId || '') : ''
      commitView()
    }
    dragMoved = false
  }
  panning.value = false
  try {
    e.currentTarget?.releasePointerCapture?.(e.pointerId)
  } catch {
    /* ignore */
  }
}

onBeforeUnmount(() => {
  if (dragFrame) {
    cancelAnimationFrame(dragFrame)
    dragFrame = 0
    flushDragFrame()
  }
  commitView()
})

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
  fitToFrame()
}

function fitToFrame() {
  const frame = frameRef.value
  const svg = getSvg()
  if (!frame || !svg) {
    scale.value = 1
    panX.value = 0
    panY.value = 0
    return
  }
  const { w, h } = svgSize(svg)
  const fw = frame.clientWidth || 1
  const fh = frame.clientHeight || 1
  const next = clampScale(Math.min(fw / w, fh / h) * 0.92)
  scale.value = next
  panX.value = (fw - w * next) / 2
  panY.value = (fh - h * next) / 2
}

function serializeSvg() {
  const svg = getSvg()
  if (!svg) return ''
  applyOffsetsToDom()
  applyStrokePreset()
  const clone = svg.cloneNode(true)
  clone.querySelectorAll('.er-hit').forEach((el) => el.remove())
  clone.querySelectorAll('.er-node-active').forEach((el) => el.classList.remove('er-node-active'))
  clone.querySelectorAll('[style]').forEach((el) => el.removeAttribute('style'))
  clone.querySelectorAll('[data-base-sw]').forEach((el) => el.removeAttribute('data-base-sw'))
  // 导出白底（预览里纸面透明，避免夜间一大块黑底）
  const paper = clone.querySelector('.er-paper')
  if (paper) paper.setAttribute('fill', '#ffffff')
  const xml = new XMLSerializer().serializeToString(clone)
  if (xml.startsWith('<?xml')) return xml
  return `<?xml version="1.0" encoding="UTF-8"?>\n${xml}`
}

function svgSize(svg) {
  const vb = (svg.getAttribute('viewBox') || '').trim().split(/[\s,]+/).map(Number)
  let w = Number(svg.getAttribute('width')) || 0
  let h = Number(svg.getAttribute('height')) || 0
  if ((!w || !h) && vb.length === 4) {
    w = vb[2]
    h = vb[3]
  }
  return { w: w || 800, h: h || 600 }
}

function rasterizePng(pixelRatio = PNG_SCALE) {
  const xml = serializeSvg()
  if (!xml) return Promise.reject(new Error('empty svg'))
  const svg = getSvg()
  const { w, h } = svgSize(svg)
  const blob = new Blob([xml], { type: 'image/svg+xml;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => {
      try {
        const canvas = document.createElement('canvas')
        canvas.width = Math.max(1, Math.round(w * pixelRatio))
        canvas.height = Math.max(1, Math.round(h * pixelRatio))
        const ctx = canvas.getContext('2d')
        ctx.fillStyle = '#ffffff'
        ctx.fillRect(0, 0, canvas.width, canvas.height)
        ctx.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0)
        ctx.drawImage(img, 0, 0, w, h)
        canvas.toBlob(
          (png) => {
            URL.revokeObjectURL(url)
            if (!png) reject(new Error('toBlob failed'))
            else resolve(png)
          },
          'image/png',
        )
      } catch (err) {
        URL.revokeObjectURL(url)
        reject(err)
      }
    }
    img.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('svg load failed'))
    }
    img.src = url
  })
}

function triggerDownload(blob, name) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = name
  a.click()
  URL.revokeObjectURL(url)
}

function downloadSvg() {
  const xml = serializeSvg()
  if (!xml) {
    message.error('无法导出矢量图')
    return
  }
  triggerDownload(new Blob([xml], { type: 'image/svg+xml;charset=utf-8' }), `${fileBase.value}.svg`)
}

async function downloadPng() {
  if (busy.value) return
  busy.value = true
  try {
    const png = await rasterizePng()
    triggerDownload(png, `${fileBase.value}.png`)
    message.success('已下载 PNG，可直接插入 Word')
  } catch {
    message.error('导出 PNG 失败')
  } finally {
    busy.value = false
  }
}

async function copyPng() {
  if (busy.value) return
  busy.value = true
  try {
    const png = await rasterizePng()
    if (!navigator.clipboard?.write || typeof ClipboardItem === 'undefined') {
      triggerDownload(png, `${fileBase.value}.png`)
      message.warning('当前环境不支持复制图片，已改为下载 PNG')
      return
    }
    try {
      await navigator.clipboard.write([
        new ClipboardItem({ 'image/png': Promise.resolve(png) }),
      ])
      message.success('已复制图片，可在 Word 中粘贴')
    } catch {
      triggerDownload(png, `${fileBase.value}.png`)
      message.warning('复制失败，已改为下载 PNG')
    }
  } catch {
    message.error('复制图片失败')
  } finally {
    busy.value = false
  }
}

defineExpose({ serializeSvg, downloadSvg, downloadPng, copyPng, resetView })
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
.er-hint {
  margin: 0;
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
  position: relative;
  will-change: transform;
}
.er-grid {
  position: absolute;
  left: 0;
  top: 0;
  z-index: 0;
  pointer-events: none;
}
.er-svg-host {
  position: relative;
  z-index: 1;
}
.er-svg-host :deep(svg) {
  display: block;
}
.er-canvas :deep(.er-svg-host svg) {
  display: block;
  max-width: none;
  height: auto;
  overflow: visible;
}
/* 预览纸面透明，画布跟着内容走；导出时再填白 */
.er-canvas :deep(.er-paper) {
  fill: transparent !important;
}
.er-canvas :deep(.er-node-active) rect,
.er-canvas :deep(.er-node-active) ellipse,
.er-canvas :deep(.er-node-active) polygon {
  stroke: #2563eb;
  stroke-width: 2;
}

/* 夜间：只反相图元，不再出现整页大黑底 */
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
