<template>
  <div class="uc-viewer" :class="{ 'is-dark': isDark }">
    <div class="uc-toolbar row mb-12">
      <div class="uc-zoom-btns row">
        <n-radio-group
          v-if="actorOptions.length"
          :value="actorLocal"
          size="small"
          :disabled="loading"
          @update:value="onActorChange"
        >
          <n-radio-button v-for="a in actorOptions" :key="a.id" :value="a.id">
            {{ a.label }}
          </n-radio-button>
        </n-radio-group>
        <n-button size="small" @click="zoomOut">缩小</n-button>
        <span class="uc-zoom-label">{{ Math.round(scale * 100) }}%</span>
        <n-button size="small" @click="zoomIn">放大</n-button>
        <n-button size="small" @click="resetView">重置视口</n-button>
        <n-button size="small" :loading="loading" @click="$emit('reload')">重新加载</n-button>
        <n-button size="small" type="primary" :loading="busy" @click="copyPng">复制图片</n-button>
        <n-button size="small" type="primary" secondary :loading="busy" @click="downloadPng">下载 PNG</n-button>
        <n-button size="small" quaternary @click="downloadSvg">下载矢量源</n-button>
        <n-button size="small" quaternary :loading="mdjBusy" @click="downloadMdj">下载 StarUML (.mdj)</n-button>
      </div>
    </div>
    <p class="small muted uc-hint mb-8">
      <template v-if="styleRules.length">
        客户画法 ·
        <span v-for="(r, i) in styleRules" :key="i">
          {{ i + 1 }}.{{ r }}{{ i < styleRules.length - 1 ? '；' : '' }}
        </span>
      </template>
      <template v-else>
        按角色走查（含岗位）· 一级恰好 5 个 · 虚线
        <code>&lt;&lt;include&gt;&gt;</code> /
        <code>&lt;&lt;extend&gt;&gt;</code>
        · 二级动词开头 · 可导出 StarUML
      </template>
    </p>
    <p v-if="sourceNote" class="small muted uc-hint mb-8">{{ sourceNote }}</p>
    <div v-if="description" class="uc-desc mb-8">
      <div class="row" style="justify-content:space-between;align-items:flex-start;gap:8px">
        <p class="small uc-desc-text">{{ description }}</p>
        <n-button size="tiny" quaternary @click="copyDesc">复制描述</n-button>
      </div>
    </div>
    <div
      ref="frameRef"
      class="uc-frame"
      :class="{ 'is-panning': panning }"
      @wheel.prevent="onWheel"
      @pointerdown="onPointerDown"
      @pointermove="onPointerMove"
      @pointerup="onPointerUp"
      @pointercancel="onPointerUp"
      @pointerleave="onPointerUp"
    >
      <ContentLoading v-if="loading && !svgSource" :rows="1" block compact />
      <div v-else class="uc-canvas" :style="canvasStyle" v-html="svgHtml" />
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
  downloadName: { type: String, default: 'usecases' },
  actor: { type: String, default: 'user' },
  actors: { type: Array, default: () => [] },
  description: { type: String, default: '' },
  sourceNote: { type: String, default: '' },
  styleRules: { type: Array, default: () => [] },
  mdjUrl: { type: String, default: '' },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['reload', 'update:actor'])

const PNG_SCALE = 2.5
const frameRef = ref(null)
const svgHtml = ref('')
const scale = ref(1)
const panX = ref(0)
const panY = ref(0)
const panning = ref(false)
const busy = ref(false)
const mdjBusy = ref(false)
const actorLocal = ref(String(props.actor || 'user'))
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
  () => String(props.downloadName || 'usecases').replace(/\.(svg|png|mdj)$/i, '') || 'usecases',
)

const actorOptions = computed(() => {
  const list = Array.isArray(props.actors) ? props.actors : []
  if (list.length) return list.map((a) => ({ id: a.id, label: a.label || a.id }))
  return [
    { id: 'user', label: '用户' },
    { id: 'admin', label: '管理员' },
  ]
})

watch(
  () => props.actor,
  (v) => {
    actorLocal.value = String(v || 'user')
  },
)

function onActorChange(v) {
  const next = String(v || 'user')
  actorLocal.value = next
  emit('update:actor', next)
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

async function downloadMdj() {
  const url = props.mdjUrl
  if (!url) {
    message.error('无 StarUML 下载地址')
    return
  }
  mdjBusy.value = true
  try {
    const res = await fetch(`${url}${url.includes('?') ? '&' : '?'}t=${Date.now()}`)
    if (!res.ok) throw new Error('mdj')
    const text = await res.text()
    triggerDownload(new Blob([text], { type: 'application/json;charset=utf-8' }), `${fileBase.value}.mdj`)
  } catch {
    message.error('下载 .mdj 失败')
  } finally {
    mdjBusy.value = false
  }
}

async function copyDesc() {
  try {
    await navigator.clipboard.writeText(props.description || '')
    message.success('已复制描述')
  } catch {
    message.error('复制描述失败')
  }
}
</script>

<style scoped>
.uc-viewer {
  display: flex;
  flex-direction: column;
  gap: 0;
  max-height: min(86vh, 900px);
}
.uc-toolbar {
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  flex-shrink: 0;
}
.uc-zoom-btns {
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.uc-zoom-label {
  min-width: 3.2em;
  text-align: center;
  font-variant-numeric: tabular-nums;
}
.uc-hint {
  line-height: 1.45;
  flex-shrink: 0;
}
.uc-desc {
  padding: 10px 12px;
  border: 1px solid var(--n-border-color);
  border-radius: 6px;
  background: var(--n-color-embedded, #fafafa);
  flex-shrink: 0;
  max-height: 7.5em;
  overflow: auto;
}
.uc-desc-text {
  margin: 0;
  line-height: 1.65;
  white-space: pre-wrap;
}
.uc-frame {
  /* 与 E-R 图同口径：固定视口，避免 SVG 固有高度把弹窗撑开 */
  position: relative;
  height: 52vh;
  min-height: 320px;
  flex: 0 0 auto;
  overflow: hidden;
  border: 1px solid var(--n-border-color);
  border-radius: 6px;
  background: #fff;
  cursor: grab;
  touch-action: none;
}
.uc-frame.is-panning {
  cursor: grabbing;
}
.uc-viewer.is-dark .uc-frame {
  background: #111;
}
.uc-viewer.is-dark .uc-desc {
  background: rgba(255, 255, 255, 0.04);
}
.uc-canvas {
  position: absolute;
  left: 0;
  top: 0;
  display: inline-block;
  will-change: transform;
  transform-origin: 0 0;
}
.uc-canvas :deep(svg) {
  display: block;
  max-width: none;
}
</style>
