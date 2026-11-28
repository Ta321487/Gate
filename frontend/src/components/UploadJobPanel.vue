<template>
  <div v-if="jobs.length" class="uj-panel mb-16">
    <div class="uj-hd">
      <div class="uj-hd-main">
        <h3>{{ title }}</h3>
        <span v-if="statusPill" class="uj-pill" :class="statusPillClass">{{ statusPill }}</span>
      </div>
      <span v-if="hint" class="small muted uj-hint">{{ hint }}</span>
    </div>

    <!-- 多条时先看总览，避免 20 行墙 -->
    <div v-if="useCompact" class="uj-overview">
      <div class="uj-overview-top">
        <div class="uj-overview-copy">
          <div class="uj-overview-title">{{ overviewTitle }}</div>
          <div v-if="overviewSub" class="small muted">{{ overviewSub }}</div>
        </div>
        <button type="button" class="uj-toggle" @click="expanded = !expanded">
          {{ expanded ? '收起明细' : `明细 ${jobs.length}` }}
        </button>
      </div>
      <!-- 整批有总数：用落定/总数画定长条；否则走动条 -->
      <div v-if="totalCount > 0 && (Number(batchTotal) > 0 || settledCount > 0 || !busyCount)" class="progress">
        <i
          :style="{
            width: donePct + '%',
            background: settledFail ? 'var(--danger, #c45c5c)' : 'var(--green)',
          }"
        />
      </div>
      <div v-else-if="busyCount" class="sub-progress" aria-hidden="true"><i /></div>
      <div v-else class="progress">
        <i :style="{ width: donePct + '%', background: 'var(--green)' }" />
      </div>
    </div>

    <div
      v-show="!useCompact || expanded"
      class="uj-list"
      :class="{ 'uj-list--compact': useCompact }"
    >
      <div
        v-for="job in jobs"
        :key="job.id"
        class="upload-job uj-row"
        :class="[`is-${job.status || 'idle'}`]"
      >
        <div class="uj-row-main">
          <div class="uj-name" :title="job.name">{{ job.name }}</div>
          <div class="uj-meta">
            <slot name="meta" :job="job">{{ defaultMeta(job) }}</slot>
          </div>
          <slot name="progress" :job="job">
            <div class="progress uj-bar">
              <i
                :style="{
                  width: (Number(job.pct) || 0) + '%',
                  background: barColor(job),
                }"
              />
            </div>
          </slot>
          <div v-if="job.error" class="small warn uj-err">{{ job.error }}</div>
        </div>
        <div class="uj-actions">
          <slot name="actions" :job="job" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { uploadJobBarColor } from '../utils/uploadJobUi'

const props = defineProps({
  jobs: { type: Array, default: () => [] },
  hint: { type: String, default: '' },
  title: { type: String, default: '上传任务' },
  /** 条数 ≥ 此值：总览 + 默认可收起明细 */
  compactAt: { type: Number, default: 3 },
  /** 整批总数（完成条收起后分母仍不变）；0=跟面板现有条数 */
  batchTotal: { type: Number, default: 0 },
  /** 整批已成功 / 已失败（相对 batchTotal） */
  batchDone: { type: Number, default: 0 },
  batchFail: { type: Number, default: 0 },
  /** 无 meta 插槽时：`(job) => string` */
  metaFn: { type: Function, default: null },
})

const expanded = ref(false)

watch(
  () => props.jobs.length,
  (n, prev) => {
    // 新涌入一批时先收起明细，避免墙
    if (n >= props.compactAt && n > (prev || 0)) expanded.value = false
  },
)

const useCompact = computed(() => (props.jobs || []).length >= Number(props.compactAt || 3))

const busyCount = computed(
  () =>
    (props.jobs || []).filter((j) =>
      ['uploading', 'extracting', 'parsing', 'queued'].includes(j?.status),
    ).length,
)
const doneCount = computed(
  () => (props.jobs || []).filter((j) => j?.status === 'done').length,
)
const errorCount = computed(
  () => (props.jobs || []).filter((j) => j?.status === 'error').length,
)
/** 整批分母：优先外部 batchTotal，避免完成条收起后分母缩水 */
const totalCount = computed(() => {
  const hinted = Number(props.batchTotal) || 0
  if (hinted > 0) return hinted
  return (props.jobs || []).length || 0
})
const settledDone = computed(() => {
  const hinted = Number(props.batchTotal) || 0
  if (hinted > 0) return Math.max(0, Number(props.batchDone) || 0)
  return doneCount.value
})
const settledFail = computed(() => {
  const hinted = Number(props.batchTotal) || 0
  if (hinted > 0) return Math.max(0, Number(props.batchFail) || 0)
  return errorCount.value
})
const settledCount = computed(() => settledDone.value + settledFail.value)
const donePct = computed(() => {
  const n = totalCount.value || 1
  return Math.min(100, Math.round((settledCount.value / n) * 100))
})

/** 头 pill 只表态，数量只在 overviewTitle 出现一次 */
const statusPill = computed(() => {
  const total = totalCount.value
  if (settledFail.value && settledCount.value >= total && total) return '有失败'
  if (total && settledDone.value >= total && !settledFail.value) return '已完成'
  if (busyCount.value || settledCount.value < total) return '进行中'
  return ''
})
const statusPillClass = computed(() => {
  if (settledFail.value) return 'is-err'
  if (busyCount.value || settledCount.value < totalCount.value) return 'is-busy'
  return 'is-ok'
})

const overviewTitle = computed(() => {
  const total = totalCount.value || (props.jobs || []).length
  // 唯一数量：已落定 / 整批总数
  return `${settledCount.value}/${total}`
})
const overviewSub = computed(() => {
  if (settledFail.value) return `失败 ${settledFail.value}`
  return ''
})

function defaultMeta(job) {
  return typeof props.metaFn === 'function' ? props.metaFn(job) : ''
}

function barColor(job) {
  return uploadJobBarColor(job)
}
</script>

<style scoped>
.uj-panel {
  border: 1px solid var(--line-soft);
  border-radius: 12px;
  background: color-mix(in srgb, var(--panel, #1b1f27) 92%, transparent);
  overflow: hidden;
}
.uj-hd {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--line-soft);
}
.uj-hd-main {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.uj-hd h3 {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  color: var(--ink);
  letter-spacing: -0.01em;
}
.uj-hint {
  flex-shrink: 0;
}
.uj-pill {
  font-size: 11px;
  line-height: 1;
  padding: 4px 8px;
  border-radius: 999px;
  border: 1px solid var(--line-soft);
  color: var(--muted);
  white-space: nowrap;
}
.uj-pill.is-busy {
  color: var(--teal, #2a9d8f);
  border-color: color-mix(in srgb, var(--teal, #2a9d8f) 35%, var(--line-soft));
  background: color-mix(in srgb, var(--teal, #2a9d8f) 12%, transparent);
}
.uj-pill.is-ok {
  color: var(--green, #3d9a6a);
  border-color: color-mix(in srgb, var(--green, #3d9a6a) 35%, var(--line-soft));
  background: color-mix(in srgb, var(--green, #3d9a6a) 12%, transparent);
}
.uj-pill.is-err {
  color: var(--danger, #c45c5c);
  border-color: color-mix(in srgb, var(--danger, #c45c5c) 35%, var(--line-soft));
  background: color-mix(in srgb, var(--danger, #c45c5c) 12%, transparent);
}

.uj-overview {
  padding: 12px 14px 10px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.uj-overview-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.uj-overview-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--ink);
  line-height: 1.3;
}
.uj-toggle {
  flex-shrink: 0;
  border: none;
  background: transparent;
  color: var(--muted);
  font: inherit;
  font-size: 12px;
  cursor: pointer;
  padding: 2px 0;
}
.uj-toggle:hover {
  color: var(--ink);
}

.uj-list {
  padding: 8px 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.uj-list--compact {
  max-height: 280px;
  overflow: auto;
  padding-top: 0;
  border-top: 1px solid var(--line-soft);
}
.uj-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 10px 8px;
  border-radius: 10px;
  background: color-mix(in srgb, var(--bg, #12151b) 55%, transparent);
  border: 1px solid transparent;
}
.uj-row.is-extracting,
.uj-row.is-uploading,
.uj-row.is-parsing,
.uj-row.is-queued {
  border-color: color-mix(in srgb, var(--teal, #2a9d8f) 22%, transparent);
}
.uj-row.is-done {
  opacity: 0.88;
}
.uj-row.is-error {
  border-color: color-mix(in srgb, var(--danger, #c45c5c) 35%, transparent);
}
.uj-row-main {
  min-width: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.uj-name {
  font-weight: 600;
  font-size: 13px;
  line-height: 1.35;
  color: var(--ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.uj-meta {
  font-size: 12px;
  color: var(--muted);
  line-height: 1.35;
}
.uj-bar {
  margin-top: 4px;
}
.uj-err {
  margin-top: 2px;
}
.uj-actions {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
  padding-top: 2px;
}
</style>
