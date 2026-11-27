<template>
  <div ref="viewerRef" class="mod-viewer diagram-viewer-shell" :class="{ 'is-dark': isDark, 'is-resizing': resizing }">
    <div class="diagram-chrome">
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
          <n-button
            size="small"
            :loading="loading"
            :title="labelGateBad ? '强制重算（绕过图缓存；修 modules.py 后必点）' : '重新加载'"
            @click="$emit('reload')"
          >重新加载</n-button>
          <n-button
            size="small"
            type="primary"
            :loading="busy"
            :disabled="exportBad"
            :title="exportBlockTitle"
            @click="copyPng"
          >复制图片</n-button>
          <n-button
            size="small"
            type="primary"
            secondary
            :loading="busy"
            :disabled="exportBad"
            :title="exportBlockTitle"
            @click="downloadPng"
          >下载 PNG</n-button>
          <n-button
            size="small"
            quaternary
            :disabled="exportBad"
            :title="exportBlockTitle"
            @click="downloadSvg"
          >下载矢量源</n-button>
          <n-button
            size="small"
            quaternary
            :loading="drawioBusy"
            :disabled="exportBad"
            :title="exportBlockTitle || '同源 Draw.io，可拖框手调'"
            @click="downloadDrawio"
          >下载 Draw.io</n-button>
          <n-button
            size="small"
            quaternary
            :loading="mmdBusy"
            :disabled="exportBad || !mermaidUrl"
            :title="exportBlockTitle"
            @click="copyMermaid"
          >复制 Mermaid</n-button>
          <n-button
            size="small"
            quaternary
            :loading="mmdBusy"
            :disabled="exportBad || !mermaidUrl"
            :title="exportBlockTitle"
            @click="downloadMermaid"
          >下载 .mmd</n-button>
        </div>
      </div>
      <p class="small muted mod-hint mb-8">
        {{
          layoutLocal === 'biz'
            ? '按业务拆：业务对象 / 订单…（对照用）；叶子来自交付菜单'
            : '按身份拆：登录身份 → 一级功能模块（论文常用）；叶子对齐交付菜单，开题只辅助命名；未交付模块不进图（差项见下方弱提醒）；【】（）细节默认不进图'
        }}
      </p>
      <p v-if="layoutMismatch" class="small mod-hint mb-8 mod-warn">
        界面为「按身份」，图数据仍是「按业务」· 重启后端后重新加载。
      </p>
      <p
        v-if="sourceNote"
        class="small mod-hint mb-8 mod-source-note"
        :class="labelGateBad ? 'mod-warn' : 'muted'"
      >{{ sourceNote }}</p>
      <div v-if="deliveryGapWarn" class="banner warn mod-gap-banner mb-8">
        <h4>开题对账 · 弱提醒（不挡导出）</h4>
        <p class="small">
          开题里点名了、当前交付菜单对不上的模块<strong>没有画进图</strong>。
          图仍只反映已交付功能。把下面当作施工清单：补匹配确认 / 能力后重 bake，再点「重新加载」。
          完善工厂后同类项会越来越少。
        </p>
        <ul v-if="droppedRows.length" class="small mod-findings">
          <li v-for="(row, i) in droppedRows" :key="'d' + i">
            <strong>未进图</strong>
            <span v-if="row.branch" class="muted"> · {{ row.branch }}</span>
            → 「{{ row.label }}」
          </li>
        </ul>
        <details v-if="paddedRows.length" class="mod-gap-padded">
          <summary class="small muted">开题未点名、菜单有（图上多出 · {{ paddedRows.length }}）</summary>
          <ul class="small mod-findings">
            <li v-for="(row, i) in paddedRows" :key="'p' + i">
              <span v-if="row.branch" class="muted">{{ row.branch }} → </span>「{{ row.label }}」
            </li>
          </ul>
        </details>
      </div>
      <div v-if="labelGateBad" class="banner fail mod-gate-banner mb-8">
        <h4>工厂提示 · 文案红</h4>
        <p class="small">
          叶子短签未过闸，勿当可贴论文图发出。修工厂
          <code>backend/app/bake/schema/modules.py</code>
          清洗（勿只擦本包 SVG）→ 热重载后端 → 点「重新加载」强制重算缓存。
          仅交付菜单 / domain.schema 叶子本身错时才重 bake。
        </p>
        <ul v-if="findingRows.length" class="small mod-findings">
          <li v-for="(row, i) in findingRows" :key="i">
            <strong>{{ row.kindZh }}</strong>
            <span v-if="row.sourceZh" class="muted"> · {{ row.sourceZh }}</span>
            · {{ row.branch || '（根）' }} → 「{{ row.label || '（空）' }}」
            <span class="muted">{{ row.detail }}</span>
          </li>
        </ul>
      </div>
      <DiagramRubricBanner :gate="rubricGate" />
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
      class="mod-frame"
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
      <div v-else class="mod-canvas" :style="canvasStyle" v-html="svgHtml" />
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import {
  PNG_SCALE_DEFAULT,
  copyMermaidUrl,
  copyPngFromSvgDom,
  downloadDrawioUrl,
  downloadMermaidUrl,
  downloadPngFromSvgDom,
  downloadSvgText,
} from '../utils/diagramExport'
import { message } from '../api'
import { isDark } from '../theme'
import ContentLoading from './ContentLoading.vue'
import DiagramRubricBanner from './DiagramRubricBanner.vue'
import { useDiagramFrameResize } from './useDiagramFrameResize'
import { watchFrameHeightFit } from '../utils/diagramFitDebounce'

const props = defineProps({
  svgSource: { type: String, default: '' },
  downloadName: { type: String, default: 'modules' },
  layout: { type: String, default: 'identity' },
  /** 接口返回的 layout，用于发现前后端不一致 */
  resolvedLayout: { type: String, default: '' },
  expandDetails: { type: Boolean, default: false },
  sourceNote: { type: String, default: '' },
  /** 叶子文案机器闸：false 时提示加红 */
  labelGateOk: { type: Boolean, default: true },
  /** label_gate.findings：kind/branch/label/detail，可选 source */
  labelGateFindings: { type: Array, default: () => [] },
  /** 开题∩交付差账：dropped 弱提醒；不挡导出 */
  deliveryGap: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  drawioUrl: { type: String, default: '' },
  mermaidUrl: { type: String, default: '' },
  rubricGate: { type: Object, default: null },
})

const emit = defineEmits(['reload', 'update:layout', 'update:expandDetails'])

const labelGateBad = computed(() => props.labelGateOk === false)
const rubricBad = computed(() => props.rubricGate && props.rubricGate.ok === false)
const exportBad = computed(() => labelGateBad.value || rubricBad.value)
const exportBlockTitle = computed(() => {
  if (labelGateBad.value) return '文案红不可导出，先按工厂提示修闸'
  if (rubricBad.value) return String(props.rubricGate?.note || '论文图规则红，不可导出')
  return undefined
})

const deliveryGapWarn = computed(() => {
  const g = props.deliveryGap
  if (!g || typeof g !== 'object') return false
  if (g.severity === 'warn') return true
  return Array.isArray(g.dropped) && g.dropped.length > 0
})

const droppedRows = computed(() => {
  const list = Array.isArray(props.deliveryGap?.dropped) ? props.deliveryGap.dropped : []
  return list.slice(0, 40).map((r) => ({
    branch: String(r?.branch || '').trim(),
    label: String(r?.label || '').trim() || '（空）',
  }))
})

const paddedRows = computed(() => {
  const list = Array.isArray(props.deliveryGap?.padded) ? props.deliveryGap.padded : []
  return list.slice(0, 40).map((r) => ({
    branch: String(r?.branch || '').trim(),
    label: String(r?.label || '').trim() || '（空）',
  }))
})

const KIND_ZH = {
  empty: '空叶子',
  prose: '散文/泄漏',
  suffix: '模块/功能尾',
  etc: '「等」收尾',
  glue: '并列未切开',
  role_prefix: '复读角色前缀',
  too_long: '超长',
}

const SOURCE_ZH = {
  machine: '机器',
  override: '手调',
}

const findingRows = computed(() => {
  const list = Array.isArray(props.labelGateFindings) ? props.labelGateFindings : []
  return list.slice(0, 30).map((f) => ({
    kindZh: KIND_ZH[f?.kind] || f?.kind || '闸红',
    sourceZh: SOURCE_ZH[f?.source] || '',
    branch: String(f?.branch || '').trim(),
    label: String(f?.label || '').trim(),
    detail: String(f?.detail || '').trim(),
  }))
})

const PNG_SCALE = PNG_SCALE_DEFAULT
const frameRef = ref(null)
const svgHtml = ref('')
const scale = ref(1)
const panX = ref(0)
const panY = ref(0)
const panning = ref(false)
const busy = ref(false)
const drawioBusy = ref(false)
const mmdBusy = ref(false)
const layoutLocal = ref(props.layout === 'biz' ? 'biz' : 'identity')
const expandLocal = ref(!!props.expandDetails)
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

watchFrameHeightFit(frameHeight, fitToFrame)

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

async function copyPng() {
  busy.value = true
  try {
    await copyPngFromSvgDom(getSvg, {
      scale: PNG_SCALE,
      okText: '已复制图片',
      failText: '复制失败，可改下 PNG',
    })
  } finally {
    busy.value = false
  }
}

async function downloadPng() {
  busy.value = true
  try {
    await downloadPngFromSvgDom(getSvg, `${fileBase.value}.png`, {
      scale: PNG_SCALE,
      failText: '下载 PNG 失败',
    })
  } finally {
    busy.value = false
  }
}

function downloadSvg() {
  downloadSvgText(props.svgSource || '', `${fileBase.value}.svg`)
}

async function downloadDrawio() {
  if (exportBad.value) {
    message.error(exportBlockTitle.value || '不可导出')
    return
  }
  drawioBusy.value = true
  try {
    await downloadDrawioUrl(props.drawioUrl, `${fileBase.value}.drawio`)
  } finally {
    drawioBusy.value = false
  }
}

async function copyMermaid() {
  if (exportBad.value) {
    message.error(exportBlockTitle.value || '不可导出')
    return
  }
  mmdBusy.value = true
  try {
    await copyMermaidUrl(props.mermaidUrl, {
      okText: '已复制 Mermaid（可贴 diagrams.net）',
      failText: '复制 Mermaid 失败',
      
    })
  } finally {
    mmdBusy.value = false
  }
}

async function downloadMermaid() {
  if (exportBad.value) {
    message.error(exportBlockTitle.value || '不可导出')
    return
  }
  mmdBusy.value = true
  try {
    await downloadMermaidUrl(props.mermaidUrl, `${fileBase.value}.mmd`, {
      failText: '下载 Mermaid 失败',
      
    })
  } finally {
    mmdBusy.value = false
  }
}

</script>

<style scoped>
/* 高度 / 拖条见 styles.css · .diagram-viewer-shell */
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
.mod-gate-banner,
.mod-gap-banner {
  margin: 0;
}
.mod-gate-banner code {
  font-size: 0.92em;
}
.mod-gap-padded {
  margin-top: 8px;
}
.mod-gap-padded summary {
  cursor: pointer;
  user-select: none;
}
.mod-findings {
  margin: 8px 0 0;
  padding-left: 1.2em;
  max-height: 9.5em;
  overflow: auto;
  line-height: 1.45;
}
.mod-findings li + li {
  margin-top: 4px;
}
.mod-frame {
  flex: 0 0 auto;
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
