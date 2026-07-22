<template>
  <div class="page-fill">
    <h1 class="page-title">任务队列</h1>
    <p class="page-desc">生成任务状态、取消、清空历史与清理失效。</p>
    <PageSkeleton v-if="!booted" variant="list" />
    <div v-else class="panel panel-fill">
      <div class="panel-hd">
        <h3>任务列表</h3>
        <div class="row" style="gap:8px;flex-wrap:wrap">
          <n-button size="small" :loading="loading" @click="refresh">刷新</n-button>
          <n-button
            size="small"
            secondary
            type="warning"
            :loading="purgingFinished"
            :disabled="!finishedCount"
            @click="purgeFinished"
          >清空历史（{{ finishedCount }}）</n-button>
          <n-button
            size="small"
            secondary
            type="error"
            :loading="purging"
            @click="purgeOrphans"
          >清空项目不存在的任务</n-button>
        </div>
      </div>
      <div class="panel-bd panel-bd-fill">
        <n-data-table
          :columns="columns"
          :data="treeList"
          :row-key="rowKey"
          :expanded-row-keys="expandedKeys"
          :bordered="false"
          size="small"
          @update:expanded-row-keys="onExpandedKeys"
        >
          <template #empty>
            <div class="empty-hint">
              <div class="empty-title">暂无任务</div>
              <div class="empty-desc">在「项目」上传材料并开始生成后，任务会出现在这里</div>
            </div>
          </template>
        </n-data-table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, h, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NButton } from 'naive-ui'
import { api, message, confirm } from '../api'
import PageSkeleton from '../components/PageSkeleton.vue'
import { JOB_STATUS, statusPillNode } from '../opsShared'

const router = useRouter()
const list = ref([])
const treeList = ref([])
const expandedKeys = ref([])
const loading = ref(false)
const purging = ref(false)
const purgingFinished = ref(false)
const booted = ref(false)
let timer = null

const finishedCount = computed(
  () => list.value.filter((j) => ['success', 'failed', 'cancelled'].includes(j.status)).length,
)

function jobTime(j) {
  const t = j.started_at || j.created_at
  return t ? new Date(t).getTime() : 0
}

function titleKey(j) {
  return String(j.project_title || '').trim()
}

function groupId(title) {
  return `g:${title}`
}

function summarizeStatuses(jobs) {
  const counts = new Map()
  for (const j of jobs) {
    const key = j.status || 'unknown'
    counts.set(key, (counts.get(key) || 0) + 1)
  }
  const order = ['running', 'queued', 'failed', 'success', 'cancelled']
  const parts = []
  for (const s of order) {
    const n = counts.get(s)
    if (!n) continue
    const m = JOB_STATUS[s] || { label: s }
    parts.push(`${m.label} ${n}`)
    counts.delete(s)
  }
  for (const [s, n] of counts) {
    const m = JOB_STATUS[s] || { label: s }
    parts.push(`${m.label} ${n}`)
  }
  return parts.join(' · ')
}

/** 非空标题相同且 ≥2 条折叠为组头 + children；空标题不折叠 */
function buildJobTree(jobs) {
  const buckets = new Map()
  const singles = []
  for (const j of jobs) {
    const key = titleKey(j)
    if (!key) {
      singles.push({ job: j, sort: jobTime(j) })
      continue
    }
    if (!buckets.has(key)) buckets.set(key, [])
    buckets.get(key).push(j)
  }

  const rows = []
  for (const [title, group] of buckets) {
    if (group.length === 1) {
      rows.push({ row: group[0], sort: jobTime(group[0]) })
      continue
    }
    const children = [...group].sort((a, b) => jobTime(b) - jobTime(a))
    rows.push({
      row: {
        id: groupId(title),
        isGroup: true,
        project_title: title,
        children,
        statusSummary: summarizeStatuses(children),
      },
      sort: jobTime(children[0]),
    })
  }
  for (const s of singles) rows.push({ row: s.job, sort: s.sort })
  rows.sort((a, b) => b.sort - a.sort)
  return rows.map((x) => x.row)
}

function rowKey(r) {
  return r.isGroup ? r.id : r.id
}

function onExpandedKeys(keys) {
  expandedKeys.value = keys
}

function pruneExpanded(tree) {
  const alive = new Set(tree.filter((r) => r.isGroup).map((r) => r.id))
  expandedKeys.value = expandedKeys.value.filter((k) => alive.has(k))
}

async function act(fn, okMsg) {
  const res = await fn()
  message.success(typeof res === 'string' ? res : (okMsg || '完成'))
  await load()
}

const columns = [
  {
    title: '任务',
    key: 'id',
    width: 90,
    render: (r) => {
      if (r.isGroup) return h('span', { class: 'muted' }, '—')
      return h('span', { class: 'mono' }, `#${r.id}`)
    },
  },
  {
    title: '项目',
    key: 'project_title',
    render: (r) => {
      if (r.isGroup) {
        return h('div', { style: 'min-width:180px' }, [
          h('div', { style: 'font-weight:600;line-height:1.35' }, r.project_title),
          h('div', { class: 'small muted', style: 'margin-top:4px' }, `共 ${r.children.length} 条`),
        ])
      }
      const title = r.project_title || '（无标题）'
      const when = r.started_at || r.created_at
      const whenText = when ? new Date(when).toLocaleString() : ''
      return h('div', { style: 'min-width:180px' }, [
        h('div', { style: 'font-weight:600;line-height:1.35' }, title),
        h('div', { class: 'small muted mono', style: 'margin-top:4px' }, r.project_id || '—'),
        whenText
          ? h('div', { class: 'small muted', style: 'margin-top:2px' }, `开始 ${whenText}`)
          : null,
      ])
    },
  },
  {
    title: '步骤',
    key: 'step',
    render: (r) => (r.isGroup ? h('span', { class: 'muted' }, '—') : r.step),
  },
  {
    title: '状态',
    key: 'status',
    render: (r) => {
      if (r.isGroup) {
        return h('span', { class: 'small muted' }, r.statusSummary || '—')
      }
      const m = JOB_STATUS[r.status] || { label: r.status, pill: 'pill-neutral' }
      const pill = statusPillNode(m.label, m.pill)
      if (r.error && (r.status === 'failed' || r.status === 'cancelled')) {
        return h('div', { title: r.error }, [
          pill,
          h('div', { class: 'small muted', style: 'margin-top:4px;max-width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis' }, r.error),
        ])
      }
      return pill
    },
  },
  {
    title: '进度',
    key: 'progress',
    width: 80,
    render: (r) => (r.isGroup ? h('span', { class: 'muted' }, '—') : `${r.progress || 0}%`),
  },
  {
    title: '',
    key: 'actions',
    width: 220,
    render: (r) => {
      if (r.isGroup) return null
      const btns = [
        h(NButton, {
          text: true,
          size: 'small',
          onClick: () => router.push(`/projects/${r.project_id}`),
        }, { default: () => '详情' }),
      ]
      if (r.status === 'queued' || r.status === 'running') {
        btns.push(h(NButton, {
          size: 'small',
          type: 'error',
          secondary: true,
          onClick: async () => {
            const ok = await confirm('确认取消该生成任务？进行中的步骤将中止。', {
              title: '取消任务',
              type: 'warning',
              positiveText: '确认取消',
            })
            if (!ok) return
            await act(() => api.cancelJob(r.id), '已取消')
          },
        }, { default: () => '取消' }))
      }
      if (r.status === 'failed') {
        btns.push(h(NButton, {
          size: 'small',
          onClick: () => act(async () => {
            const res = await api.retryJob(r.id)
            return res?.message || '已从失败步骤续跑'
          }),
        }, { default: () => '重试' }))
      }
      if (['success', 'failed', 'cancelled'].includes(r.status)) {
        btns.push(h(NButton, {
          size: 'small',
          quaternary: true,
          type: 'error',
          onClick: async () => {
            const ok = await confirm(`确定删除任务 #${r.id}？`, {
              title: '删除任务',
              type: 'warning',
              positiveText: '删除',
            })
            if (!ok) return
            await act(() => api.deleteJob(r.id), '已删除')
          },
        }, { default: () => '删除' }))
      }
      return h('div', { class: 'row' }, btns)
    },
  },
]

async function load() {
  try {
    const data = await api.listJobs()
    list.value = Array.isArray(data) ? data : []
    const tree = buildJobTree(list.value)
    treeList.value = tree
    pruneExpanded(tree)
  } catch {
    /* api 拦截器已提示 */
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

async function purgeFinished() {
  const ok = await confirm(
    `将删除成功、失败与已取消的任务（共 ${finishedCount.value} 条），进行中的不受影响。`,
    {
      title: '清空历史',
      type: 'warning',
      positiveText: '清空',
    },
  )
  if (!ok) return
  purgingFinished.value = true
  try {
    const res = await api.purgeFinishedJobs()
    message.success(res.message || '已清空历史')
    await load()
  } finally {
    purgingFinished.value = false
  }
}

async function purgeOrphans() {
  const ok = await confirm('将清空项目已不存在的任务，此操作不可恢复。', {
    title: '清空项目不存在的任务',
    type: 'error',
    positiveText: '清空',
  })
  if (!ok) return
  purging.value = true
  try {
    const res = await api.purgeOrphanJobs()
    message.success(res.message || '已清空项目不存在的任务')
    await load()
  } finally {
    purging.value = false
  }
}

onMounted(() => {
  load()
  timer = setInterval(load, 3000)
})
onUnmounted(() => clearInterval(timer))
</script>

<style scoped>
.page-fill {
  display: flex;
  flex-direction: column;
  /* topbar 52 + content 上下 padding 48 */
  min-height: calc(100dvh - 100px);
}
.panel-fill {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.panel-bd-fill {
  flex: 1;
  min-height: 0;
  padding: 0 !important;
  overflow: auto;
}
</style>
