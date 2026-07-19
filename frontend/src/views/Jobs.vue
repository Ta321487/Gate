<template>
  <div class="page-fill">
    <h1 class="page-title">任务队列</h1>
    <p class="page-desc">生成任务状态、取消与重试。</p>
    <PageSkeleton v-if="!booted" variant="list" />
    <div v-else class="panel panel-fill">
      <div class="panel-hd">
        <h3>任务列表</h3>
        <div class="row" style="gap:8px">
          <n-button size="small" @click="load">刷新</n-button>
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
        <n-data-table :columns="columns" :data="list" :bordered="false" size="small">
          <template #empty>
            <div class="empty-hint">
              <div class="empty-title">暂无任务</div>
              <div class="empty-desc">上传开题并开始生成后，任务会出现在这里</div>
            </div>
          </template>
        </n-data-table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { h, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NTag } from 'naive-ui'
import { api, message, confirm } from '../api'
import PageSkeleton from '../components/PageSkeleton.vue'

const router = useRouter()
const list = ref([])
const purging = ref(false)
const booted = ref(false)
let timer = null

const statusType = {
  queued: 'default',
  running: 'info',
  success: 'success',
  failed: 'error',
  cancelled: 'default',
}
const statusLabel = {
  queued: '排队',
  running: '运行中',
  success: '成功',
  failed: '失败',
  cancelled: '已取消',
}

async function act(fn, okMsg) {
  const res = await fn()
  message.success(typeof res === 'string' ? res : (okMsg || '完成'))
  await load()
}

const columns = [
  { title: 'Job', key: 'id', width: 90, render: (r) => h('span', { class: 'mono' }, `#${r.id}`) },
  { title: '项目', key: 'project_title', render: (r) => r.project_title || r.project_id },
  { title: '步骤', key: 'step' },
  {
    title: '状态',
    key: 'status',
    render: (r) => h(NTag, { size: 'small', type: statusType[r.status] || 'default', bordered: false }, { default: () => statusLabel[r.status] || r.status }),
  },
  {
    title: '进度',
    key: 'progress',
    width: 80,
    render: (r) => `${r.progress || 0}%`,
  },
  {
    title: '',
    key: 'actions',
    width: 200,
    render: (r) => {
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
          onClick: () => act(() => api.cancelJob(r.id), '已取消'),
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
      return h('div', { class: 'row' }, btns)
    },
  },
]

async function load() {
  try {
    const data = await api.listJobs()
    list.value = Array.isArray(data) ? data : []
  } catch {
    /* api 拦截器已提示 */
  } finally {
    booted.value = true
  }
}

async function purgeOrphans() {
  const ok = await confirm('确认删除所有「项目已不存在」的任务？此操作不可恢复。', {
    title: '清空孤儿任务',
    type: 'error',
    positiveText: '确认删除',
  })
  if (!ok) return
  purging.value = true
  try {
    const res = await api.purgeOrphanJobs()
    message.success(res.message || '已清空')
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
