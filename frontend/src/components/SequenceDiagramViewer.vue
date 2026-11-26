<template>
  <div ref="viewerRef" class="seq-viewer diagram-viewer-shell" :class="{ 'is-dark': isDark, 'is-resizing': resizing }">
    <div class="diagram-chrome">
      <div class="seq-toolbar row mb-12">
        <div class="seq-zoom-btns row">
          <n-button size="small" @click="zoomOut">缩小</n-button>
          <span class="seq-zoom-label">{{ Math.round(scale * 100) }}%</span>
          <n-button size="small" @click="zoomIn">放大</n-button>
          <n-button size="small" @click="resetView">重置视口</n-button>
          <n-button size="small" :loading="loading" @click="$emit('reload')">重新加载</n-button>
          <n-button size="small" type="primary" :loading="busy" :disabled="rubricBad" :title="exportBlockTitle" @click="copyPng">复制当前图</n-button>
          <n-button size="small" type="primary" secondary :loading="busy" :disabled="rubricBad" :title="exportBlockTitle" @click="downloadPng">下载当前 PNG</n-button>
          <n-button size="small" quaternary :disabled="rubricBad" :title="exportBlockTitle" @click="downloadSvg">下载当前矢量源</n-button>
          <n-button size="small" quaternary :loading="mmdBusy" :disabled="rubricBad || !mermaidUrl" :title="exportBlockTitle" @click="copyMermaid">复制当前 Mermaid</n-button>
          <n-button size="small" quaternary :loading="mmdBusy" :disabled="rubricBad || !mermaidUrl" :title="exportBlockTitle" @click="downloadMermaid">下载当前 .mmd</n-button>
        </div>
      </div>
      <DiagramRubricBanner :gate="rubricGate" />
      <p class="small muted seq-hint mb-8">
        固定 3 张核心功能序列图：交付角色 / 页面 / 控制器 / 数据库；生命线 + 分段变长激活条；往库实线带 ()、往角色虚线无 ()；阶梯序号。文案取自 bake 包。Mermaid 与图同源，可贴 diagrams.net 作参考。
      </p>
      <div class="seq-pick mb-8">
        <div class="small muted mb-6">从交付功能中勾选恰好 3 个（已选 {{ localIds.length }} / 3）</div>
        <div class="seq-cand-list">
          <label v-for="c in candidates" :key="c.id" class="seq-cand">
            <input
              type="checkbox"
              :value="c.id"
              :checked="localIds.includes(c.id)"
              :disabled="!localIds.includes(c.id) && localIds.length >= 3"
              @change="onToggle(c.id, $event.target.checked)"
            />
            <span>{{ c.name || c.label }}</span>
            <span class="seq-cand-meta muted">{{ c.actor }}</span>
          </label>
        </div>
        <n-button
          size="small"
          type="primary"
          class="mt-8"
          :disabled="localIds.length !== 3"
          :loading="loading"
          @click="applySelection"
        >应用所选并出图</n-button>
      </div>
      <div v-if="diagrams.length" class="seq-tabs row mb-8">
        <n-button
          v-for="(d, i) in diagrams"
          :key="d.id || i"
          size="small"
          :type="i === diagramIndex ? 'primary' : 'default'"
          @click="$emit('update:diagramIndex', i)"
        >图{{ i + 1 }} · {{ shortTitle(d.figure_title) }}</n-button>
      </div>
      <p v-if="sourceNote" class="small muted seq-hint mb-8">{{ sourceNote }}</p>
      <div v-if="currentWorkflow" class="seq-workflow mb-8">
        <div class="seq-workflow-head row">
          <span class="seq-workflow-title">{{ currentWorkflow.title }}</span>
          <n-button size="tiny" quaternary :disabled="!currentWorkflow.plain" @click="copyWorkflow">复制工作流程</n-button>
        </div>
        <p class="small muted seq-hint mb-6">{{ currentWorkflow.source_note || '由本张序列图逐步改写，换题随勾选变化；不套示例范文。' }}</p>
        <ol class="seq-workflow-steps">
          <li v-for="s in currentWorkflow.steps || []" :key="s.n">{{ s.text }}</li>
        </ol>
      </div>
    </div>
    <div
      class="diagram-resize"
      title="拖动调整预览高度"
      @pointerdown="onResizeDown"
      @pointermove="onResizeMove"
      @pointerup="onResizeUp"
      @pointercancel="onResizeUp"
    />
    <div
      ref="frameRef"
      class="seq-frame"
      :class="{ 'is-panning': panning }"
      :style="frameStyle"
      @wheel.prevent="onWheel"
      @pointerdown="onPointerDown"
      @pointermove="onPointerMove"
      @pointerup="onPointerUp"
      @pointercancel="onPointerUp"
      @pointerleave="onPointerUp"
    >
      <ContentLoading v-if="loading && !svgSource" :rows="1" block compact />
      <div v-else class="seq-canvas" :style="canvasStyle" v-html="svgHtml" />
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { message } from '../api'
import { isDark } from '../theme'
import ContentLoading from './ContentLoading.vue'
import DiagramRubricBanner from './DiagramRubricBanner.vue'
import { useDiagramFrameResize } from './useDiagramFrameResize'

const props = defineProps({
  svgSource: { type: String, default: '' },
  downloadName: { type: String, default: 'sequence' },
  mermaidUrl: { type: String, default: '' },
  sourceNote: { type: String, default: '' },
  loading: { type: Boolean, default: false },
  candidates: { type: Array, default: () => [] },
  selectedIds: { type: Array, default: () => [] },
  diagrams: { type: Array, default: () => [] },
  diagramIndex: { type: Number, default: 0 },
  rubricGate: { type: Object, default: null },
})

const rubricBad = computed(() => props.rubricGate && props.rubricGate.ok === false)
const exportBlockTitle = computed(() =>
  rubricBad.value ? String(props.rubricGate?.note || '论文图规则红，不可导出') : undefined,
)

const emit = defineEmits(['reload', 'apply-selection', 'update:diagramIndex'])

const PNG_SCALE = 2.5
const frameRef = ref(null)
const svgHtml = ref('')
const scale = ref(1)
const panX = ref(0)
const panY = ref(0)
const panning = ref(false)
const busy = ref(false)
const mmdBusy = ref(false)
const localIds = ref([])
let panLastX = 0
let panLastY = 0

const {
  viewerRef,
  frameHeight,
  frameStyle,
  resizing,
  onResizeDown,
  onResizeMove,
  onResizeUp,
} = useDiagramFrameResize()

watch(frameHeight, async () => {
  await nextTick()
  fitToFrame()
})

const SCALE_MIN = 0.25
const SCALE_MAX = 4
const SCALE_STEP = 0.15

watch(
  () => props.selectedIds,
  (ids) => {
    localIds.value = Array.isArray(ids) ? [...ids] : []
  },
  { immediate: true },
)

const canvasStyle = computed(() => ({
  transform: `translate(${panX.value}px, ${panY.value}px) scale(${scale.value})`,
  transformOrigin: '0 0',
}))

const fileBase = computed(
  () => String(props.downloadName || 'sequence').replace(/\.(svg|png)$/i, '') || 'sequence',
)

watch(
  () => props.svgSource,
  async (raw) => {
    const text = String(raw || '')
    svgHtml.value = text.replace(/<\?xml[^?]*\?>/i, '').trim()
    await nextTick()
    fitToFrame()
  },
  { immediate: true },
)

function shortTitle(t) {
  const s = String(t || '').replace(/序列图$/u, '')
  return s.length > 12 ? `${s.slice(0, 12)}…` : s || '功能'
}

const currentWorkflow = computed(() => {
  const list = props.diagrams || []
  const d = list[props.diagramIndex]
  const wf = d && d.workflow
  if (!wf || !Array.isArray(wf.steps) || !wf.steps.length) return null
  return wf
})

async function copyWorkflow() {
  const plain = String(currentWorkflow.value?.plain || '').trim()
  if (!plain) {
    message.warning('暂无工作流程文案')
    return
  }
  try {
    const { copyMaterialText } = await import('../utils/zhCopy')
    await copyMaterialText(plain)
    message.success('已复制工作流程（可贴论文）')
  } catch {
    message.error('复制失败')
  }
}

function onToggle(id, checked) {
  if (checked) {
    if (localIds.value.length >= 3) return
    if (!localIds.value.includes(id)) localIds.value = [...localIds.value, id]
  } else {
    localIds.value = localIds.value.filter((x) => x !== id)
  }
}

function applySelection() {
  if (localIds.value.length !== 3) {
    message.warning('请恰好勾选 3 个交付功能')
    return
  }
  emit('apply-selection', [...localIds.value])
}

function getSvg() {
  return frameRef.value?.querySelector('svg') || null
}

function fitToFrame() {
  const frame = frameRef.value
  const svg = getSvg()
  if (!frame || !svg) return
  const vb = svg.viewBox?.baseVal
  const sw = vb?.width || Number(svg.getAttribute('width')) || 800
  const sh = vb?.height || Number(svg.getAttribute('height')) || 600
  const fw = frame.clientWidth - 24
  const fh = frame.clientHeight - 24
  if (fw <= 0 || fh <= 0 || sw <= 0 || sh <= 0) return
  const s = Math.min(fw / sw, fh / sh, 1.2)
  scale.value = Math.max(SCALE_MIN, Math.min(SCALE_MAX, s))
  panX.value = Math.max(0, (fw - sw * scale.value) / 2)
  panY.value = 12
}

function zoomIn() {
  scale.value = Math.min(SCALE_MAX, scale.value + SCALE_STEP)
}
function zoomOut() {
  scale.value = Math.max(SCALE_MIN, scale.value - SCALE_STEP)
}
function resetView() {
  fitToFrame()
}

function onWheel(e) {
  const delta = e.deltaY > 0 ? -SCALE_STEP : SCALE_STEP
  scale.value = Math.min(SCALE_MAX, Math.max(SCALE_MIN, scale.value + delta))
}

function onPointerDown(e) {
  if (e.button !== 0) return
  panning.value = true
  panLastX = e.clientX
  panLastY = e.clientY
  e.currentTarget?.setPointerCapture?.(e.pointerId)
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
    message.success('已复制当前图')
  } catch {
    message.error('复制失败，可改下当前 PNG')
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
    message.error('下载当前 PNG 失败')
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

async function fetchMermaidText() {
  const url = props.mermaidUrl
  if (!url) throw new Error('no mermaid url')
  const res = await fetch(url, { credentials: 'include' })
  if (!res.ok) throw new Error('mmd')
  return await res.text()
}

async function copyMermaid() {
  mmdBusy.value = true
  try {
    const text = await fetchMermaidText()
    await navigator.clipboard.writeText(text)
    message.success('已复制当前 Mermaid（可贴 diagrams.net）')
  } catch {
    message.error('复制当前 Mermaid 失败')
  } finally {
    mmdBusy.value = false
  }
}

async function downloadMermaid() {
  mmdBusy.value = true
  try {
    const text = await fetchMermaidText()
    triggerDownload(new Blob([text], { type: 'text/plain;charset=utf-8' }), `${fileBase.value}.mmd`)
  } catch {
    message.error('下载当前 Mermaid 失败')
  } finally {
    mmdBusy.value = false
  }
}
</script>

<style scoped>
/* 高度 / 拖条见 styles.css · .diagram-viewer-shell */
.seq-toolbar {
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.seq-zoom-btns {
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.seq-zoom-label {
  min-width: 48px;
  text-align: center;
  font-variant-numeric: tabular-nums;
  font-size: 12px;
  color: var(--muted);
}
.seq-hint { line-height: 1.5; }
.seq-cand-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  max-height: 120px;
  overflow: auto;
}
.seq-cand {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  cursor: pointer;
}
.seq-cand-meta {
  font-size: 12px;
}
.seq-tabs {
  flex-wrap: wrap;
  gap: 8px;
}
.seq-workflow {
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 10px 12px;
  background: var(--card, transparent);
  max-height: 220px;
  overflow: auto;
}
.seq-workflow-head {
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}
.seq-workflow-title {
  font-size: 13px;
  font-weight: 600;
}
.seq-workflow-steps {
  margin: 0;
  padding-left: 1.4em;
  font-size: 13px;
  line-height: 1.65;
}
.seq-workflow-steps li {
  margin: 0 0 2px;
}
.seq-frame {
  flex: 0 0 auto;
  overflow: hidden;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: #fff;
  cursor: grab;
  position: relative;
}
.seq-frame.is-panning { cursor: grabbing; }
.seq-viewer.is-dark .seq-frame {
  background: #f7f7f7;
}
.seq-canvas {
  display: inline-block;
  will-change: transform;
}
.seq-canvas :deep(svg) {
  display: block;
}
.mt-8 { margin-top: 8px; }
</style>
