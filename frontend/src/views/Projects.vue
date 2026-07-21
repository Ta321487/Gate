<template>
  <div>
    <h1 class="page-title">项目</h1>
    <p class="page-desc">
      上传开题、任务书等材料以创建项目（可多选，至少一份）。
      单次上传对应一个项目；如需创建多个项目，请分次提交，系统将按队列依次处理并展示进度。
    </p>

    <div
      class="dropzone"
      :class="{ dragover }"
      @dragover.prevent="dragover = true"
      @dragleave="dragover = false"
      @drop.prevent="onDrop"
    >
      <input type="file" multiple accept=".pdf,.doc,.docx,.txt" @change="onFile" />
      <div class="dropzone-icon">↑</div>
      <div class="dropzone-title">拖入材料，或点击选择</div>
      <div class="dropzone-hint">
        单次最多 8 份（同一项目）· 多个项目请分次上传 · 支持 PDF / Word / TXT
      </div>
    </div>

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
                v-if="job.status === 'done' && job.projectId"
                size="tiny"
                @click="router.push(`/projects/${job.projectId}`)"
              >查看</n-button>
              <n-button
                v-if="job.status === 'done' || job.status === 'error'"
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
        <div class="stat"><div class="label">生成中</div><div class="value">{{ stats.generating }}</div><div class="hint">含排队</div></div>
        <div class="stat"><div class="label">可预览</div><div class="value">{{ stats.previewable }}</div><div class="hint">已生成 / 运行中</div></div>
        <div class="stat"><div class="label">本月 Token</div><div class="value">{{ formatK(stats.monthly_tokens) }}</div><div class="hint">预算 {{ formatK(stats.monthly_budget) }}</div></div>
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
                <div class="empty-desc">上传材料即可创建项目；多个项目请分次提交</div>
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
/** 与状态/运行列语义对齐：运行中 · 可交付 · 质检未过 */
const filters = [
  { id: 'all', label: '全部', pill: 'pill-neutral' },
  { id: 'active', label: '运行中', pill: 'pill-green' },
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
 *  status: 'queued'|'uploading'|'parsing'|'done'|'error'
 *  pct: number
 *  error: string
 *  projectId: string
 *  tick: any
 * }>>} */
const uploadJobs = ref([])
let uploadSeq = 1
/** 同时跑几路上传（Match Agent 较重，默认 2） */
const UPLOAD_CONCURRENCY = 2
let activeUploads = 0

const uploadQueueHint = computed(() => {
  const jobs = uploadJobs.value
  const running = jobs.filter((j) => j.status === 'uploading' || j.status === 'parsing').length
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

const booted = ref(false)
const loading = ref(false)
const stats = reactive({ total: 0, generating: 0, previewable: 0, monthly_tokens: 0, monthly_budget: 1000000 })

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
  if (job.status === 'uploading') return job.pct < 90 ? `上传中 ${job.pct}%` : '上传中'
  if (job.status === 'parsing') return '正在解析并匹配'
  if (job.status === 'done') return '项目已创建'
  if (job.status === 'error') return '上传失败'
  return ''
}

function jobBarColor(job) {
  if (job.status === 'error') return 'var(--danger, #c45c5c)'
  if (job.status === 'done') return 'var(--green)'
  if (job.status === 'queued') return 'var(--line-soft)'
  return ''
}

function dismissJob(id) {
  const job = uploadJobs.value.find((j) => j.id === id)
  if (job?.tick) clearInterval(job.tick)
  uploadJobs.value = uploadJobs.value.filter((j) => j.id !== id)
}

function enqueueUpload(fileList) {
  const files = [...(fileList || [])].filter(Boolean)
  if (!files.length) {
    message.warning('请至少选择一份材料')
    return
  }
  if (files.length > 8) {
    message.warning('单次最多 8 份材料；多个项目请分次上传')
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
    const project = await api.upload(job.files, (e) => {
      if (!e.total) return
      const pct = Math.round((e.loaded / e.total) * 90)
      job.pct = Math.min(90, pct)
      if (e.loaded >= e.total) {
        job.status = 'parsing'
        if (!job.tick) {
          job.tick = setInterval(() => {
            if (job.pct < 98) job.pct += 1
          }, 400)
        }
      }
    })
    if (job.tick) {
      clearInterval(job.tick)
      job.tick = null
    }
    job.pct = 100
    job.status = 'done'
    job.projectId = project?.id || ''
    message.success(
      job.fileCount > 1
        ? `项目「${project?.title || job.name}」已创建（${job.fileCount} 份材料）`
        : `项目「${project?.title || job.name}」已创建`,
    )
    await load()
    const stillBusy = uploadJobs.value.some(
      (j) => j.id !== job.id && (j.status === 'queued' || j.status === 'uploading' || j.status === 'parsing'),
    )
    // 多批时留在列表；仅单独一批成功时进详情（沿用旧习惯）
    if (!stillBusy && job.projectId) {
      const doneCount = uploadJobs.value.filter((j) => j.status === 'done').length
      const errCount = uploadJobs.value.filter((j) => j.status === 'error').length
      if (doneCount === 1 && errCount === 0) {
        router.push(`/projects/${job.projectId}`)
      }
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

function onFile(e) {
  enqueueUpload(e.target.files)
  e.target.value = ''
}

function onDrop(e) {
  dragover.value = false
  enqueueUpload(e.dataTransfer.files)
}

onMounted(load)
onUnmounted(() => {
  onSearch.cancel()
  for (const job of uploadJobs.value) {
    if (job.tick) clearInterval(job.tick)
  }
})
</script>
