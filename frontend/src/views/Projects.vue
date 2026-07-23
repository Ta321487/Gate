<template>
  <div>
    <h1 class="page-title">项目</h1>
    <p class="page-desc">
      上传开题等材料，确认分堆后创建项目。细则见「帮助 → 上传与分堆」。
    </p>

    <div class="row mb-12" style="justify-content:flex-end;gap:8px">
      <n-button size="small" @click="openSampleProposal">生成测试开题</n-button>
    </div>

    <div
      class="dropzone"
      :class="{ dragover }"
      @dragover.prevent="dragover = true"
      @dragleave="dragover = false"
      @drop.prevent="onDrop"
    >
      <input type="file" multiple accept=".pdf,.doc,.docx,.txt,.zip" @change="onFile" />
      <div class="dropzone-icon">↑</div>
      <div class="dropzone-title">拖入材料，或点击选择</div>
      <div class="dropzone-hint">
        文件 / 文件夹 / zip · 展开后最多 {{ MAX_UPLOAD_MATERIALS }} 份 · PDF / Word / TXT
      </div>
    </div>

    <n-modal
      v-model:show="planOpen"
      preset="card"
      title="确认分堆"
      style="width:min(720px,94vw)"
      :mask-closable="false"
      @after-leave="onPlanLeave"
    >
      <div v-if="planLoading" class="muted">正在解析并分堆…</div>
      <template v-else-if="planData">
        <p class="small muted" style="margin:0 0 12px">
          {{ planData.notes || '请核对下方分堆后确认创建。' }}
          <span v-if="planData.llm_ok"> · LLM 结构分堆</span>
          <span v-else> · 规则分堆</span>
          · 来源 {{ planData.source }}
          <span v-if="otherPendingPlans > 0"> · 另有 {{ otherPendingPlans }} 份待确认</span>
        </p>
        <div class="stack" style="gap:10px;max-height:55vh;overflow:auto">
          <div
            v-for="cl in planData.clusters"
            :key="cl.id"
            class="plan-cluster"
          >
            <div class="row" style="justify-content:space-between;gap:8px;align-items:flex-start">
              <div style="min-width:0;flex:1">
                <div class="row" style="gap:8px;align-items:baseline;flex-wrap:wrap">
                  <span class="plan-cluster-idx">项目 {{ cl.id }}</span>
                  <span class="plan-cluster-title" :title="cl.label">{{ shortLabel(cl.label) }}</span>
                </div>
                <div
                  v-if="clusterReasonVisible(cl)"
                  class="small muted"
                  style="margin-top:4px"
                >{{ cl.reason }}</div>
              </div>
              <span class="small muted" style="flex-shrink:0">{{ cl.files?.length || 0 }} 份</span>
            </div>
            <div class="plan-cluster-files">
              <span
                v-for="f in cl.files"
                :key="f.index"
                class="plan-file-chip"
              >
                {{ f.name }}
                <span class="muted">{{ roleLabel(f.role) }}</span>
              </span>
            </div>
          </div>
          <div v-if="planData.discard?.length" class="small warn">
            <div style="font-weight:600;margin-bottom:4px">将剔除（不参与匹配）</div>
            <div class="plan-cluster-files">
              <span
                v-for="d in planData.discard"
                :key="d.index"
                class="plan-file-chip plan-file-chip--discard"
                :title="d.reason"
              >
                {{ d.name }}
              </span>
            </div>
          </div>
          <div v-if="!planData.clusters?.length" class="warn small">
            没有可创建的项目（材料可能均被剔除或信号过弱）。
          </div>
        </div>
        <div class="row" style="justify-content:space-between;margin-top:16px;gap:8px;flex-wrap:wrap">
          <div class="row" style="gap:8px">
            <n-button size="small" quaternary :disabled="planConfirming" @click="planSplitAll">
              全部拆开
            </n-button>
            <n-button size="small" quaternary :disabled="planConfirming" @click="planMergeAll">
              合并为一个
            </n-button>
          </div>
          <div class="row" style="gap:8px">
            <n-button :disabled="planConfirming" @click="planOpen = false">取消</n-button>
            <n-button
              v-if="!planData.clusters?.length"
              type="primary"
              :loading="planConfirming"
              @click="dismissEmptyPlan"
            >
              确认跳过
            </n-button>
            <n-button
              v-else
              type="primary"
              :loading="planConfirming"
              @click="confirmPlan"
            >
              确认创建 {{ planData.clusters.length }} 个项目
            </n-button>
          </div>
        </div>
      </template>
    </n-modal>

    <n-modal
      v-model:show="sampleOpen"
      preset="card"
      title="生成测试开题"
      style="width:min(720px,94vw)"
      :mask-closable="!sampleLoading"
    >
      <p class="small muted" style="margin:0 0 12px">
        随机覆盖常见毕设方向，可选 DeepSeek / Gemini 润色（与「大模型」页启用链一致）。下载 txt 后拖到上方上传即可。
      </p>
      <div class="stack" style="gap:10px">
        <div class="row" style="gap:8px;flex-wrap:wrap">
          <n-select
            v-model:value="sampleDomain"
            clearable
            placeholder="领域（空=随机）"
            :options="sampleDomainOptions"
            style="min-width:220px;flex:1"
            :disabled="sampleLoading"
          />
          <label class="row small" style="gap:8px;align-items:center">
            <n-switch v-model:value="sampleUseLlm" :disabled="sampleLoading" />
            LLM 润色（DeepSeek / Gemini）
          </label>
        </div>
        <div v-if="sampleResult" class="panel" style="margin:0">
          <div class="panel-bd stack" style="gap:8px;padding:12px">
            <div class="small">
              <strong>{{ sampleResult.title }}</strong>
              <span class="muted"> · {{ sampleResult.anchor_domain }} · {{ sampleResult.pack_id }}</span>
              <span v-if="sampleResult.used_llm" class="pill pill-teal" style="margin-left:6px">已润色</span>
              <span v-else class="pill pill-neutral" style="margin-left:6px">模板</span>
            </div>
            <pre class="sample-proposal-pre">{{ sampleResult.text }}</pre>
          </div>
        </div>
      </div>
      <template #footer>
        <div class="row" style="justify-content:flex-end;gap:8px">
          <n-button :disabled="sampleLoading" @click="sampleOpen = false">关闭</n-button>
          <n-button :loading="sampleLoading" @click="generateSample">{{ sampleResult ? '再抽一份' : '生成' }}</n-button>
          <n-button type="primary" :disabled="!sampleResult || sampleLoading" @click="downloadSample">下载 txt</n-button>
        </div>
      </template>
    </n-modal>

    <div v-if="uploadJobs.length" class="panel mb-16">
      <div class="panel-hd">
        <h3>上传任务</h3>
        <span class="small muted">{{ uploadQueueHint }}</span>
      </div>
      <div class="panel-bd stack" style="gap:14px">
        <div v-for="job in uploadJobs" :key="job.id" class="upload-job">
          <div class="row" style="justify-content:space-between;margin-bottom:6px;gap:8px">
            <div style="min-width:0">
              <div style="font-weight:600;line-height:1.35">{{ job.name }}</div>
              <div class="small muted">{{ job.fileCount }} 份材料 · {{ jobPhaseLabel(job) }}</div>
            </div>
            <div class="row" style="gap:6px;flex-shrink:0">
              <n-button
                v-if="job.status === 'planned' && job.plan"
                size="tiny"
                @click="reopenPlan(job)"
              >查看分堆</n-button>
              <n-button
                v-if="job.status === 'done' && job.projectId"
                size="tiny"
                @click="router.push(`/projects/${job.projectId}`)"
              >查看</n-button>
              <n-button
                v-if="job.status === 'done' || job.status === 'error' || job.status === 'planned'"
                text
                size="tiny"
                @click="dismissJob(job.id)"
              >移除</n-button>
            </div>
          </div>
          <div class="progress"><i :style="{ width: job.pct + '%', background: jobBarColor(job) }" /></div>
          <div v-if="job.error" class="small warn" style="margin-top:6px">{{ job.error }}</div>
        </div>
      </div>
    </div>

    <PageSkeleton v-if="!booted" variant="dashboard" />
    <template v-else>
      <div class="stats">
        <div class="stat"><div class="label">全部项目</div><div class="value">{{ stats.total }}</div><div class="hint">本机工作区</div></div>
        <div class="stat"><div class="label">生成中</div><div class="value">{{ stats.generating }}</div><div class="hint">正在跑流水线</div></div>
        <div class="stat"><div class="label">可预览</div><div class="value">{{ stats.previewable }}</div><div class="hint">已生成 · 可启预览</div></div>
        <div class="stat"><div class="label">本月 Token</div><div class="value">{{ formatK(stats.monthly_tokens) }}</div><div class="hint">流水线 {{ formatK(stats.monthly_tokens_pipeline) }} · 系统支持 {{ formatK(stats.monthly_tokens_support) }} · 预算 {{ formatK(stats.monthly_budget) }}</div></div>
      </div>

      <div class="panel">
        <div class="panel-hd">
          <h3>项目列表</h3>
          <n-button size="small" :loading="loading" @click="refresh">刷新</n-button>
        </div>
        <div class="panel-bd" style="padding-top:12px">
          <div class="row mb-12" style="justify-content:space-between">
            <div class="filter-pills" role="group" aria-label="项目筛选">
              <button
                v-for="f in filters"
                :key="f.id"
                type="button"
                class="pill filter-pill"
                :class="[f.pill, { on: filter === f.id }]"
                @click="setFilter(f.id)"
              >{{ f.label }}</button>
            </div>
            <n-input v-model:value="q" clearable placeholder="搜索题目 / ID…" style="width:220px" @update:value="onSearch" />
          </div>
          <n-data-table :columns="columns" :data="list" :row-key="r => r.id" :bordered="false" size="small">
            <template #empty>
              <div class="empty-hint">
                <div class="empty-title">暂无项目</div>
                <div class="empty-desc">上传材料后确认分堆即可创建；同课题会合并，不同课题会拆开</div>
              </div>
            </template>
          </n-data-table>
          <div class="small muted mt-12">共 {{ list.length }} 条 · 点击行进入详情</div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, h, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NButton } from 'naive-ui'
import { api, message } from '../api'
import { collectUploadMaterials, MAX_UPLOAD_MATERIALS } from '../uploadMaterials'
import PageSkeleton from '../components/PageSkeleton.vue'
import CopyIconButton from '../components/CopyIconButton.vue'
import {
  debounce,
  formatArchDom,
  getCatalog,
  projectStatusLabel,
  projectStatusPill,
  statusPillNode,
} from '../opsShared'

const router = useRouter()
const list = ref([])
const catalog = ref({ archetypes: [], domains: [] })
const filter = ref('all')
/** 与状态/运行列语义对齐：运行中 · 生成中 · 可交付 · 质检未过 */
const filters = [
  { id: 'all', label: '全部', pill: 'pill-neutral' },
  { id: 'active', label: '运行中', pill: 'pill-green' },
  { id: 'generating', label: '生成中', pill: 'pill-teal' },
  { id: 'done', label: '可交付', pill: 'pill-teal' },
  { id: 'fail', label: '质检未过', pill: 'pill-red' },
]
const q = ref('')
const dragover = ref(false)
/** @type {import('vue').Ref<Array<{
 *  id: number
 *  name: string
 *  fileCount: number
 *  files: File[]
 *  status: 'queued'|'uploading'|'parsing'|'planned'|'done'|'error'
 *  pct: number
 *  error: string
 *  projectId: string
 *  plan?: object|null
 *  tick: any
 * }>>} */
const uploadJobs = ref([])
let uploadSeq = 1
/** 同时跑几路上传（Match Agent 较重，默认 2） */
const UPLOAD_CONCURRENCY = 2
let activeUploads = 0
/** 当前确认弹窗对应的 uploadJobs.id */
const planJobId = ref(null)

const planOpen = ref(false)
const planLoading = ref(false)
const planConfirming = ref(false)
const planData = ref(null)
/** 确认时覆盖分堆：number[][] | null */
const planClustersOverride = ref(null)
const planDiscardOverride = ref(null)
/** 确认成功关闭弹窗时跳过 after-leave 自动翻页（由 confirmPlan 自行决定） */
let planCloseFromConfirm = false

const otherPendingPlans = computed(() =>
  uploadJobs.value.filter(
    (j) => j.status === 'planned' && j.plan && !j.deferred && j.id !== planJobId.value,
  ).length,
)

const uploadQueueHint = computed(() => {
  const jobs = uploadJobs.value
  const running = jobs.filter((j) =>
    j.status === 'uploading' || j.status === 'parsing' || j.status === 'planned',
  ).length
  const queued = jobs.filter((j) => j.status === 'queued').length
  const done = jobs.filter((j) => j.status === 'done').length
  const err = jobs.filter((j) => j.status === 'error').length
  const parts = []
  if (running) parts.push(`处理中 ${running}`)
  if (queued) parts.push(`待处理 ${queued}`)
  if (done) parts.push(`已完成 ${done}`)
  if (err) parts.push(`失败 ${err}`)
  return parts.join(' · ') || '—'
})

function roleLabel(role) {
  return ({ proposal: '开题', taskbook: '任务书', checklist: '功能清单', unknown: '材料' })[role] || role || '材料'
}

/** 长题名缩短展示，悬停仍见全称（用 title 属性） */
function shortLabel(label) {
  const s = (label || '').trim()
  if (!s) return '未命名课题'
  const m = s.match(/的(.{4,28}?)(?:的设计与实现|的设计与开发)?$/)
  if (m && m[1] && m[1].length >= 4 && m[1].length < s.length - 8) return m[1]
  if (s.length > 36) return `${s.slice(0, 34)}…`
  return s
}

function clusterReasonVisible(cl) {
  const reason = (cl?.reason || '').trim()
  if (!reason) return false
  const label = (cl?.label || '').trim()
  if (!label) return true
  // 理由只是复述题名时不展示，避免「标题 + 几乎同样的灰色一行」
  if (reason === label) return false
  if (label.includes(reason) || reason.includes(label)) return false
  const core = shortLabel(label)
  if (core && (reason.includes(core) || core.includes(reason))) return false
  if (reason.startsWith('同题「') && reason.includes(core)) return false
  return true
}

function onPlanLeave() {
  if (planConfirming.value) return
  const closedId = planJobId.value
  syncOverridesToJob()
  // 取消/关窗：标记 deferred，避免多份 planned 时 A↔B 反复弹（干扰项 0 项目只能取消时必现）
  if (!planCloseFromConfirm && closedId != null) {
    const job = uploadJobs.value.find((j) => j.id === closedId)
    if (job && job.status === 'planned') job.deferred = true
  }
  planJobId.value = null
  planClustersOverride.value = null
  planDiscardOverride.value = null
  planData.value = null
  if (planCloseFromConfirm) {
    planCloseFromConfirm = false
    return
  }
  // 取消关闭：只翻尚未 deferred 的下一份
  queueMicrotask(() => openNextPendingPlan(closedId))
}

function syncOverridesToJob() {
  const job = uploadJobs.value.find((j) => j.id === planJobId.value)
  if (!job) return
  job.clustersOverride = planClustersOverride.value
  job.discardOverride = planDiscardOverride.value
  if (planData.value) job.plan = planData.value
}

function loadOverridesFromJob(job) {
  planClustersOverride.value = job.clustersOverride || null
  planDiscardOverride.value = job.discardOverride || null
}

/** @param {{ force?: boolean }} [opts] force=用户点「查看分堆」显式切换 */
function showPlanForJob(job, opts = {}) {
  if (!job?.plan) return false
  if (planConfirming.value) {
    message.warning('正在创建项目，请稍候再切换分堆')
    return false
  }
  // 弹窗已开且不是当前任务：后到的分堆只挂队列，不顶掉正在确认的内容
  if (planOpen.value && planJobId.value != null && planJobId.value !== job.id && !opts.force) {
    return false
  }
  if (planOpen.value && planJobId.value != null && planJobId.value !== job.id && opts.force) {
    syncOverridesToJob()
  }
  planJobId.value = job.id
  loadOverridesFromJob(job)
  planData.value = job.plan
  planLoading.value = false
  planOpen.value = true
  return true
}

function openNextPendingPlan(exceptId = null) {
  if (planOpen.value || planConfirming.value) return
  const next = uploadJobs.value.find(
    (j) => j.status === 'planned' && j.plan && !j.deferred && j.id !== exceptId,
  )
  if (next) showPlanForJob(next)
}

function reopenPlan(job) {
  if (job) job.deferred = false
  if (!showPlanForJob(job, { force: true })) return
}

function pendingPlanCount() {
  return uploadJobs.value.filter((j) => j.status === 'planned' && j.plan && !j.deferred).length
}

/** 全剔除 / 0 项目：确认跳过，结束任务，避免只能取消却仍占 planned 队列 */
async function dismissEmptyPlan() {
  if (planData.value?.clusters?.length) return
  const job = uploadJobs.value.find((j) => j.id === planJobId.value)
  const planId = planData.value?.plan_id || job?.plan?.plan_id
  if (job) {
    job.status = 'done'
    job.pct = 100
    job.plan = null
    job.deferred = false
    job.name = '已跳过 · 无项目可创建'
    const n = (planData.value?.discard || []).length
    message.info(n ? `已跳过，剔除 ${n} 份无关材料` : '已跳过（无项目可创建）')
  }
  await discardPlanOnServer(planId)
  planCloseFromConfirm = true
  planOpen.value = false
  planData.value = null
  planJobId.value = null
  planClustersOverride.value = null
  planDiscardOverride.value = null
  queueMicrotask(() => openNextPendingPlan())
}

function planSplitAll() {
  if (!planData.value?.files?.length) return
  const disc = new Set((planData.value.discard || []).map((d) => d.index))
  const allFiles = planData.value.files
  planDiscardOverride.value = [...disc]
  planClustersOverride.value = allFiles
    .filter((f) => !disc.has(f.index))
    .map((f) => [f.index])
  const next = {
    ...planData.value,
    source: 'override',
    notes: '已改为：每份材料单独成项目（确认后生效）',
    clusters: planClustersOverride.value.map((idxs, i) => {
      const f = allFiles.find((x) => x.index === idxs[0])
      return {
        id: i + 1,
        label: f?.title || f?.name || `项目 ${i + 1}`,
        reason: '人工：全部拆开',
        files: f ? [f] : [],
      }
    }),
  }
  planData.value = next
  const job = uploadJobs.value.find((j) => j.id === planJobId.value)
  if (job) job.plan = next
}

function planMergeAll() {
  if (!planData.value?.files?.length) return
  const disc = new Set((planData.value.discard || []).map((d) => d.index))
  const keep = planData.value.files.filter((f) => !disc.has(f.index))
  if (!keep.length) return
  planDiscardOverride.value = [...disc]
  planClustersOverride.value = [keep.map((f) => f.index)]
  const next = {
    ...planData.value,
    source: 'override',
    notes: '已改为：合并为单个项目（确认后生效）',
    clusters: [
      {
        id: 1,
        label: keep.find((f) => f.role === 'proposal')?.title || keep[0].title || keep[0].name,
        reason: '人工：合并为一个',
        files: keep,
      },
    ],
  }
  planData.value = next
  const job = uploadJobs.value.find((j) => j.id === planJobId.value)
  if (job) job.plan = next
}

async function confirmPlan() {
  if (!planData.value?.plan_id || !planData.value.clusters?.length) return
  planConfirming.value = true
  const planId = planData.value.plan_id
  const sourceJob = uploadJobs.value.find((j) => j.id === planJobId.value)
  const job = sourceJob || {
    id: uploadSeq++,
    name: `确认创建 ${planData.value.clusters.length} 个项目`,
    fileCount: planData.value.files?.length || 0,
    files: [],
    status: 'parsing',
    pct: 40,
    error: '',
    projectId: '',
    plan: planData.value,
    tick: null,
  }
  if (!sourceJob) {
    uploadJobs.value = [...uploadJobs.value, job]
  } else {
    job.status = 'parsing'
    job.pct = 40
    job.error = ''
    job.name = `确认创建 ${planData.value.clusters.length} 个项目`
  }
  job.tick = setInterval(() => {
    if (job.pct < 95) job.pct += 1
  }, 500)
  try {
    const body = { plan_id: planId }
    if (planClustersOverride.value) body.clusters = planClustersOverride.value
    if (planDiscardOverride.value) body.discard = planDiscardOverride.value
    const res = await api.uploadConfirm(body)
    if (job.tick) {
      clearInterval(job.tick)
      job.tick = null
    }
    job.pct = 100
    job.status = 'done'
    job.plan = null
    const projects = res?.projects || []
    job.projectId = projects[0]?.id || ''
    job.name =
      projects.length === 1
        ? projects[0].title || job.name
        : `已创建 ${projects.length} 个项目`
    message.success(
      projects.length
        ? `已创建 ${projects.length} 个项目`
        : '未创建项目',
    )
    if (res?.discarded?.length) {
      message.info(`已剔除 ${res.discarded.length} 份无关材料`)
    }
    // 多项目时追加可点进详情的条目
    if (projects.length > 1) {
      const extras = projects.slice(1).map((p) => ({
        id: uploadSeq++,
        name: p.title || p.id,
        fileCount: 0,
        files: [],
        status: 'done',
        pct: 100,
        error: '',
        projectId: p.id,
        plan: null,
        tick: null,
      }))
      uploadJobs.value = [...uploadJobs.value, ...extras]
    }
    const goDetail = projects.length === 1 && projects[0].id
    planCloseFromConfirm = true
    planOpen.value = false
    planData.value = null
    planJobId.value = null
    planClustersOverride.value = null
    planDiscardOverride.value = null
    await load()
    if (goDetail) {
      router.push(`/projects/${projects[0].id}`)
    } else {
      queueMicrotask(() => openNextPendingPlan())
    }
  } catch (err) {
    if (job.tick) {
      clearInterval(job.tick)
      job.tick = null
    }
    job.status = sourceJob?.plan ? 'planned' : 'error'
    job.pct = 100
    const detail = err?.response?.data?.detail || err?.message || '创建失败'
    job.error = typeof detail === 'string' ? detail : JSON.stringify(detail)
  } finally {
    planConfirming.value = false
  }
}

const booted = ref(false)
const loading = ref(false)
const stats = reactive({
  total: 0,
  generating: 0,
  previewable: 0,
  monthly_tokens: 0,
  monthly_tokens_pipeline: 0,
  monthly_tokens_support: 0,
  monthly_budget: 1000000,
})

const sampleOpen = ref(false)
const sampleLoading = ref(false)
const sampleUseLlm = ref(true)
const sampleDomain = ref(null)
const sampleResult = ref(null)
const sampleDomainOptions = computed(() =>
  (catalog.value.domains || []).map((d) => ({ label: d.label || d.id, value: d.id })),
)

async function openSampleProposal() {
  sampleOpen.value = true
  sampleResult.value = null
  if (!catalog.value.domains?.length) {
    try {
      catalog.value = await getCatalog()
    } catch {
      /* ignore */
    }
  }
}

async function generateSample() {
  sampleLoading.value = true
  try {
    sampleResult.value = await api.sampleProposal({
      domain: sampleDomain.value || undefined,
      use_llm: sampleUseLlm.value,
    })
  } catch {
    /* api interceptor 已提示 */
  } finally {
    sampleLoading.value = false
  }
}

function downloadSample() {
  const r = sampleResult.value
  if (!r?.text) return
  const blob = new Blob([r.text], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = r.filename || '测试开题.txt'
  a.click()
  URL.revokeObjectURL(url)
  message.success('已开始下载')
}

const columns = [
  {
    title: '项目',
    key: 'title',
    render(row) {
      const when = row.updated_at || row.created_at
      const whenText = when ? new Date(when).toLocaleString() : ''
      const meta = [row.db_name, whenText ? `更新 ${whenText}` : ''].filter(Boolean).join(' · ')
      return h('div', {
        style: 'cursor:pointer;min-width:200px',
        onClick: () => router.push(`/projects/${row.id}`),
      }, [
        h('div', { style: 'font-weight:600;line-height:1.35' }, row.title),
        h('div', {
          class: 'small muted mono',
          style: 'display:inline-flex;align-items:center;gap:4px;margin-top:4px',
          onClick: (e) => e.stopPropagation(),
        }, [
          row.id,
          h(CopyIconButton, { text: row.id, tip: '复制项目 ID' }),
        ]),
        meta
          ? h('div', { class: 'small muted', style: 'margin-top:2px' }, meta)
          : null,
      ])
    },
  },
  {
    title: '骨架 · 领域',
    key: 'arch',
    render(row) {
      return formatArchDom(catalog.value, row.archetype, row.domain)
    },
  },
  {
    title: '状态',
    key: 'status',
    render(row) {
      const opts = { zipReady: row.zip_ready }
      return statusPillNode(
        projectStatusLabel(row.status, opts),
        projectStatusPill(row.status, opts),
      )
    },
  },
  {
    title: '运行',
    key: 'runtime',
    width: 160,
    render(row) {
      if (row.backend_running || row.frontend_running) {
        return h('div', { class: 'small' }, [
          statusPillNode('运行中', 'pill-green'),
          h('div', { class: 'mono muted', style: 'margin-top:4px' }, `${row.backend_port || '—'} / ${row.frontend_port || '—'}`),
        ])
      }
      return h('span', { class: 'muted' }, '—')
    },
  },
]

function formatK(n) {
  if (n >= 1000) return Math.round(n / 1000) + 'k'
  return String(n || 0)
}

function setFilter(f) {
  filter.value = f
  load()
}

const onSearch = debounce(() => load(), 300)

async function load() {
  try {
    const [s, items, cat] = await Promise.all([
      api.stats(),
      api.listProjects({ filter: filter.value, q: q.value || undefined }),
      getCatalog(),
    ])
    Object.assign(stats, s)
    list.value = items
    catalog.value = cat
  } finally {
    booted.value = true
  }
  await restorePendingPlans()
}

/** 从磁盘方案恢复待确认队列（刷新不丢；已待确认匹配 / 空堆由后端滤掉） */
async function restorePendingPlans() {
  try {
    const res = await api.uploadPlans()
    const items = res?.items || []
    if (!items.length) return
    const have = new Set(
      uploadJobs.value.map((j) => j.plan?.plan_id).filter(Boolean),
    )
    let added = 0
    for (const plan of items) {
      const pid = plan?.plan_id
      if (!pid || have.has(pid)) continue
      // 无簇（干扰项）不进队列
      if (!(plan.clusters || []).length) continue
      have.add(pid)
      const n = plan.clusters?.length || 0
      uploadJobs.value = [
        ...uploadJobs.value,
        {
          id: uploadSeq++,
          name: `分堆就绪 · ${n} 个项目`,
          fileCount: plan.files?.length || 0,
          files: [],
          status: 'planned',
          pct: 100,
          error: '',
          projectId: '',
          plan,
          tick: null,
          restored: true,
          // 恢复项默认搁置，避免刷新后自动弹窗抢焦点；点「查看分堆」再开
          deferred: true,
        },
      ]
      added += 1
    }
    if (added) {
      message.info(`已恢复 ${added} 个待确认分堆（已搁置，可点查看分堆）`)
    }
  } catch {
    // 恢复失败不挡列表
  }
}

async function discardPlanOnServer(planId) {
  if (!planId) return
  try {
    await api.uploadPlanDelete(planId)
  } catch {
    // 已不存在则忽略
  }
}

async function refresh() {
  if (loading.value) return
  loading.value = true
  try {
    await load()
  } finally {
    loading.value = false
  }
}

function jobPhaseLabel(job) {
  if (job.status === 'queued') return '待处理'
  if (job.status === 'uploading') return job.pct < 70 ? `上传中 ${job.pct}%` : '上传中'
  if (job.status === 'parsing') {
    return job.plan || job.name?.includes('确认') ? '正在创建项目' : '正在解析并分堆'
  }
  if (job.status === 'planned') {
    const n = job.plan?.clusters?.length
    const base = n != null ? `待确认分堆（${n} 个项目）` : '待确认分堆'
    return job.deferred ? `${base} · 已搁置` : base
  }
  if (job.status === 'done') return job.projectId ? '项目已创建' : (job.name?.includes('跳过') ? '已跳过' : '已完成')
  if (job.status === 'error') return '上传失败'
  return ''
}

function jobBarColor(job) {
  if (job.status === 'error') return 'var(--danger, #c45c5c)'
  if (job.status === 'done') return 'var(--green)'
  if (job.status === 'planned') return 'var(--teal, #2a9d8f)'
  if (job.status === 'queued') return 'var(--line-soft)'
  return ''
}

function dismissJob(id) {
  const job = uploadJobs.value.find((j) => j.id === id)
  if (job?.tick) clearInterval(job.tick)
  const planId = job?.plan?.plan_id
  uploadJobs.value = uploadJobs.value.filter((j) => j.id !== id)
  if (job?.status === 'planned' && planId) {
    discardPlanOnServer(planId)
  }
}

async function enqueueUpload(source) {
  let files = []
  try {
    const collected = await collectUploadMaterials(source, { maxFiles: MAX_UPLOAD_MATERIALS })
    if (collected.error) {
      message.warning(collected.error)
      return
    }
    files = collected.files
    if (collected.notes?.length) {
      collected.notes.forEach((n) => message.info(n))
    }
    if (collected.skipped?.length && !files.length) {
      message.warning(`没有可用材料：${collected.skipped.slice(0, 3).join('、')}`)
      return
    }
    if (collected.skipped?.length) {
      message.warning(`已跳过 ${collected.skipped.length} 项非材料文件`)
    }
  } catch (err) {
    message.error(err?.message || '读取文件失败')
    return
  }
  if (!files.length) {
    message.warning('请至少选择一份材料（PDF / Word / TXT，或含这些文件的文件夹 / zip）')
    return
  }
  const name = files.length === 1 ? files[0].name : `${files[0].name} 等 ${files.length} 份`
  uploadJobs.value = [
    ...uploadJobs.value,
    {
      id: uploadSeq++,
      name,
      fileCount: files.length,
      files,
      status: 'queued',
      pct: 0,
      error: '',
      projectId: '',
      tick: null,
    },
  ]
  pumpUploadQueue()
}

function pumpUploadQueue() {
  while (activeUploads < UPLOAD_CONCURRENCY) {
    const next = uploadJobs.value.find((j) => j.status === 'queued')
    if (!next) break
    activeUploads += 1
    next.status = 'uploading'
    next.pct = 0
    runUploadJob(next).finally(() => {
      activeUploads -= 1
      pumpUploadQueue()
    })
  }
}

async function runUploadJob(job) {
  try {
    const plan = await api.uploadPlan(job.files, (e) => {
      if (!e.total) return
      const pct = Math.round((e.loaded / e.total) * 70)
      job.pct = Math.min(70, pct)
      if (e.loaded >= e.total) {
        job.status = 'parsing'
        if (!job.tick) {
          job.tick = setInterval(() => {
            if (job.pct < 92) job.pct += 1
          }, 400)
        }
      }
    })
    if (job.tick) {
      clearInterval(job.tick)
      job.tick = null
    }
    job.pct = 100
    job.status = 'planned'
    job.plan = plan
    job.clustersOverride = null
    job.discardOverride = null
    job.name = `分堆就绪 · ${plan?.clusters?.length || 0} 个项目`
    const n = (plan?.clusters || []).length
    const discarded = (plan?.discard || []).length
    const opened = showPlanForJob(job)
    if (opened) {
      message.success(
        `识别为 ${n} 个项目` +
          (discarded ? `，剔除 ${discarded} 份` : '') +
          '，请确认',
      )
    } else {
      message.info(
        `另有分堆就绪（${n} 个项目）· 当前弹窗确认完后可点「查看分堆」（待确认 ${pendingPlanCount()}）`,
      )
    }
  } catch (err) {
    if (job.tick) {
      clearInterval(job.tick)
      job.tick = null
    }
    job.status = 'error'
    job.pct = 100
    const detail = err?.response?.data?.detail || err?.message || '上传失败'
    job.error = typeof detail === 'string' ? detail : JSON.stringify(detail)
  }
}

async function onFile(e) {
  await enqueueUpload(e.target)
  e.target.value = ''
}

async function onDrop(e) {
  dragover.value = false
  await enqueueUpload(e)
}

onMounted(load)
onUnmounted(() => {
  onSearch.cancel()
  for (const job of uploadJobs.value) {
    if (job.tick) clearInterval(job.tick)
  }
})
</script>

<style scoped>
.plan-cluster {
  margin: 0;
  border: 1px solid var(--line-soft);
  border-radius: 8px;
  padding: 10px 12px;
  background: var(--panel, transparent);
}
.plan-cluster-idx {
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 600;
  color: var(--muted);
}
.plan-cluster-title {
  font-weight: 600;
  line-height: 1.35;
  word-break: break-word;
}
.plan-cluster-files {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}
.plan-file-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 100%;
  padding: 3px 8px;
  border-radius: 6px;
  background: var(--chip-bg, rgba(0, 0, 0, 0.04));
  font-size: 12px;
  line-height: 1.35;
  word-break: break-all;
}
.plan-file-chip .muted {
  color: var(--muted);
  flex-shrink: 0;
}
.plan-file-chip--discard {
  opacity: 0.85;
  text-decoration: line-through;
}
</style>
