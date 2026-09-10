<template>
  <div class="mod-viewer" :class="{ 'is-dark': isDark }">
    <div class="mod-toolbar row mb-12">
      <div class="mod-zoom-btns row">
        <n-radio-group v-model:value="layoutLocal" size="small" :disabled="loading" @update:value="onLayoutChange">
          <n-radio-button value="identity">按身份</n-radio-button>
          <n-radio-button value="biz">按业务</n-radio-button>
        </n-radio-group>
        <n-switch
          size="small"
          :value="expandLocal"
          :disabled="loading || layoutLocal !== 'identity'"
          @update:value="onExpandChange"
        >
          <template #checked>展开细节</template>
          <template #unchecked>展开细节</template>
        </n-switch>
        <n-button size="small" @click="zoomOut">缩小</n-button>
        <span class="mod-zoom-label">{{ Math.round(scale * 100) }}%</span>
        <n-button size="small" @click="zoomIn">放大</n-button>
        <n-button size="small" @click="resetView">重置视口</n-button>
        <n-button size="small" :loading="loading" @click="$emit('reload')">重新加载</n-button>
        <n-button size="small" type="primary" :loading="busy" @click="copyPng">复制图片</n-button>
        <n-button size="small" type="primary" secondary :loading="busy" @click="downloadPng">下载 PNG</n-button>
        <n-button size="small" quaternary @click="downloadSvg">下载矢量源</n-button>
      </div>
    </div>
    <p class="small muted mod-hint mb-8">
      {{
        layoutLocal === 'biz'
          ? '按业务拆：业务对象 / 订单…（对照用）'
          : '按身份拆：登录身份 → 一级功能模块（论文常用）；【】（）细节默认不进图'
      }}
      ；优先读开题等材料枚举。
    </p>
    <p v-if="layoutMismatch" class="small mod-hint mb-8 mod-warn">
      界面选的是「按身份」，但图数据仍是「按业务」——请重启工厂后端后再点重新加载。
    </p>
    <p v-if="sourceNote" class="small muted mod-hint mb-8 mod-source-note">{{ sourceNote }}</p>
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
      <ContentLoading v-if="loading && !svgSource" :rows="1" block compact />
      <div v-else class="mod-canvas" :style="canvasStyle" v-html="svgHtml" />
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { message } from '../api'
import { isDark } from '../theme'
import ContentLoading from './ContentLoading.vue'

const props = defineProps({
  svgSource: { type: String, default: '' },
  downloadName: { type: String, default: 'modules' },
  layout: { type: String, default: 'identity' },
  /** 接口返回的 layout，用于发现前后端不一致 */
  resolvedLayout: { type: String, default: '' },
  expandDetails: { type: Boolean, default: false },
  sourceNote: { type: String, default: '' },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['reload', 'update:layout', 'update:expandDetails'])

const PNG_SCALE = 2.5
const frameRef = ref(null)
const svgHtml = ref('')
const scale = ref(1)
const panX = ref(0)
const panY = ref(0)
const panning = ref(false)
const busy = ref(false)
const layoutLocal = ref(props.layout === 'biz' ? 'biz' : 'identity')
const expandLocal = ref(!!props.expandDetails)
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

const layoutMismatch = computed(() => {
  const want = layoutLocal.value === 'biz' ? 'biz' : 'identity'
  const got = String(props.resolvedLayout || '').trim()
  return want === 'identity' && got === 'biz'
})

watch(
  () => props.layout,
  (v) => {
    layoutLocal.value = v === 'biz' ? 'biz' : 'identity'
  },
)

watch(
  () => props.expandDetails,
  (v) => {
    expandLocal.value = !!v
  },
)

function onLayoutChange(v) {
  const next = v === 'biz' ? 'biz' : 'identity'
  layoutLocal.value = next
  emit('update:layout', next)
}

function onExpandChange(v) {
  expandLocal.value = !!v
  emit('update:expandDetails', !!v)
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
  clone.setAttribute('width', String(w))
  clone.setAttribute('height', String(h))
  const xml = new XMLSerializer().serializeToString(clone)
  const url = URL.createObjectURL(new Blob([xml], { type: 'image/svg+xml;charset=utf-8' }))
  try {
    const img = new Image()
    await new Promise((resolve, reject) => {
      img.onload = resolve
      img.onerror = reject
      img.src = url
    })
    const canvas = document.createElement('canvas')
    canvas.width = Math.round(w * PNG_SCALE)
    canvas.height = Math.round(h * PNG_SCALE)
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
  busy.value = true
  try {
    const canvas = await svgToCanvas()
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/png'))
    if (!blob) throw new Error('png')
    await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })])
    message.success('已复制图片')
  } catch {
    message.error('复制失败，可改下 PNG')
  } finally {
    busy.value = false
  }
}

async function downloadPng() {
  busy.value = true
  try {
    const canvas = await svgToCanvas()
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/png'))
    if (!blob) throw new Error('png')
    triggerDownload(blob, `${fileBase.value}.png`)
  } catch {
    message.error('下载 PNG 失败')
  } finally {
    busy.value = false
  }
}

function downloadSvg() {
  const raw = props.svgSource || ''
  if (!raw) {
    message.error('无矢量源')
    return
  }
  triggerDownload(new Blob([raw], { type: 'image/svg+xml;charset=utf-8' }), `${fileBase.value}.svg`)
}
</script>

<style scoped>
.mod-viewer {
  display: flex;
  flex-direction: column;
  min-height: 420px;
}
.mod-toolbar {
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.mod-zoom-btns {
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.mod-zoom-label {
  min-width: 3.2em;
  text-align: center;
  font-variant-numeric: tabular-nums;
}
.mod-hint {
  line-height: 1.45;
}
.mod-source-note {
  color: var(--n-text-color-3, #888);
}
.mod-warn {
  color: #c45c26;
}
.mod-frame {
  flex: 1;
  min-height: 360px;
  overflow: hidden;
  border: 1px solid var(--n-border-color);
  border-radius: 6px;
  background: #fff;
  cursor: grab;
  touch-action: none;
}
.mod-frame.is-panning {
  cursor: grabbing;
}
.mod-viewer.is-dark .mod-frame {
  background: #111;
}
.mod-canvas {
  display: inline-block;
  will-change: transform;
}
.mod-canvas :deep(svg) {
  display: block;
}
</style>
