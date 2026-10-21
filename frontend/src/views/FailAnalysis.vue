<template>
  <div class="page-fill">
    <h1 class="page-title">失败分析</h1>
    <p class="page-desc">
      按失败类型汇总并排列处理优先级；处理建议仅供参考。单条任务重试请使用「任务队列」，当日待办请见「开工台」。
    </p>
    <PageSkeleton v-if="!booted" variant="dashboard" :rows="4" />
    <template v-else>
      <div class="panel mb-16">
        <div class="panel-hd">
          <h3>筛选</h3>
          <div class="row" style="gap:8px;flex-wrap:wrap">
            <n-select
              v-model:value="rangeKey"
              size="small"
              style="width:140px"
              :options="rangeOptions"
              @update:value="load"
            />
            <n-select
              v-model:value="filterCode"
              size="small"
              clearable
              filterable
              placeholder="失败类型"
              class="fa-code-select"
              style="width:220px"
              :options="codeOptions"
              :consistent-menu-width="false"
              :filter="filterCodeOption"
              :render-label="renderCodeLabel"
              :menu-props="{ class: 'fa-code-menu', style: { minWidth: '300px' } }"
              @update:value="load"
            />
            <n-select
              v-model:value="filterStep"
              size="small"
              clearable
              placeholder="步骤"
              style="width:160px"
              :options="stepOptions"
              @update:value="load"
            />
            <n-select
              v-model:value="filterDomain"
              size="small"
              clearable
              placeholder="领域"
              style="width:160px"
              :options="domainOptions"
              @update:value="load"
            />
            <n-button size="small" :loading="loading" @click="load">刷新</n-button>
          </div>
        </div>
        <div class="panel-bd">
          <div class="stats fa-stats" style="margin-bottom:0">
            <div class="stat">
              <div class="label">失败次数</div>
              <div class="value">{{ data?.totals?.failed ?? 0 }}</div>
            </div>
            <div class="stat">
              <div class="label">失败类型</div>
              <div class="value">{{ data?.totals?.codes ?? 0 }}</div>
            </div>
            <div class="stat">
              <div class="label">时间范围</div>
              <div class="value" style="font-size:14px">{{ rangeLabel }}</div>
            </div>
          </div>
        </div>
      </div>

      <div class="panel mb-16" v-if="priorities.length">
        <div class="panel-hd"><h3>建议优先处理</h3></div>
        <div class="panel-bd">
          <div v-for="p in priorities" :key="p.code" class="fa-priority">
            <div class="fa-priority-main">
              <strong>{{ p.count }}</strong>
              <span>{{ p.label }}</span>
              <span class="mono muted">{{ p.code }}</span>
            </div>
            <div class="fa-locus">{{ p.fix_locus }}</div>
          </div>
        </div>
      </div>

      <div class="grid-2 mb-16">
        <div class="panel">
          <div class="panel-hd"><h3>按类型</h3></div>
          <div class="panel-bd">
            <div v-if="!byCode.length" class="empty-hint">
              <div class="empty-title">暂无失败记录</div>
              <div class="empty-desc">当前时间范围内没有出包失败</div>
            </div>
            <div v-for="row in byCode" :key="row.code" class="fa-bar-row" @click="filterCode = row.code; load()">
              <span class="fa-code-cell">
                <span class="fa-code-name">{{ row.label || row.code }}</span>
                <span class="mono muted fa-code-id">{{ row.code }}</span>
              </span>
              <span class="fa-bar"><i :style="{ width: barPct(row.count, maxCode) }" /></span>
              <span>{{ row.count }}</span>
            </div>
          </div>
        </div>
        <div class="panel">
          <div class="panel-hd"><h3>按领域 / 步骤</h3></div>
          <div class="panel-bd">
            <div class="small muted mb-8">领域</div>
            <div v-for="row in byDomain.slice(0, 8)" :key="'d'+row.domain" class="fa-bar-row" @click="filterDomain = row.domain; load()">
              <span class="fa-code">{{ row.domain }}</span>
              <span class="fa-bar"><i :style="{ width: barPct(row.count, maxDomain) }" /></span>
              <span>{{ row.count }}</span>
            </div>
            <div class="small muted mb-8 mt-12">步骤</div>
            <div v-for="row in byStep.slice(0, 8)" :key="'s'+row.step" class="fa-bar-row" @click="filterStep = row.step; load()">
              <span class="fa-code">{{ row.step }}</span>
              <span class="fa-bar"><i :style="{ width: barPct(row.count, maxStep) }" /></span>
              <span>{{ row.count }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="panel panel-fill">
        <div class="panel-hd"><h3>样本</h3></div>
        <div class="panel-bd panel-bd-fill">
          <n-data-table
            :columns="columns"
            :data="samples"
            :bordered="false"
            size="small"
            :scroll-x="1200"
            remote
            :pagination="samplePagination"
          >
            <template #empty>
              <div class="empty-hint">
                <div class="empty-title">暂无记录</div>
                <div class="empty-desc">可放宽筛选条件，或扩大时间范围后重试</div>
              </div>
            </template>
          </n-data-table>
        </div>
      </div>

      <div v-if="draftCard" class="fa-draft-card">
        <div class="fa-draft-hd">
          <strong>
            处理建议
            <span v-if="draftJobId != null" class="fa-draft-job">· 任务 #{{ draftJobId }}</span>
          </strong>
          <div class="row" style="gap:8px">
            <n-button size="tiny" :disabled="!!draftCard.pending" @click="copyDraft">复制</n-button>
            <n-button
              size="tiny"
              secondary
              :disabled="!!draftCard.pending"
              :loading="draftJobId != null && !!draftBusy[draftJobId]"
              @click="regenDraft"
            >重新生成</n-button>
            <n-button size="tiny" quaternary @click="closeDraft">关闭</n-button>
            <n-button size="tiny" quaternary type="warning" @click="purgeDraft">清除缓存</n-button>
          </div>
        </div>
        <div
          v-if="draftCard.resolve_note"
          class="fa-resolve-note"
          :class="draftCard.maybe_resolved ? 'is-ok' : 'is-stale'"
        >
          {{ draftCard.resolve_note }}
        </div>
        <div class="small muted mb-8">
          类型 {{ draftCard.code }} · 相关位置：{{ draftCard.fix_locus || '—' }}
          <span v-if="draftCard.pending" class="fa-cached"> · 生成中</span>
          <span v-else-if="draftCard.cached" class="fa-cached"> · 已保存的建议</span>
          <span v-if="draftCard.draft_suspect" class="fa-suspect"> · 建议位置可能不准确</span>
        </div>
        <pre
          class="fa-draft-body"
          :class="{
            'is-muted': draftCard.maybe_resolved || draftCard.resolve_stale,
            'is-pending': !!draftCard.pending,
          }"
        >{{ draftCard.draft }}</pre>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, h, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton } from 'naive-ui'
import { api, message } from '../api'
import PageSkeleton from '../components/PageSkeleton.vue'

const route = useRoute()
const router = useRouter()
const booted = ref(false)
const loading = ref(false)
const data = ref(null)
const rangeKey = ref('7d')
const filterCode = ref(null)
const filterStep = ref(null)
const filterDomain = ref(null)
const draftCard = ref(null)
const draftJobId = ref(null)
const draftRow = ref(null)
/** job_id -> 已返回的建议；关闭浮层不丢，可多条并跑 */
const draftByJob = ref({})
const draftRowByJob = ref({})
/** 当前浮层对准的任务；null = 已关闭（后台仍可跑完进缓存） */
const draftFocusJobId = ref(null)
const assistBusy = ref({})
const draftBusy = ref({})
const samplePage = ref(1)
const samplePageSize = ref(10)
const samplesTotal = ref(0)

function pendingDraft(row) {
  return {
    pending: true,
    job_id: row.job_id,
    code: row.code,
    label: row.label,
    fix_locus: row.fix_locus,
    draft: '正在生成处理建议…',
  }
}

function showDraftForJob(jobId, payload, row) {
  draftFocusJobId.value = jobId
  draftJobId.value = jobId
  draftCard.value = payload
  if (row) {
    draftRow.value = row
    draftRowByJob.value = { ...draftRowByJob.value, [jobId]: row }
  } else if (draftRowByJob.value[jobId]) {
    draftRow.value = draftRowByJob.value[jobId]
  }
}

const rangeOptions = [
  { label: '近 7 天', value: '7d' },
  { label: '近 30 天', value: '30d' },
  { label: '近 90 天', value: '90d' },
]

const rangeLabel = computed(() => {
  const r = data.value?.range
  if (!r?.from) return '—'
  return `${String(r.from).slice(0, 10)} 起`
})

const priorities = computed(() => data.value?.priorities || [])
const byCode = computed(() => data.value?.by_code || [])
const byDomain = computed(() => data.value?.by_domain || [])
const byStep = computed(() => data.value?.by_step || [])
const samples = computed(() => data.value?.samples || [])
const maxCode = computed(() => Math.max(1, ...byCode.value.map((x) => x.count)))
const maxDomain = computed(() => Math.max(1, ...byDomain.value.map((x) => x.count)))
const maxStep = computed(() => Math.max(1, ...byStep.value.map((x) => x.count)))

const samplePagination = computed(() => ({
  page: samplePage.value,
  pageSize: samplePageSize.value,
  itemCount: samplesTotal.value,
  showSizePicker: true,
  pageSizes: [10, 20, 40],
  prefix: ({ itemCount }) => `共 ${itemCount} 条`,
  onUpdatePage: (page) => {
    samplePage.value = page
    load({ resetPage: false })
  },
  onUpdatePageSize: (size) => {
    samplePageSize.value = size
    samplePage.value = 1
    load({ resetPage: false })
  },
}))

const codeOptions = computed(() =>
  (data.value?.catalog || []).map((c) => ({
    label: c.label,
    value: c.code,
  })),
)
const stepOptions = computed(() =>
  byStep.value.map((s) => ({ label: s.step, value: s.step })),
)
const domainOptions = computed(() =>
  byDomain.value.map((d) => ({ label: d.domain, value: d.domain })),
)

function filterCodeOption(pattern, option) {
  const p = String(pattern || '').trim().toLowerCase()
  if (!p) return true
  return (
    String(option.label || '').toLowerCase().includes(p) ||
    String(option.value || '').toLowerCase().includes(p)
  )
}

/** 只改文案，不动 option 节点（自定义 render-option 会丢掉点击） */
function renderCodeLabel(option) {
  if (!option) return null
  return h('div', { class: 'fa-code-opt' }, [
    h('span', { class: 'fa-code-opt-label' }, option.label || option.value),
    h('span', { class: 'fa-code-opt-code' }, option.value),
  ])
}

function barPct(n, max) {
  return `${Math.max(6, Math.round((n / max) * 100))}%`
}

function rangeParams() {
  const days = rangeKey.value === '30d' ? 30 : rangeKey.value === '90d' ? 90 : 7
  const from = new Date(Date.now() - days * 86400000)
  const pad = (x) => String(x).padStart(2, '0')
  const fmt = (d) =>
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  return {
    from: fmt(from),
    code: filterCode.value || undefined,
    step: filterStep.value || undefined,
    domain: filterDomain.value || undefined,
    sample_page: samplePage.value,
    sample_page_size: samplePageSize.value,
  }
}

function applyRouteQuery() {
  const c = route.query.code
  if (typeof c === 'string' && c.trim()) {
    filterCode.value = c.trim()
  }
}

function syncRouteQuery() {
  const next = {}
  if (filterCode.value) next.code = filterCode.value
  const cur = typeof route.query.code === 'string' ? route.query.code : undefined
  if ((next.code || undefined) === (cur || undefined)) return
  router.replace({ query: next })
}

async function load({ resetPage = true } = {}) {
  if (resetPage) samplePage.value = 1
  loading.value = true
  try {
    data.value = await api.failAnalysis(rangeParams())
    samplesTotal.value = data.value?.samples_total ?? (data.value?.samples || []).length
    syncRouteQuery()
  } catch (e) {
    message.error(e?.message || '加载失败')
  } finally {
    loading.value = false
    booted.value = true
  }
}

async function assist(row) {
  assistBusy.value = { ...assistBusy.value, [row.job_id]: true }
  try {
    const res = await api.failAnalysisClassifyAssist({
      error: row.error,
      step: row.step,
    })
    message.success(`可能属于：${res.code} · ${res.label || ''}（仅供参考，未写入）`)
  } catch (e) {
    message.error(e?.message || '暂时无法识别类型')
  } finally {
    assistBusy.value = { ...assistBusy.value, [row.job_id]: false }
  }
}

async function askDraft(row, { force = false } = {}) {
  const jid = row.job_id
  draftRowByJob.value = { ...draftRowByJob.value, [jid]: row }

  // 已在生成：只把浮层切到这条，不重复请求
  if (draftBusy.value[jid] && !force) {
    showDraftForJob(jid, draftByJob.value[jid] || pendingDraft(row), row)
    message.info(`任务 #${jid} 仍在生成中，已切换至该条`)
    return
  }

  // 有缓存且非强制：直接打开
  if (!force && draftByJob.value[jid]?.draft && !draftByJob.value[jid].pending) {
    showDraftForJob(jid, draftByJob.value[jid], row)
    message.info('已载入已保存的处理建议')
    return
  }

  showDraftForJob(jid, pendingDraft(row), row)
  draftBusy.value = { ...draftBusy.value, [jid]: true }
  try {
    const res = await api.failAnalysisFixDraft({
      error: row.error,
      code: row.code,
      job_id: jid,
      force,
    })
    draftByJob.value = { ...draftByJob.value, [jid]: { ...res, pending: false } }
    if (draftFocusJobId.value === jid) {
      showDraftForJob(jid, draftByJob.value[jid], row)
      if (res.cached) {
        message.info('已载入已保存的处理建议')
      } else {
        message.warning('处理建议已生成，请核对后再操作')
      }
    } else if (draftFocusJobId.value == null) {
      message.info(`任务 #${jid} 的处理建议已就绪，可再次打开「处理建议」查看`)
    }
    // 浮层正看着别的任务：只进缓存，不抢屏
  } catch (e) {
    if (draftFocusJobId.value === jid) {
      draftCard.value = null
      draftFocusJobId.value = null
      message.error(e?.message || '暂时无法生成建议')
    } else if (draftFocusJobId.value == null) {
      message.error(`任务 #${jid} 建议生成失败`)
    }
  } finally {
    draftBusy.value = { ...draftBusy.value, [jid]: false }
  }
}

function closeDraft() {
  // 只收起；进行中的请求继续，结果进缓存
  draftFocusJobId.value = null
  draftCard.value = null
}

async function purgeDraft() {
  const jid = draftJobId.value
  if (jid == null) {
    closeDraft()
    return
  }
  try {
    await api.failAnalysisDiscardDraft(jid)
  } catch {
    /* 本地仍清 */
  }
  const next = { ...draftByJob.value }
  delete next[jid]
  draftByJob.value = next
  const rows = { ...draftRowByJob.value }
  delete rows[jid]
  draftRowByJob.value = rows
  closeDraft()
  message.success(`已清除任务 #${jid} 的建议缓存`)
}

function clearLocalDraftCache() {
  draftByJob.value = {}
  draftRowByJob.value = {}
  draftBusy.value = {}
  draftFocusJobId.value = null
  draftCard.value = null
  draftJobId.value = null
  draftRow.value = null
}

async function regenDraft() {
  const row = draftRow.value || (draftJobId.value != null ? draftRowByJob.value[draftJobId.value] : null)
  if (!row) return
  await askDraft(row, { force: true })
}

async function copyDraft() {
  const t = draftCard.value?.draft || ''
  try {
    await navigator.clipboard.writeText(t)
    message.success('已复制到剪贴板')
  } catch {
    message.error('复制失败')
  }
}

const columns = [
  {
    title: '任务',
    key: 'job_id',
    width: 72,
    render: (r) => `#${r.job_id}`,
  },
  {
    title: '项目',
    key: 'project_title',
    width: 160,
    ellipsis: { tooltip: true },
    render: (r) =>
      h(
        'a',
        {
          href: `#`,
          class: 'link',
          onClick: (e) => {
            e.preventDefault()
            router.push(`/projects/${r.project_id}`)
          },
        },
        r.project_title || r.project_id,
      ),
  },
  {
    title: '类型',
    key: 'code',
    width: 168,
    render: (r) =>
      h('div', { class: 'fa-type-cell' }, [
        h('div', null, r.label || r.code),
        h('div', { class: 'mono muted fa-code-id' }, r.code),
      ]),
  },
  {
    title: '状态',
    key: 'resolve',
    width: 100,
    render: (r) => {
      if (r.maybe_resolved) {
        return h('span', { class: 'fa-badge fa-badge-ok' }, '可能已修复')
      }
      if (r.resolve_stale) {
        return h('span', { class: 'fa-badge fa-badge-stale' }, '建议过时')
      }
      return h('span', { class: 'muted small' }, '—')
    },
  },
  {
    title: '相关位置',
    key: 'fix_locus',
    ellipsis: { tooltip: true },
    render: (r) => h('span', { class: 'small' }, r.fix_locus || '待补充'),
  },
  {
    title: '步骤 / 域',
    key: 'step',
    width: 140,
    render: (r) => h('span', { class: 'small' }, `${r.step || '—'} · ${r.domain || '—'}`),
  },
  {
    title: '错误',
    key: 'error',
    ellipsis: { tooltip: true },
  },
  {
    title: '操作',
    key: 'actions',
    width: 96,
    render: (r) =>
      h('div', { class: 'fa-actions' }, [
        h(
          NButton,
          {
            size: 'tiny',
            quaternary: true,
            loading: !!assistBusy.value[r.job_id],
            onClick: () => assist(r),
          },
          { default: () => '识别类型' },
        ),
        h(
          NButton,
          {
            size: 'tiny',
            quaternary: true,
            type: 'primary',
            loading: !!draftBusy.value[r.job_id],
            onClick: () => askDraft(r),
          },
          { default: () => '处理建议' },
        ),
      ]),
  },
]

onMounted(() => {
  applyRouteQuery()
  load({ resetPage: true })
})

onUnmounted(clearLocalDraftCache)

watch(
  () => route.query.code,
  (code) => {
    const next = typeof code === 'string' && code.trim() ? code.trim() : null
    if ((filterCode.value || null) === next) return
    filterCode.value = next
    load({ resetPage: true })
  },
)
</script>

<style scoped>
/* 全局 .stats 默认 4 列；本页只有 3 个指标 */
.fa-stats {
  grid-template-columns: repeat(3, 1fr);
}
.fa-priority {
  padding: 8px 0;
  border-bottom: 1px solid var(--line);
}
.fa-priority:last-child { border-bottom: 0; }
.fa-priority-main {
  display: flex;
  gap: 10px;
  align-items: baseline;
  flex-wrap: wrap;
  color: var(--ink);
}
.fa-locus {
  margin-top: 4px;
  font-size: 12px;
  color: var(--muted);
  font-family: var(--mono);
}
.fa-bar-row {
  display: grid;
  grid-template-columns: minmax(120px, 1.4fr) 1fr 36px;
  gap: 8px;
  align-items: center;
  font-size: 12px;
  padding: 6px 0;
  cursor: pointer;
  color: var(--ink-2);
}
.fa-bar-row:hover { color: var(--teal); }
.fa-code {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.fa-code-cell {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}
.fa-code-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--ink);
}
.fa-code-id {
  font-size: 11px;
  line-height: 1.3;
}
.fa-type-cell {
  display: flex;
  flex-direction: column;
  gap: 1px;
  line-height: 1.35;
}
.fa-badge {
  display: inline-block;
  font-size: 11px;
  line-height: 1.3;
  padding: 2px 6px;
  border-radius: 4px;
  white-space: nowrap;
}
.fa-badge-ok {
  color: var(--green);
  background: var(--green-soft);
}
.fa-badge-stale {
  color: var(--amber);
  background: var(--amber-soft);
}
.fa-actions {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 2px;
  width: 100%;
}
.fa-actions :deep(.n-button) {
  justify-content: flex-start;
  --n-padding: 0 2px;
  --n-height: 22px;
  --n-font-size: 12px;
}
.fa-bar {
  height: 6px;
  background: var(--line);
  border-radius: 3px;
  overflow: hidden;
}
.fa-bar i {
  display: block;
  height: 100%;
  background: var(--teal);
}
.fa-draft-card {
  position: fixed;
  right: 24px;
  bottom: 24px;
  width: min(420px, calc(100vw - 48px));
  max-height: 50vh;
  overflow: auto;
  background: var(--surface);
  color: var(--ink);
  border: 1px solid var(--amber);
  border-radius: 8px;
  padding: 12px 14px;
  box-shadow: 0 8px 28px color-mix(in srgb, var(--ink) 28%, transparent);
  z-index: 40;
}
.fa-draft-hd {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  color: var(--ink);
}
.fa-draft-job {
  font-weight: 500;
  color: var(--muted);
}
.fa-draft-body {
  white-space: pre-wrap;
  font-size: 12px;
  margin: 0;
  line-height: 1.5;
  color: var(--ink);
  background: var(--surface-2);
  border: 1px solid var(--line-soft);
  border-radius: 6px;
  padding: 10px 12px;
  font-family: var(--mono);
}
.fa-suspect { color: var(--amber); font-weight: 600; }
.fa-cached { color: var(--muted); }
.fa-resolve-note {
  margin: 0 0 10px;
  padding: 8px 10px;
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.45;
  border: 1px solid var(--line);
}
.fa-resolve-note.is-ok {
  color: var(--green);
  background: var(--green-soft);
  border-color: color-mix(in srgb, var(--green) 35%, var(--line));
}
.fa-resolve-note.is-stale {
  color: var(--amber);
  background: var(--amber-soft);
  border-color: color-mix(in srgb, var(--amber) 35%, var(--line));
}
.fa-draft-body.is-muted {
  opacity: 0.55;
}
.fa-draft-body.is-pending {
  color: var(--muted);
  font-style: italic;
}
.mb-16 { margin-bottom: 16px; }
.mt-12 { margin-top: 12px; }
.mb-8 { margin-bottom: 8px; }
</style>

<style>
/* 下拉挂 body：保留 Naive 选项壳，只排两行文案 */
.fa-code-menu.n-base-select-menu {
  min-width: 300px;
}
.fa-code-menu .n-base-select-option {
  height: auto !important;
  padding-top: 8px;
  padding-bottom: 8px;
}
.fa-code-menu .fa-code-opt {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  line-height: 1.35;
  white-space: normal;
}
.fa-code-menu .fa-code-opt-label {
  color: var(--ink);
  font-size: 13px;
}
.fa-code-menu .fa-code-opt-code {
  color: var(--muted);
  font-size: 11px;
  font-family: var(--mono);
}
/* 收起态：只显示中文，避免撑高筛选条 */
.fa-code-select .n-base-selection-label .fa-code-opt {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}
.fa-code-select .n-base-selection-label .fa-code-opt-code {
  display: none;
}
.fa-code-select .n-base-selection-label .fa-code-opt-label {
  color: inherit;
  font-size: inherit;
}
</style>
