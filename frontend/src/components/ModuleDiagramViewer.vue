<template>
  <div class="mod-viewer" :class="{ 'is-dark': isDark }">
    <div class="mod-toolbar row mb-12">
      <div class="mod-zoom-btns row">
        <n-radio-group v-model:value="layoutLocal" size="small" @update:value="onLayoutChange">
          <n-radio-button value="biz">按业务</n-radio-button>
          <n-radio-button value="side">按端</n-radio-button>
        </n-radio-group>
        <n-button size="small" @click="zoomOut">缩小</n-button>
        <span class="mod-zoom-label">{{ Math.round(scale * 100) }}%</span>
        <n-button size="small" @click="zoomIn">放大</n-button>
        <n-button size="small" @click="resetView">重置视口</n-button>
        <n-button size="small" @click="$emit('reload')">重新加载</n-button>
        <n-button size="small" type="primary" :loading="busy" @click="copyPng">复制图片</n-button>
        <n-button size="small" type="primary" secondary :loading="busy" @click="downloadPng">下载 PNG</n-button>
        <n-button size="small" quaternary @click="downloadSvg">下载矢量源</n-button>
      </div>
    </div>
    <p class="small muted mod-hint mb-8">
      {{
        layoutLocal === 'biz'
          ? '按业务拆：用户 / 业务对象 / 订单…（论文常用）'
          : '按端拆：用户端与管理端菜单对照'
      }}
      ；与系统菜单一致，开题材料只辅助中文命名。
    </p>
    <div
      ref="frameRef"
      class="mod-frame"
      :class="{ 'is-panning': panning }"
      @wheel.prevent="onWheel"
      @pointerdown="onPointerDown"
      @pointermove="onPointerMove"
      @pointerup="onPointerUp"
      @pointercancel="onPointerUp"
      @pointerleave="onPointerUp"
    >
      <div class="mod-canvas" :style="canvasStyle" v-html="svgHtml" />
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { message } from '../api'
import { isDark } from '../theme'

const props = defineProps({
  svgSource: { type: String, default: '' },
  downloadName: { type: String, default: 'modules' },
  layout: { type: String, default: 'biz' },
})

const emit = defineEmits(['reload', 'update:layout'])

const PNG_SCALE = 2.5
const frameRef = ref(null)
const svgHtml = ref('')
const scale = ref(1)
const panX = ref(0)
const panY = ref(0)
const panning = ref(false)
const busy = ref(false)
const layoutLocal = ref(props.layout === 'side' ? 'side' : 'biz')
let panLastX = 0
let panLastY = 0

const SCALE_MIN = 0.25
const SCALE_MAX = 4
const SCALE_STEP = 0.15

const canvasStyle = computed(() => ({
  transform: `translate(${panX.value}px, ${panY.value}px) scale(${scale.value})`,
  transformOrigin: '0 0',
}))

const fileBase = computed(
  () => String(props.downloadName || 'modules').replace(/\.(svg|png)$/i, '') || 'modules',
)

watch(
  () => props.layout,
  (v) => {
    layoutLocal.value = v === 'side' ? 'side' : 'biz'
  },
)

function onLayoutChange(v) {
  const next = v === 'side' ? 'side' : 'biz'
  layoutLocal.value = next
  emit('update:layout', next)
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

function fitToFrame() {
  const frame = frameRef.value
  const svg = getSvg()
  if (!frame || !svg) return
  const vb = svg.viewBox?.baseVal
  const sw = vb?.width || Number(svg.getAttribute('width')) || 800
  const sh = vb?.height || Number(svg.getAttribute('height')) || 600
  const fw = frame.clientWidth || 800
  const fh = frame.clientHeight || 480
  const s = clampScale(Math.min(fw / sw, fh / sh) * 0.92)
  scale.value = s
  panX.value = (fw - sw * s) / 2
  panY.value = (fh - sh * s) / 2
}

function loadSource(raw) {
  svgHtml.value = parseSvg(raw)
  nextTick(() => fitToFrame())
}

watch(
  () => props.svgSource,
  (v) => loadSource(v),
  { immediate: true },
)

function zoomIn() {
  scale.value = clampScale(scale.value + SCALE_STEP)
}
function zoomOut() {
  scale.value = clampScale(scale.value - SCALE_STEP)
}
function resetView() {
  fitToFrame()
}

function onWheel(e) {
  const delta = e.deltaY > 0 ? -SCALE_STEP : SCALE_STEP
  scale.value = clampScale(scale.value + delta)
}

function onPointerDown(e) {
  if (e.button !== 0) return
  panning.value = true
  panLastX = e.clientX
  panLastY = e.clientY
  frameRef.value?.setPointerCapture?.(e.pointerId)
}

function onPointerMove(e) {
  if (!panning.value) return
  panX.value += e.clientX - panLastX
  panY.value += e.clientY - panLastY
  panLastX = e.clientX
  panLastY = e.clientY
}

function onPointerUp() {
  panning.value = false
}

function triggerDownload(blob, filename) {
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = filename
  a.click()
  URL.revokeObjectURL(a.href)
}

async function svgToCanvas() {
  const svg = getSvg()
  if (!svg) throw new Error('无图')
  const clone = svg.cloneNode(true)
  const vb = svg.viewBox?.baseVal
  const w = vb?.width || Number(svg.getAttribute('width')) || 800
  const h = vb?.height || Number(svg.getAttribute('height')) || 600
  const xml = new XMLSerializer().serializeToString(clone)
  const blob = new Blob([xml], { type: 'image/svg+xml;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  try {
    const img = await new Promise((resolve, reject) => {
      const i = new Image()
      i.onload = () => resolve(i)
      i.onerror = reject
      i.src = url
    })
    const canvas = document.createElement('canvas')
    canvas.width = Math.max(1, Math.round(w * PNG_SCALE))
    canvas.height = Math.max(1, Math.round(h * PNG_SCALE))
    const ctx = canvas.getContext('2d')
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
    return canvas
  } finally {
    URL.revokeObjectURL(url)
  }
}

async function copyPng() {
  if (busy.value) return
  busy.value = true
  try {
    const canvas = await svgToCanvas()
    const blob = await new Promise((r) => canvas.toBlob(r, 'image/png'))
    if (!navigator.clipboard?.write || typeof ClipboardItem === 'undefined') {
      triggerDownload(blob, `${fileBase.value}.png`)
      message.warning('当前环境不支持复制图片，已改为下载 PNG')
      return
    }
    try {
      await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })])
      message.success('已复制图片，可在 Word 中粘贴')
    } catch {
      triggerDownload(blob, `${fileBase.value}.png`)
      message.warning('复制失败，已改为下载 PNG')
    }
  } catch (e) {
    message.error(e?.message || '复制失败')
  } finally {
    busy.value = false
  }
}

async function downloadPng() {
  if (busy.value) return
  busy.value = true
  try {
    const canvas = await svgToCanvas()
    const blob = await new Promise((r) => canvas.toBlob(r, 'image/png'))
    triggerDownload(blob, `${fileBase.value}.png`)
    message.success('已下载 PNG，可直接插入 Word')
  } catch (e) {
    message.error(e?.message || '下载失败')
  } finally {
    busy.value = false
  }
}

function downloadSvg() {
  const raw = props.svgSource || ''
  const blob = new Blob([raw], { type: 'image/svg+xml;charset=utf-8' })
  triggerDownload(blob, `${fileBase.value}.svg`)
}

defineExpose({ downloadSvg, downloadPng, copyPng, resetView })
</script>

<style scoped>
.mod-toolbar {
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 8px;
}
.mod-zoom-btns {
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.mod-zoom-label {
  min-width: 48px;
  text-align: center;
  font-variant-numeric: tabular-nums;
  font-size: 13px;
  color: var(--muted);
}
.mod-hint {
  margin: 0;
}
.mod-frame {
  height: 72vh;
  overflow: hidden;
  border: 1px solid var(--line);
  background: var(--er-bg, #fafafa);
  cursor: grab;
  touch-action: none;
  user-select: none;
}
.mod-frame.is-panning,
.mod-frame:active {
  cursor: grabbing;
}
.mod-canvas {
  display: inline-block;
  will-change: transform;
}
.mod-canvas :deep(svg) {
  display: block;
  max-width: none;
  height: auto;
  overflow: visible;
}
/* 预览纸面透明，导出时仍是白底 */
.mod-canvas :deep(.er-paper) {
  fill: transparent !important;
}
/* 与 E-R 夜间一致：只反相图元，不整页大黑底 */
.mod-viewer.is-dark .mod-frame {
  background: #0f161e;
}
.mod-viewer.is-dark .mod-canvas {
  filter: invert(1) hue-rotate(180deg);
}
</style>
