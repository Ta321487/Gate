<template>
  <div>
    <h1 class="page-title">项目</h1>
    <p class="page-desc">上传开题报告创建项目。</p>

    <div
      class="dropzone"
      :class="{ dragover }"
      @dragover.prevent="dragover = true"
      @dragleave="dragover = false"
      @drop.prevent="onDrop"
    >
      <input type="file" accept=".pdf,.doc,.docx,.txt" @change="onFile" />
      <div class="dropzone-icon">↑</div>
      <div class="dropzone-title">拖入开题报告，或点击选择</div>
      <div class="dropzone-hint">支持 PDF / Word / TXT · 上传后自动解析题目并创建项目</div>
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
          <n-button size="small" @click="load">刷新</n-button>
        </div>
        <div class="panel-bd" style="padding-top:12px">
          <div class="row mb-12" style="justify-content:space-between">
            <n-button-group size="small">
              <n-button :type="filter==='all'?'primary':'default'" @click="setFilter('all')">全部</n-button>
              <n-button :type="filter==='active'?'primary':'default'" @click="setFilter('active')">进行中</n-button>
              <n-button :type="filter==='done'?'primary':'default'" @click="setFilter('done')">可交付</n-button>
              <n-button :type="filter==='fail'?'primary':'default'" @click="setFilter('fail')">失败</n-button>
            </n-button-group>
            <n-input v-model:value="q" clearable placeholder="搜索题目 / ID…" style="width:220px" @update:value="onSearch" />
          </div>
          <n-data-table :columns="columns" :data="list" :row-key="r => r.id" :bordered="false" size="small">
            <template #empty>
              <div class="empty-hint">
                <div class="empty-title">暂无项目</div>
                <div class="empty-desc">拖入开题报告即可创建</div>
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
import { NButton, NTag } from 'naive-ui'
import { api, message } from '../api'
import PageSkeleton from '../components/PageSkeleton.vue'
import CopyIconButton from '../components/CopyIconButton.vue'
import {
  debounce,
  formatArchDom,
  getCatalog,
  projectStatusLabel,
  projectStatusTag,
} from '../opsShared'

const router = useRouter()
const list = ref([])
const catalog = ref({ archetypes: [], domains: [] })
const filter = ref('all')
const q = ref('')
const dragover = ref(false)
const uploading = ref(false)
const uploadName = ref('')
const uploadPct = ref(0)
const uploadPhase = ref('')
const booted = ref(false)
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
      return h(NTag, {
        size: 'small',
        type: projectStatusTag(row.status, opts),
        bordered: false,
      }, { default: () => projectStatusLabel(row.status, opts) })
    },
  },
  {
    title: '运行',
    key: 'runtime',
    width: 160,
    render(row) {
      if (row.backend_running || row.frontend_running) {
        return h('div', { class: 'small' }, [
          h(NTag, { size: 'tiny', type: 'success', bordered: false }, { default: () => '运行中' }),
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

async function doUpload(file) {
  if (!file) return
  uploading.value = true
  uploadName.value = file.name
  uploadPct.value = 0
  uploadPhase.value = '上传文件…'
  let tick = null
  try {
    const project = await api.upload(file, (e) => {
      if (!e.total) return
      // 传输进度最多到 90%：字节传完后服务端还要解析开题 / 匹配领域
      const pct = Math.round((e.loaded / e.total) * 90)
      uploadPct.value = Math.min(90, pct)
      if (e.loaded >= e.total) {
        uploadPhase.value = '解析开题 · 匹配领域…'
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
    message.success('已建项')
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
  doUpload(e.target.files?.[0])
  e.target.value = ''
}

function onDrop(e) {
  dragover.value = false
  doUpload(e.dataTransfer.files?.[0])
}

onMounted(load)
onUnmounted(() => onSearch.cancel())
</script>
