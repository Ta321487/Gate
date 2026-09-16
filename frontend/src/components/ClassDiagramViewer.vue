<template>
  <div class="cls-viewer" :class="{ 'is-dark': isDark }">
    <div class="cls-toolbar row mb-12">
      <div class="cls-zoom-btns row">
        <n-radio-group
          v-if="displayModes.length"
          :value="displayMode"
          size="small"
          class="cls-mode"
          @update:value="onDisplayMode"
        >
          <n-radio-button v-for="m in displayModes" :key="m.id" :value="m.id">
            {{ m.label }}
          </n-radio-button>
        </n-radio-group>
        <n-button size="small" @click="zoomOut">缩小</n-button>
        <span class="cls-zoom-label">{{ Math.round(scale * 100) }}%</span>
        <n-button size="small" @click="zoomIn">放大</n-button>
        <n-button size="small" @click="resetView">重置视口</n-button>
        <n-button size="small" :loading="loading" @click="onReload">复位布局</n-button>
        <n-button size="small" type="primary" :loading="busy" @click="copyPng">复制图片</n-button>
        <n-button size="small" type="primary" secondary :loading="busy" @click="downloadPng">下载 PNG</n-button>
        <n-button size="small" quaternary @click="downloadSvg">下载矢量源</n-button>
      </div>
    </div>
  <p class="small muted cls-hint mb-8">
    论文口径：三栏类框（+ 公有 / # 保护 / - 私有）· 六种关系线 · 同图零交叉（拖中只动相连线，松手回拉精炼）· 「论文示例 / 代码全量」
  </p>
    <p v-if="sourceNote" class="small muted cls-hint mb-8">{{ sourceNote }}</p>
    <p v-if="evidenceNote" class="small muted cls-hint mb-8">{{ evidenceNote }}</p>
    <div
      ref="frameRef"
      class="cls-frame"
      :class="{ 'is-dragging-node': !!dragNode, 'is-panning': panning }"
      @wheel.prevent="onWheel"
      @pointerdown="onPointerDown"
      @pointermove="onPointerMove"
      @pointerup="onPointerUp"
      @pointercancel="onPointerUp"
    >
      <ContentLoading v-if="loading && !svgSource" :rows="1" block compact />
      <div v-else class="cls-canvas" :style="canvasStyle" v-html="svgHtml" />
    </div>
  </div>
</template>

<script setup>
/**
 * 对齐 ErDiagramViewer：后端出 SVG，前端拖 .uml-node，导出序列化活 DOM。
 */
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { message } from '../api'
import { isDark } from '../theme'
import ContentLoading from './ContentLoading.vue'

const props = defineProps({
  svgSource: { type: String, default: '' },
  downloadName: { type: String, default: 'classes' },
  sourceNote: { type: String, default: '' },
  evidenceNote: { type: String, default: '' },
  loading: { type: Boolean, default: false },
  displayMode: { type: String, default: 'sample' },
  displayModes: { type: Array, default: () => [] },
})

const emit = defineEmits(['save-layout', 'reset-layout', 'update:displayMode'])

function onDisplayMode(v) {
  emit('update:displayMode', v)
}

const PNG_SCALE = 3
const CANVAS_PAD = 64
const CANVAS_MAX_W = 6000
const CANVAS_MAX_H = 4500
const EDGE_GROW = 80 // 拖近边缘时多留一截，避免贴边才扩
const SCALE_MIN = 0.2
const SCALE_MAX = 4
const SCALE_STEP = 0.15
/** 默认适配留白：外绕折线 + marker 不被 frame overflow 裁掉 */
const FIT_MARGIN = 0.72

const frameRef = ref(null)
const svgHtml = ref('')
const scale = ref(1)
const panX = ref(0)
const panY = ref(0)
const panning = ref(false)
const dragNode = ref(null)
const busy = ref(false)
const didFitView = ref(false)
/** 用户手动缩放/平移后，不再因弹窗 resize 强行 fit */
let userAdjustedView = false
let fitRetries = 0
let resizeObs = null
let frameLastW = 0
let frameLastH = 0

/** nodeId -> { dx, dy } */
const offsets = new Map()

let panLastX = 0
let panLastY = 0
let dragLastX = 0
let dragLastY = 0

const canvasStyle = computed(() => ({
  transform: `translate(${panX.value}px, ${panY.value}px) scale(${scale.value})`,
  transformOrigin: '0 0',
}))

const fileBase = computed(
  () => String(props.downloadName || 'classes').replace(/\.(svg|png)$/i, '') || 'classes',
)

function clampScale(s) {
  return Math.min(SCALE_MAX, Math.max(SCALE_MIN, s))
}

function getSvg() {
  return frameRef.value?.querySelector('svg') || null
}

function parseSvg(raw) {
  return (raw || '').replace(/^<\?xml[^>]*>\s*/i, '')
}

function nodeCenter(g) {
  const id = g.getAttribute('data-id')
  const o = offsets.get(id) || { dx: 0, dy: 0 }
  const cx = Number(g.getAttribute('data-cx')) || 0
  const cy = Number(g.getAttribute('data-cy')) || 0
  return { x: cx + o.dx, y: cy + o.dy, g, id }
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


/** 直角折线绕障（框不穿；候选再与既有边比交叉，尽量零交叉） */
function segHitsBox(x0, y0, x1, y1, bx, by, bw, bh, pad = 6) {
  const left = bx - pad
  const right = bx + bw + pad
  const top = by - pad
  const bottom = by + bh + pad
  if (Math.abs(y0 - y1) < 1e-6) {
    const y = y0
    if (y <= top || y >= bottom) return false
    const lo = Math.min(x0, x1)
    const hi = Math.max(x0, x1)
    return lo < right - 1 && hi > left + 1
  }
  if (Math.abs(x0 - x1) < 1e-6) {
    const x = x0
    if (x <= left || x >= right) return false
    const lo = Math.min(y0, y1)
    const hi = Math.max(y0, y1)
    return lo < bottom - 1 && hi > top + 1
  }
  return false
}

function pathObstacleHits(pts, obstacles, ignore) {
  let hits = 0
  for (let i = 0; i < pts.length - 1; i++) {
    const [x0, y0] = pts[i]
    const [x1, y1] = pts[i + 1]
    for (const o of obstacles) {
      if (ignore.has(o.id)) continue
      if (segHitsBox(x0, y0, x1, y1, o.x, o.y, o.w, o.h)) hits += 1
    }
  }
  return hits
}

function pathLen(pts) {
  let s = 0
  for (let i = 0; i < pts.length - 1; i++) {
    s += Math.abs(pts[i + 1][0] - pts[i][0]) + Math.abs(pts[i + 1][1] - pts[i][1])
  }
  return s
}

function iterHvSegs(pts) {
  const segs = []
  for (let i = 0; i < pts.length - 1; i++) {
    const [x0, y0] = pts[i]
    const [x1, y1] = pts[i + 1]
    if (Math.abs(y0 - y1) < 0.5) segs.push(['H', Math.min(x0, x1), Math.max(x0, x1), y0])
    else if (Math.abs(x0 - x1) < 0.5) segs.push(['V', x0, Math.min(y0, y1), Math.max(y0, y1)])
  }
  return segs
}

function hvProperCross(ha, va) {
  const [x0, x1, y] = ha
  const [x, y0, y1] = va
  const eps = 0.25
  return x0 + eps < x && x < x1 - eps && y0 + eps < y && y < y1 - eps
}

function segOverlap1d(a0, a1, b0, b1, eps = 0.5) {
  const loA = Math.min(a0, a1)
  const hiA = Math.max(a0, a1)
  const loB = Math.min(b0, b1)
  const hiB = Math.max(b0, b1)
  return hiA - eps > loB && hiB - eps > loA
}

/** 两折线是否开交叉（对齐后端：同槽共线可共用总线，不算冲突） */
function pathsConflict(a, b) {
  const sa = iterHvSegs(a)
  const sb = iterHvSegs(b)
  for (const si of sa) {
    for (const sj of sb) {
      if (si[0] === 'H' && sj[0] === 'V') {
        if (hvProperCross([si[1], si[2], si[3]], [sj[1], sj[2], sj[3]])) return true
      } else if (si[0] === 'V' && sj[0] === 'H') {
        if (hvProperCross([sj[1], sj[2], sj[3]], [si[1], si[2], si[3]])) return true
      }
    }
  }
  return false
}

function markerAttrsForKind(kind, hot = false) {
  const k = String(kind || 'association')
  const suf = hot ? '-hot' : ''
  if (k === 'dependency') {
    return { dash: '6 4', start: '', end: `url(#uml-open${suf})` }
  }
  if (k === 'inheritance') {
    return { dash: '', start: '', end: `url(#uml-tri${suf})` }
  }
  if (k === 'implementation') {
    return { dash: '6 4', start: '', end: `url(#uml-tri${suf})` }
  }
  if (k === 'aggregation') {
    return { dash: '', start: `url(#uml-agg${suf})`, end: `url(#uml-open${suf})` }
  }
  if (k === 'composition') {
    return { dash: '', start: `url(#uml-comp${suf})`, end: `url(#uml-open${suf})` }
  }
  return { dash: '', start: '', end: `url(#uml-open${suf})` }
}

function applyPathMarkers(pathEl, kind, hot = false) {
  const m = markerAttrsForKind(kind, hot)
  if (m.dash) pathEl.setAttribute('stroke-dasharray', m.dash)
  else pathEl.removeAttribute('stroke-dasharray')
  if (m.start) pathEl.setAttribute('marker-start', m.start)
  else pathEl.removeAttribute('marker-start')
  pathEl.setAttribute('marker-end', m.end)
}

function boxFromCenter(c) {
  const hw = Number(c.g.getAttribute('data-hw')) || 60
  const hh = Number(c.g.getAttribute('data-hh')) || 40
  return { id: c.id, x: c.x - hw, y: c.y - hh, w: hw * 2, h: hh * 2, cx: c.x, cy: c.y }
}

/** 与后端 classes.py `_CHANNEL` / `_BOX_GAP` / `_LANE_GAP` 对齐 */
const CHANNEL = 56
const BOX_GAP = 72
const LANE_GAP = 12

/** 侧边端口兜底（禁止中心穿框） */
function sidePortFallback(A, B, t, off) {
  const dx = B.cx - A.cx
  const dy = B.cy - A.cy
  let sx
  let sy
  let ex
  let ey
  if (Math.abs(dx) >= Math.abs(dy)) {
    if (dx >= 0) {
      sx = A.x + A.w
      sy = A.y + A.h * t
      ex = B.x
      ey = B.y + B.h * t
    } else {
      sx = A.x
      sy = A.y + A.h * t
      ex = B.x + B.w
      ey = B.y + B.h * t
    }
    if (Math.abs(sy - ey) < 1) return [[sx, sy], [ex, ey]]
    const mid = clampMid(sx, ex, (sx + ex) / 2 + off)
    return [[sx, sy], [mid, sy], [mid, ey], [ex, ey]]
  }
  if (dy >= 0) {
    sx = A.x + A.w * t
    sy = A.y + A.h
    ex = B.x + B.w * t
    ey = B.y
  } else {
    sx = A.x + A.w * t
    sy = A.y
    ex = B.x + B.w * t
    ey = B.y + B.h
  }
  if (Math.abs(sx - ex) < 1) return [[sx, sy], [ex, ey]]
  const midy = clampMid(sy, ey, (sy + ey) / 2 + off)
  return [[sx, sy], [sx, midy], [ex, midy], [ex, ey]]
}

function dedupePts(pts, eps = 0.5) {
  if (!pts?.length) return []
  const out = [pts[0]]
  for (let i = 1; i < pts.length; i++) {
    const p = pts[i]
    const q = out[out.length - 1]
    if (Math.abs(p[0] - q[0]) > eps || Math.abs(p[1] - q[1]) > eps) out.push(p)
  }
  return out
}

/** 端口第一段必须朝框外，禁止穿回自身（否则白底盖住只剩框外断头） */
function portLeavesOutward(p0, p1, box) {
  const [x0, y0] = p0
  const [x1, y1] = p1
  const { x: bx, y: by, w: bw, h: bh } = box
  const tol = 2.5
  const onR = Math.abs(x0 - (bx + bw)) <= tol && y0 >= by - tol && y0 <= by + bh + tol
  const onL = Math.abs(x0 - bx) <= tol && y0 >= by - tol && y0 <= by + bh + tol
  const onT = Math.abs(y0 - by) <= tol && x0 >= bx - tol && x0 <= bx + bw + tol
  const onB = Math.abs(y0 - (by + bh)) <= tol && x0 >= bx - tol && x0 <= bx + bw + tol
  if (onR && x1 < x0 - 1) return false
  if (onL && x1 > x0 + 1) return false
  if (onT && y1 > y0 + 1) return false
  if (onB && y1 < y0 - 1) return false
  return true
}

function pathCutsBoxInterior(pts, box, eps = 1) {
  const ix0 = box.x + eps
  const iy0 = box.y + eps
  const ix1 = box.x + box.w - eps
  const iy1 = box.y + box.h - eps
  if (ix1 <= ix0 || iy1 <= iy0) return false
  for (let i = 0; i < pts.length - 1; i++) {
    const [x0, y0] = pts[i]
    const [x1, y1] = pts[i + 1]
    if (Math.abs(y0 - y1) < 0.5) {
      if (y0 > iy0 && y0 < iy1) {
        const lo = Math.min(x0, x1)
        const hi = Math.max(x0, x1)
        if (lo < ix1 - 0.1 && hi > ix0 + 0.1) return true
      }
    } else if (Math.abs(x0 - x1) < 0.5) {
      if (x0 > ix0 && x0 < ix1) {
        const lo = Math.min(y0, y1)
        const hi = Math.max(y0, y1)
        if (lo < iy1 - 0.1 && hi > iy0 + 0.1) return true
      }
    }
  }
  return false
}

function pathRespectsEndpointPorts(pts, boxA, boxB) {
  if (!pts || pts.length < 2) return false
  if (boxA) {
    if (!portLeavesOutward(pts[0], pts[1], boxA)) return false
    if (pathCutsBoxInterior(pts, boxA)) return false
  }
  if (boxB) {
    if (!portLeavesOutward(pts[pts.length - 1], pts[pts.length - 2], boxB)) return false
    if (pathCutsBoxInterior(pts, boxB)) return false
  }
  return true
}

function orthoPathAvoid(a, b, allCenters, edgeKey = '', lane = 0, nLanes = 1, otherPaths = []) {
  const A = boxFromCenter(a)
  const B = boxFromCenter(b)
  const obstacles = allCenters.map(boxFromCenter)
  const t = laneT(lane, nLanes)
  const off = laneOffset(lane, nLanes)

  const ports = [
    [A.x + A.w, A.y + A.h * t, B.x, B.y + B.h * t],
    [A.x, A.y + A.h * t, B.x + B.w, B.y + B.h * t],
    [A.x + A.w * t, A.y + A.h, B.x + B.w * t, B.y],
    [A.x + A.w * t, A.y, B.x + B.w * t, B.y + B.h],
    [A.x + A.w, A.y + A.h * t, B.x + B.w, B.y + B.h * t],
    [A.x, A.y + A.h * t, B.x, B.y + B.h * t],
    [A.x + A.w * t, A.y + A.h, B.x + B.w * t, B.y + B.h],
    [A.x + A.w * t, A.y, B.x + B.w * t, B.y],
  ]

  /** @type {{pts:number[][], outer:boolean}[]} */
  const candidates = []
  function addCand(pts, outer = false) {
    if (pts?.length >= 2) candidates.push({ pts, outer })
  }

  for (const [sx, sy, ex, ey] of ports) {
    if (Math.abs(sy - ey) < 1) addCand([[sx, sy], [ex, ey]])
    else if (Math.abs(sx - ex) < 1) addCand([[sx, sy], [ex, ey]])
    else {
      addCand([[sx, sy], [ex, sy], [ex, ey]])
      addCand([[sx, sy], [sx, ey], [ex, ey]])
      const mid = clampMid(sx, ex, (sx + ex) / 2 + off)
      addCand([[sx, sy], [mid, sy], [mid, ey], [ex, ey]])
      const midy = clampMid(sy, ey, (sy + ey) / 2 + off)
      addCand([[sx, sy], [sx, midy], [ex, midy], [ex, ey]])
    }
  }

  let L = Infinity
  let R = -Infinity
  let T = Infinity
  let Bot = -Infinity
  for (const o of obstacles) {
    L = Math.min(L, o.x)
    R = Math.max(R, o.x + o.w)
    T = Math.min(T, o.y)
    Bot = Math.max(Bot, o.y + o.h)
  }
  L -= CHANNEL + lane * LANE_GAP
  R += CHANNEL + lane * LANE_GAP
  T -= CHANNEL + lane * LANE_GAP
  Bot += CHANNEL + lane * LANE_GAP
  for (const [sx, sy, ex, ey] of ports.slice(0, 4)) {
    addCand([[sx, sy], [L, sy], [L, ey], [ex, ey]], true)
    addCand([[sx, sy], [R, sy], [R, ey], [ex, ey]], true)
    addCand([[sx, sy], [sx, T], [ex, T], [ex, ey]], true)
    addCand([[sx, sy], [sx, Bot], [ex, Bot], [ex, ey]], true)
  }

  const rights = [...new Set(obstacles.map((o) => o.x + o.w))].sort((a, b) => a - b)
  const lefts = [...new Set(obstacles.map((o) => o.x))].sort((a, b) => a - b)
  const bottoms = [...new Set(obstacles.map((o) => o.y + o.h))].sort((a, b) => a - b)
  const tops = [...new Set(obstacles.map((o) => o.y))].sort((a, b) => a - b)
  const guttersX = []
  for (const r of rights) {
    for (const lf of lefts) {
      if (lf - r >= BOX_GAP * 0.6) {
        guttersX.push((r + lf) / 2 + off)
        break
      }
    }
  }
  const guttersY = []
  for (const bt of bottoms) {
    for (const tp of tops) {
      if (tp - bt >= BOX_GAP * 0.6) {
        guttersY.push((bt + tp) / 2 + off)
        break
      }
    }
  }
  for (const gx of guttersX.slice(0, 8)) {
    for (const [sx, sy, ex, ey] of ports.slice(0, 4)) {
      addCand([[sx, sy], [gx, sy], [gx, ey], [ex, ey]])
    }
  }
  for (const gy of guttersY.slice(0, 8)) {
    for (const [sx, sy, ex, ey] of ports.slice(0, 4)) {
      addCand([[sx, sy], [sx, gy], [ex, gy], [ex, ey]])
    }
  }

  const ignore = new Set([A.id, B.id])
  let bestClean = null
  let bestCleanKey = null
  let bestAny = null
  let bestAnyKey = null
  function better(key, prev) {
    if (!prev) return true
    if (key.p !== prev.p) return key.p < prev.p
    if (key.c !== prev.c) return key.c < prev.c
    if (key.h !== prev.h) return key.h < prev.h
    if (key.b !== prev.b) return key.b < prev.b
    return key.l < prev.l
  }
  for (const { pts, outer } of candidates) {
    const ptsN = dedupePts(pts)
    if (ptsN.length < 2) continue
    const portBad = pathRespectsEndpointPorts(ptsN, A, B) ? 0 : 1
    const hits = pathObstacleHits(ptsN, obstacles, ignore)
    let crosses = 0
    for (const op of otherPaths) {
      if (op?.length >= 2 && pathsConflict(ptsN, op)) crosses += 1
    }
    const bends = Math.max(0, ptsN.length - 2)
    const length = pathLen(ptsN) + (outer ? 120 : 0)
    const key = { p: portBad, c: crosses, h: hits, b: bends, l: length }
    if (better(key, bestAnyKey)) {
      bestAnyKey = key
      bestAny = ptsN
    }
    // 硬优先：朝外出端口 + 零交叉 + 不穿第三方框
    if (portBad === 0 && crosses === 0 && hits === 0 && better(key, bestCleanKey)) {
      bestCleanKey = key
      bestClean = ptsN
    }
  }
  if (bestClean) return bestClean
  // 无干净路径时取冲突最少且不穿自身框的候选
  if (bestAny && bestAnyKey && bestAnyKey.p === 0) return bestAny
  return sidePortFallback(A, B, t, off)
}

function pathD(pts) {
  if (!pts?.length) return ''
  return pts.map((p, i) => `${i ? 'L' : 'M'} ${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join(' ')
}

function laneT(lane, nLanes) {
  if (nLanes <= 1) return 0.5
  return 0.2 + (0.6 * lane) / (nLanes - 1)
}

function laneOffset(lane, nLanes) {
  if (nLanes <= 1) return 0
  return (lane - (nLanes - 1) / 2) * LANE_GAP
}

function clampMid(lo, hi, mid, margin = 6) {
  const a = Math.min(lo, hi)
  const b = Math.max(lo, hi)
  if (b - a < margin * 2 + 1) return (a + b) / 2
  return Math.max(a + margin, Math.min(b - margin, mid))
}

/** 解析仅含 M/L 的直角折线 */
function parsePolyPoints(d) {
  const pts = []
  const re = /([ML])\s*([-\d.]+)\s+([-\d.]+)/gi
  let m
  while ((m = re.exec(d || ''))) {
    pts.push([Number(m[2]), Number(m[3])])
  }
  return pts
}

/**
 * 拖拽中：只重画「连到指定类」的关联（draw.io：动点只动相连边）；硬优先零交叉。
 */
function refreshEdgesForNodes(svg, nodeIds) {
  const idSet = new Set((nodeIds || []).filter(Boolean))
  if (!idSet.size) return
  const centers = []
  const byId = new Map()
  svg.querySelectorAll('.uml-node').forEach((g) => {
    const c = nodeCenter(g)
    centers.push(c)
    byId.set(c.id, c)
  })
  const paths = [...svg.querySelectorAll('path.uml-assoc')]
  const toMove = paths.filter((path) => {
    const fromId = path.getAttribute('data-from')
    const toId = path.getAttribute('data-to')
    return idSet.has(fromId) || idSet.has(toId)
  })
  const nLanes = Math.max(1, toMove.length)
  // 先收集不动边的折线，作为避叉障碍
  const frozen = []
  paths.forEach((path) => {
    const fromId = path.getAttribute('data-from')
    const toId = path.getAttribute('data-to')
    if (idSet.has(fromId) || idSet.has(toId)) return
    const pts = parsePolyPoints((path.getAttribute('d') || '').replace(/A[^ML]*/gi, ' '))
    if (pts.length >= 2) frozen.push(pts)
  })
  const movedPts = []
  toMove.forEach((path, lane) => {
    const fromId = path.getAttribute('data-from')
    const toId = path.getAttribute('data-to')
    const a = byId.get(fromId)
    const b = byId.get(toId)
    if (!a || !b) return
    const kind = path.getAttribute('data-kind') || 'association'
    path.removeAttribute('visibility')
    const pts = orthoPathAvoid(
      a,
      b,
      centers,
      `${fromId}->${toId}`,
      lane,
      nLanes,
      [...frozen, ...movedPts],
    )
    movedPts.push(pts)
    path.setAttribute('d', pathD(pts))
    const tip = path.getAttribute('data-tip') || `${fromId} → ${toId}`
    path.setAttribute('data-tip', tip)
    applyPathMarkers(path, kind, false)
  })
}

function refreshAllEdges(svg) {
  const ids = [...svg.querySelectorAll('.uml-node')].map((g) => g.getAttribute('data-id'))
  refreshEdgesForNodes(svg, ids)
}

let dragEdgeRaf = 0
function refreshEdgesWhileDrag(svg) {
  if (dragEdgeRaf) return
  const dragId = dragNode.value?.getAttribute?.('data-id')
  dragEdgeRaf = requestAnimationFrame(() => {
    dragEdgeRaf = 0
    // 只更新拖动类的相连边；扩画布若整体平移则 shiftAssocPaths 平移全部折线
    refreshEdgesForNodes(svg, [dragId])
    expandCanvasToFit(svg)
  })
}

function bindAssocHover(svg) {
  svg.querySelectorAll('.uml-node').forEach((g) => {
    if (g.dataset.hoverBound) return
    g.dataset.hoverBound = '1'
    g.addEventListener('pointerenter', () => {
      const id = g.getAttribute('data-id')
      svg.querySelectorAll('path.uml-assoc').forEach((el) => {
        const hot =
          el.getAttribute('data-from') === id || el.getAttribute('data-to') === id
        el.classList.toggle('uml-assoc-hot', hot)
        applyPathMarkers(el, el.getAttribute('data-kind') || 'association', hot)
      })
      g.classList.add('uml-node-hot')
    })
    g.addEventListener('pointerleave', () => {
      svg.querySelectorAll('path.uml-assoc').forEach((el) => {
        el.classList.remove('uml-assoc-hot')
        applyPathMarkers(el, el.getAttribute('data-kind') || 'association', false)
      })
      g.classList.remove('uml-node-hot')
    })
  })
}

function shiftAssocPaths(svg, dx, dy) {
  if (!dx && !dy) return
  svg.querySelectorAll('path.uml-assoc').forEach((el) => {
    const pts = parsePolyPoints((el.getAttribute('d') || '').replace(/A[^ML]*/gi, ' '))
    if (pts.length < 2) return
    el.setAttribute(
      'd',
      pathD(pts.map(([x, y]) => [x + dx, y + dy])),
    )
  })
}

function applyOffsetsToDom() {
  const svg = getSvg()
  if (!svg) return
  let moved = false
  svg.querySelectorAll('.uml-node').forEach((g) => {
    const id = g.getAttribute('data-id')
    const o = offsets.get(id) || { dx: 0, dy: 0 }
    if (o.dx || o.dy) moved = true
    setNodeTransform(g, id)
  })
  // 导出时若仍有未落盘位移，用改进后的零交叉路由重画；松手正常路径会回拉后端 SVG
  if (moved) refreshAllEdges(svg)
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

function nodeExtent(g) {
  const c = nodeCenter(g)
  const hw = Number(g.getAttribute('data-hw')) || 60
  const hh = Number(g.getAttribute('data-hh')) || 40
  return { minX: c.x - hw, maxX: c.x + hw, minY: c.y - hh, maxY: c.y + hh }
}

function contentBounds(svg) {
  let minX = Infinity
  let minY = Infinity
  let maxX = -Infinity
  let maxY = -Infinity
  svg.querySelectorAll('.uml-node').forEach((g) => {
    const e = nodeExtent(g)
    minX = Math.min(minX, e.minX)
    maxX = Math.max(maxX, e.maxX)
    minY = Math.min(minY, e.minY)
    maxY = Math.max(maxY, e.maxY)
  })
  // 折线外槽也算进画布，避免线被裁掉
  svg.querySelectorAll('path.uml-assoc').forEach((path) => {
    const pts = parsePolyPoints((path.getAttribute('d') || '').replace(/A[^ML]*/gi, ' '))
    for (const [x, y] of pts) {
      minX = Math.min(minX, x)
      maxX = Math.max(maxX, x)
      minY = Math.min(minY, y)
      maxY = Math.max(maxY, y)
    }
  })
  return { minX, minY, maxX, maxY }
}

function setSvgSize(svg, w, h) {
  const nw = Math.ceil(w)
  const nh = Math.ceil(h)
  svg.setAttribute('width', String(nw))
  svg.setAttribute('height', String(nh))
  svg.setAttribute('viewBox', `0 0 ${nw} ${nh}`)
  const paper = svg.querySelector('.uml-paper')
  if (paper) {
    paper.setAttribute('width', String(nw))
    paper.setAttribute('height', String(nh))
  }
}

function clampNodesToCanvas(svg, w, h) {
  // 仅在顶到绝对上限时卡住；平时靠扩画布，不往回拽
  if (w < CANVAS_MAX_W - 1 && h < CANVAS_MAX_H - 1) return
  const xMax = w - CANVAS_PAD
  const yMax = h - CANVAS_PAD
  const moved = []
  svg.querySelectorAll('.uml-node').forEach((g) => {
    const e = nodeExtent(g)
    let ddx = 0
    let ddy = 0
    if (e.minX < CANVAS_PAD) ddx = CANVAS_PAD - e.minX
    else if (e.maxX > xMax) ddx = xMax - e.maxX
    if (e.minY < CANVAS_PAD) ddy = CANVAS_PAD - e.minY
    else if (e.maxY > yMax) ddy = yMax - e.maxY
    if (!ddx && !ddy) return
    const id = g.getAttribute('data-id')
    bumpOffset(id, ddx, ddy)
    setNodeTransform(g, id)
    if (id) moved.push(id)
  })
  if (moved.length) refreshEdgesForNodes(svg, moved)
}

function expandCanvasToFit(svg) {
  const b = contentBounds(svg)
  if (!Number.isFinite(b.minX)) return

  let { maxX, maxY } = b
  // 对齐 draw.io：不因拖一个框而整体平移整图（否则无关折线也会动）
  const bumped = []
  svg.querySelectorAll('.uml-node').forEach((g) => {
    const e = nodeExtent(g)
    let ddx = 0
    let ddy = 0
    if (e.minX < CANVAS_PAD) ddx = CANVAS_PAD - e.minX
    if (e.minY < CANVAS_PAD) ddy = CANVAS_PAD - e.minY
    if (!ddx && !ddy) return
    const id = g.getAttribute('data-id')
    bumpOffset(id, ddx, ddy)
    setNodeTransform(g, id)
    if (id) bumped.push(id)
    maxX = Math.max(maxX, e.maxX + ddx)
    maxY = Math.max(maxY, e.maxY + ddy)
  })
  if (bumped.length) refreshEdgesForNodes(svg, bumped)

  const { w, h } = svgSize(svg)
  const needW = Math.ceil(Math.max(maxX + CANVAS_PAD, maxX + EDGE_GROW))
  const needH = Math.ceil(Math.max(maxY + CANVAS_PAD, maxY + EDGE_GROW))
  const nw = Math.min(Math.max(needW, w), CANVAS_MAX_W)
  const nh = Math.min(Math.max(needH, h), CANVAS_MAX_H)
  if (nw !== w || nh !== h) {
    setSvgSize(svg, nw, nh)
  }
  clampNodesToCanvas(svg, nw, nh)
}

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

function fitToFrame() {
  const frame = frameRef.value
  const svg = getSvg()
  if (!frame || !svg) return
  const { w, h } = svgSize(svg)
  const fw = frame.clientWidth || 1
  const fh = frame.clientHeight || 1
  if (fw < 40 || fh < 40 || w < 1 || h < 1) return
  const next = clampScale(Math.min(fw / w, fh / h) * FIT_MARGIN)
  scale.value = next
  panX.value = (fw - w * next) / 2
  panY.value = (fh - h * next) / 2
}

/** 弹窗首帧常未撑开；等可用尺寸再 fit。中间态≥80px 就 fit 会裁掉外绕线。 */
function scheduleFitToFrame(force = false) {
  if (didFitView.value && !force) return
  const run = () => {
    const frame = frameRef.value
    const svg = getSvg()
    if (!frame || !svg) return
    // 类图弹窗可用区大约 ≥200 高；过小说明还在动画/未布局完
    if (frame.clientWidth < 120 || frame.clientHeight < 200) {
      if (fitRetries < 36) {
        fitRetries += 1
        requestAnimationFrame(run)
      }
      return
    }
    userAdjustedView = false
    fitToFrame()
    didFitView.value = true
    fitRetries = 0
    frameLastW = frame.clientWidth
    frameLastH = frame.clientHeight
  }
  nextTick(() => requestAnimationFrame(() => requestAnimationFrame(run)))
}

onMounted(() => {
  const frame = frameRef.value
  if (!frame || typeof ResizeObserver === 'undefined') return
  resizeObs = new ResizeObserver(() => {
    const w = frame.clientWidth
    const h = frame.clientHeight
    if (!didFitView.value) {
      scheduleFitToFrame()
      return
    }
    if (userAdjustedView) {
      frameLastW = w
      frameLastH = h
      return
    }
    // 弹窗从中间态撑开：尺寸跳变则再 fit（否则顶/左侧外绕线被 overflow 裁掉）
    const grew =
      (frameLastW > 0 && w - frameLastW > 48) ||
      (frameLastH > 0 && h - frameLastH > 48)
    const crossedFloor =
      (frameLastW < 120 && w >= 120) || (frameLastH < 200 && h >= 200)
    if (grew || crossedFloor) {
      fitToFrame()
    }
    frameLastW = w
    frameLastH = h
  })
  resizeObs.observe(frame)
})

onUnmounted(() => {
  resizeObs?.disconnect()
  resizeObs = null
})

function bakeNodeOffsets(svg) {
  /** 松手后把 translate 写回 data-cx/cy 与内部几何，避免反复叠 transform */
  svg.querySelectorAll('.uml-node').forEach((g) => {
    const id = g.getAttribute('data-id')
    const o = offsets.get(id) || { dx: 0, dy: 0 }
    if (!o.dx && !o.dy) return
    const cx = Number(g.getAttribute('data-cx')) || 0
    const cy = Number(g.getAttribute('data-cy')) || 0
    g.setAttribute('data-cx', (cx + o.dx).toFixed(1))
    g.setAttribute('data-cy', (cy + o.dy).toFixed(1))
    g.querySelectorAll('rect, line, text').forEach((el) => {
      for (const attr of ['x', 'x1', 'x2']) {
        if (!el.hasAttribute(attr)) continue
        el.setAttribute(attr, (Number(el.getAttribute(attr)) + o.dx).toFixed(1))
      }
      for (const attr of ['y', 'y1', 'y2']) {
        if (!el.hasAttribute(attr)) continue
        el.setAttribute(attr, (Number(el.getAttribute(attr)) + o.dy).toFixed(1))
      }
    })
    g.removeAttribute('transform')
    offsets.set(id, { dx: 0, dy: 0 })
  })
}

function loadSource(raw) {
  offsets.clear()
  dragNode.value = null
  svgHtml.value = parseSvg(raw)
  nextTick(() => {
    const svg = getSvg()
    if (!svg) return
    svg.querySelectorAll('.uml-node').forEach((g) => {
      g.style.cursor = 'move'
      g.style.pointerEvents = 'all'
    })
    const KIND_ZH = {
      association: '关联',
      dependency: '依赖',
      inheritance: '继承',
      implementation: '实现',
      aggregation: '聚合',
      composition: '组合',
    }
    svg.querySelectorAll('.uml-assoc').forEach((el) => {
      el.style.pointerEvents = 'none'
      const frm = el.getAttribute('data-from') || ''
      const to = el.getAttribute('data-to') || ''
      const kind = el.getAttribute('data-kind') || 'association'
      const kzh = KIND_ZH[kind] || kind
      if (frm && to) el.setAttribute('data-tip', `${frm} → ${to}（${kzh}）`)
    })
    const paper = svg.querySelector('.uml-paper')
    if (paper) paper.style.pointerEvents = 'none'
    bindAssocHover(svg)
    // 后端已零交叉排线；拖拽中临时跟线，松手落盘后回拉精炼 SVG
    // 松手回拉不重置视口；首次打开等弹窗撑开后再 fit，避免裁线
    if (!didFitView.value) scheduleFitToFrame()
  })
}

watch(
  () => props.svgSource,
  (v) => loadSource(v),
  { immediate: true },
)

function findNode(target) {
  if (!target) return null
  if (typeof target.closest === 'function') return target.closest('.uml-node')
  let el = target
  while (el && el !== frameRef.value) {
    if (el.classList?.contains('uml-node')) return el
    el = el.parentElement || el.parentNode
  }
  return null
}

function onPointerDown(e) {
  if (e.button !== 0) return
  // 拖布局时禁止浏览器选中文字
  e.preventDefault()
  const node = findNode(e.target)
  if (node) {
    dragNode.value = node
    dragLastX = e.clientX
    dragLastY = e.clientY
    node.classList.add('uml-node-active')
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
    const svg = getSvg()
    if (svg) {
      refreshEdgesWhileDrag(svg)
    }
    autoPanWhileDrag(e.clientX, e.clientY)
    return
  }
  if (!panning.value) return
  userAdjustedView = true
  panX.value += e.clientX - panLastX
  panY.value += e.clientY - panLastY
  panLastX = e.clientX
  panLastY = e.clientY
}

function collectLayout(svg) {
  const layout = {}
  svg.querySelectorAll('.uml-node').forEach((g) => {
    const id = g.getAttribute('data-id')
    if (!id) return
    const cx = Number(g.getAttribute('data-cx')) || 0
    const cy = Number(g.getAttribute('data-cy')) || 0
    const hw = Number(g.getAttribute('data-hw')) || 60
    const hh = Number(g.getAttribute('data-hh')) || 40
    layout[id] = {
      x: Number((cx - hw).toFixed(1)),
      y: Number((cy - hh).toFixed(1)),
      w: Number((hw * 2).toFixed(1)),
      h: Number((hh * 2).toFixed(1)),
    }
  })
  return layout
}

function onPointerUp(e) {
  if (dragNode.value) {
    dragNode.value.classList.remove('uml-node-active')
    dragNode.value = null
    const svg = getSvg()
    if (svg) {
      bakeNodeOffsets(svg)
      expandCanvasToFit(svg)
      bakeNodeOffsets(svg)
      // 不在此用前端全量重画（易交叉且与后端不一致）；落盘后回拉后端零交叉 SVG
      emit('save-layout', collectLayout(svg))
    }
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
  const before = scale.value
  const next = clampScale(before + (e.deltaY > 0 ? -SCALE_STEP : SCALE_STEP))
  if (next === before) return
  userAdjustedView = true
  const ratio = next / before
  panX.value = mx - (mx - panX.value) * ratio
  panY.value = my - (my - panY.value) * ratio
  scale.value = next
}

function zoomIn() {
  userAdjustedView = true
  scale.value = clampScale(scale.value + SCALE_STEP)
}
function zoomOut() {
  userAdjustedView = true
  scale.value = clampScale(scale.value - SCALE_STEP)
}
function resetView() {
  userAdjustedView = false
  fitToFrame()
}

function onReload() {
  emit('reset-layout')
}

function triggerDownload(blob, filename) {
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = filename
  a.click()
  URL.revokeObjectURL(a.href)
}

function serializeSvg() {
  const svg = getSvg()
  if (!svg) return ''
  applyOffsetsToDom()
  const clone = svg.cloneNode(true)
  clone.querySelectorAll('.uml-node-active').forEach((el) => el.classList.remove('uml-node-active'))
  clone.querySelectorAll('[style]').forEach((el) => el.removeAttribute('style'))
  const paper = clone.querySelector('.uml-paper')
  if (paper) paper.setAttribute('fill', '#ffffff')
  const xml = new XMLSerializer().serializeToString(clone)
  if (xml.startsWith('<?xml')) return xml
  return `<?xml version="1.0" encoding="UTF-8"?>\n${xml}`
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
        canvas.width = Math.round(w * pixelRatio)
        canvas.height = Math.round(h * pixelRatio)
        const ctx = canvas.getContext('2d')
        ctx.fillStyle = '#ffffff'
        ctx.fillRect(0, 0, canvas.width, canvas.height)
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
        canvas.toBlob((b) => {
          URL.revokeObjectURL(url)
          if (b) resolve(b)
          else reject(new Error('png'))
        }, 'image/png')
      } catch (err) {
        URL.revokeObjectURL(url)
        reject(err)
      }
    }
    img.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('img'))
    }
    img.src = url
  })
}

async function copyPng() {
  busy.value = true
  try {
    const blob = await rasterizePng()
    await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })])
    message.success('已复制图片（当前布局）')
  } catch {
    message.error('复制失败，可改下 PNG')
  } finally {
    busy.value = false
  }
}

async function downloadPng() {
  busy.value = true
  try {
    const blob = await rasterizePng()
    triggerDownload(blob, `${fileBase.value}.png`)
  } catch {
    message.error('下载 PNG 失败')
  } finally {
    busy.value = false
  }
}

function downloadSvg() {
  const raw = serializeSvg()
  if (!raw) {
    message.error('无矢量源')
    return
  }
  triggerDownload(new Blob([raw], { type: 'image/svg+xml;charset=utf-8' }), `${fileBase.value}.svg`)
}

defineExpose({ serializeSvg, downloadSvg, downloadPng, copyPng, resetView })
</script>

<style scoped>
.cls-viewer {
  display: flex;
  flex-direction: column;
  min-height: 420px;
}
.cls-toolbar {
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.cls-zoom-btns {
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.cls-zoom-label {
  min-width: 48px;
  text-align: center;
  font-variant-numeric: tabular-nums;
  font-size: 12px;
  color: var(--muted);
}
.cls-hint { line-height: 1.5; }
.cls-frame {
  flex: 1;
  min-height: 360px;
  max-height: min(70vh, 720px);
  overflow: hidden;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: #fff;
  cursor: grab;
  position: relative;
  touch-action: none;
  user-select: none;
  -webkit-user-select: none;
}
.cls-frame.is-panning { cursor: grabbing; }
.cls-frame.is-dragging-node { cursor: move; }
.cls-viewer.is-dark .cls-frame {
  background: #f7f7f7;
}
.cls-canvas {
  display: inline-block;
  will-change: transform;
}
.cls-canvas :deep(svg) {
  display: block;
  max-width: none;
  height: auto;
  overflow: visible;
  user-select: none;
  -webkit-user-select: none;
}
.cls-canvas :deep(text) {
  user-select: none;
  -webkit-user-select: none;
}
.cls-canvas :deep(.uml-node-active .uml-class) {
  stroke-width: 2;
}
.cls-canvas :deep(.uml-node-hot .uml-class) {
  stroke: #0d9488;
  stroke-width: 2;
}
.cls-canvas :deep(path.uml-assoc-hot) {
  stroke: #0d9488;
  stroke-width: 1.6;
}
</style>
