<template>
  <div class="er-viewer" :class="{ 'is-dark': isDark }">
    <div class="er-toolbar row mb-12">
      <div class="er-zoom-btns row">
        <n-radio-group v-model:value="modeLocal" size="small" :disabled="loading" @update:value="onModeChange">
          <n-radio-button value="total">总图</n-radio-button>
          <n-radio-button value="part">分图</n-radio-button>
        </n-radio-group>
        <n-select
          v-if="modeLocal === 'part'"
          v-model:value="entityLocal"
          size="small"
          :options="entityOptions"
          :loading="loading"
          :disabled="loading"
          placeholder="选择实体"
          style="width:140px"
          @update:value="onEntityChange"
        />
        <n-button size="small" @click="zoomOut">缩小</n-button>
        <span class="er-zoom-label">{{ Math.round(scale * 100) }}%</span>
        <n-button size="small" @click="zoomIn">放大</n-button>
        <n-button size="small" @click="resetView">重置视口</n-button>
        <n-button size="small" :loading="loading" @click="$emit('reload')">重置布局</n-button>
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
          ? '总图：实体 + 联系 + 基数（不含属性）'
          : '分图：单个实体 + 全部属性（按实体各导出一张）'
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
      <div class="er-canvas" :style="canvasStyle" v-html="svgHtml" />
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { message } from '../api'
import { isDark } from '../theme'

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

const emit = defineEmits(['reload', 'update:mode', 'update:entity'])

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
const busy = ref(false)
const modeLocal = ref(props.mode === 'part' ? 'part' : 'total')
const entityLocal = ref(props.entity || '')

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
    svg.querySelectorAll('.er-edge, .er-card').forEach((el) => {
      el.style.pointerEvents = 'none'
    })
    const bg = svg.querySelector('rect')
    if (bg && !bg.classList.contains('er-bg-hit')) {
      bg.classList.add('er-bg-hit', 'er-paper')
      bg.style.pointerEvents = 'none'
    }
    applyStrokePreset()
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
  let changed = false
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
    bumpOffset(id, ddx, ddy)
    setNodeTransform(g, id)
    changed = true
  })
  if (changed) refreshAllEdges(svg)
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
    svg.querySelectorAll('.er-node').forEach((g) => {
      const id = g.getAttribute('data-id')
      bumpOffset(id, shiftX, shiftY)
      setNodeTransform(g, id)
    })
    maxX += shiftX
    maxY += shiftY
    refreshAllEdges(svg)
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
    if (svg) {
      refreshAllEdges(svg)
      expandCanvasToFit(svg)
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

function onPointerUp(e) {
  if (dragNode.value) {
    dragNode.value.classList.remove('er-node-active')
    dragNode.value = null
    dragFollowers = []
    const svg = getSvg()
    if (svg) expandCanvasToFit(svg)
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
  will-change: transform;
}
.er-canvas :deep(svg) {
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
