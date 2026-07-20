<template>
  <div>
    <h1 class="page-title">项目</h1>
    <p class="page-desc">上传开题、任务书等材料创建项目（可多选，至少一份）。</p>

    <div
      class="dropzone"
      :class="{ dragover }"
      @dragover.prevent="dragover = true"
      @dragleave="dragover = false"
      @drop.prevent="onDrop"
    >
      <input type="file" multiple accept=".pdf,.doc,.docx,.txt" @change="onFile" />
      <div class="dropzone-icon">↑</div>
      <div class="dropzone-title">拖入材料，或点击多选</div>
      <div class="dropzone-hint">支持开题 / 任务书 / 功能清单 · PDF / Word（.docx 直读，.doc 需本机 Word 或 LibreOffice）· 最多 8 份</div>
    </div>

    <div v-if="uploading" class="panel mb-16">
      <div class="panel-bd">
        <div class="row" style="justify-content:space-between;margin-bottom:8px">
          <span>{{ uploadName }}</span>
          <span class="muted">{{ uploadPhase }}</span>
        </div>
        <div class="progress"><i :style="{ width: uploadPct + '%' }" /></div>
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
                <div class="empty-desc">拖入开题或任务书即可创建</div>
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
import { h, onMounted, onUnmounted, reactive, ref } from 'vue'
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
/** 与状态/运行列语义对齐：运行中 · 可交付 · 失败 */
const filters = [
  { id: 'all', label: '全部', pill: 'pill-neutral' },
  { id: 'active', label: '运行中', pill: 'pill-green' },
  { id: 'done', label: '可交付', pill: 'pill-teal' },
  { id: 'fail', label: '失败', pill: 'pill-red' },
]
const q = ref('')
const dragover = ref(false)
const uploading = ref(false)
const uploadName = ref('')
const uploadPct = ref(0)
const uploadPhase = ref('')
const booted = ref(false)
const loading = ref(false)
const stats = reactive({ total: 0, generating: 0, previewable: 0, monthly_tokens: 0, monthly_budget: 1000000 })

const columns = [
  {
    title: '项目',
    key: 'title',
    render(row) {
      return h('div', {
        style: 'cursor:pointer',
        onClick: () => router.push(`/projects/${row.id}`),
      }, [
        h('div', { style: 'font-weight:600' }, row.title),
        h('div', {
          class: 'small muted mono',
          style: 'display:inline-flex;align-items:center;gap:4px',
          onClick: (e) => e.stopPropagation(),
        }, [
          row.id,
          h(CopyIconButton, { text: row.id, tip: '复制项目 ID' }),
        ]),
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
  {
    title: '更新',
    key: 'updated_at',
    render(row) {
      return row.updated_at ? new Date(row.updated_at).toLocaleString() : '—'
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

async function doUpload(fileList) {
  const files = [...(fileList || [])].filter(Boolean)
  if (!files.length) {
    message.warning('请至少选择一份材料')
    return
  }
  if (files.length > 8) {
    message.warning('单次最多 8 份材料')
    return
  }
  uploading.value = true
  uploadName.value = files.length === 1 ? files[0].name : `${files[0].name} 等 ${files.length} 份`
  uploadPct.value = 0
  uploadPhase.value = '上传文件…'
  let tick = null
  try {
    const project = await api.upload(files, (e) => {
      if (!e.total) return
      const pct = Math.round((e.loaded / e.total) * 90)
      uploadPct.value = Math.min(90, pct)
      if (e.loaded >= e.total) {
        uploadPhase.value = '解析材料 · 匹配领域…'
        if (!tick) {
          tick = setInterval(() => {
            if (uploadPct.value < 98) uploadPct.value += 1
          }, 400)
        }
      } else {
        uploadPhase.value = `上传中 ${Math.round((e.loaded / e.total) * 100)}%`
      }
    })
    if (tick) clearInterval(tick)
    uploadPct.value = 100
    uploadPhase.value = '完成'
    message.success(files.length > 1 ? `已建项（${files.length} 份材料）` : '已建项')
    if (!project?.id) {
      message.error('建项成功但未返回项目 ID，请从列表进入')
      await load()
      return
    }
    router.push(`/projects/${project.id}`)
  } finally {
    if (tick) clearInterval(tick)
    uploading.value = false
    uploadPhase.value = ''
  }
}

function onFile(e) {
  doUpload(e.target.files)
  e.target.value = ''
}

function onDrop(e) {
  dragover.value = false
  doUpload(e.dataTransfer.files)
}

onMounted(load)
onUnmounted(() => onSearch.cancel())
</script>
