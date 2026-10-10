<template>
  <div>
    <section class="hero">
      <h1>下载台账</h1>
      <p class="muted">查看下载记录、审核申请与纠错投诉。</p>
    </section>

    <el-tabs v-model="tab">
      <el-tab-pane label="下载记录" name="logs">
        <el-table :data="logs" stripe>
          <el-table-column prop="title" label="资料" min-width="160" />
          <el-table-column prop="username" label="用户" width="120" />
          <el-table-column prop="downloadedAt" label="时间" min-width="160" />
        </el-table>
      </el-tab-pane>

      <el-tab-pane v-if="auditOn" :label="labels.adminDownloadRequestLabel || '下载审核'" name="requests">
        <el-table :data="requests" stripe>
          <el-table-column prop="title" label="资料" min-width="140" />
          <el-table-column prop="username" label="用户" width="110" />
          <el-table-column prop="status" label="状态" width="100" />
          <el-table-column prop="createdAt" label="申请时间" min-width="150" />
          <el-table-column label="操作" width="160">
            <template #default="{ row }">
              <el-button
                v-if="row.status === 'pending'"
                link
                type="primary"
                @click="handleReq(row, 'approved')"
              >通过</el-button>
              <el-button
                v-if="row.status === 'pending'"
                link
                type="danger"
                @click="handleReq(row, 'rejected')"
              >驳回</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane v-if="feedbackOn" :label="labels.adminFeedbackLabel || '纠错与投诉'" name="feedback">
        <el-table :data="feedback" stripe>
          <el-table-column prop="title" label="资料" min-width="120" />
          <el-table-column prop="username" label="用户" width="100" />
          <el-table-column prop="kind" label="类型" width="100">
            <template #default="{ row }">
              {{ row.kind === 'infringement' ? '侵权' : '纠错' }}
            </template>
          </el-table-column>
          <el-table-column prop="body" label="内容" min-width="180" />
          <el-table-column prop="status" label="状态" width="90" />
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button
                v-if="row.status === 'pending'"
                link
                type="primary"
                @click="handleFb(row, 'handled')"
              >已处理</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/http'
import { getSchema } from '../../utils/domainSchema'

const tab = ref('logs')
const logs = ref([])
const requests = ref([])
const feedback = ref([])

const schema = computed(() => getSchema() || {})
const labels = computed(() => schema.value.labels || {})
const thicken = computed(() => schema.value.contentThicken || {})
const auditOn = computed(() => !!thicken.value.downloadAudit)
const feedbackOn = computed(() => !!thicken.value.docFeedback)

async function loadLogs() {
  const res = await http.get('/api/doclib/admin/logs', { params: { page: 1, size: 50 } })
  logs.value = (res.data?.data || res.data || {}).list || []
}

async function loadRequests() {
  if (!auditOn.value) return
  const res = await http.get('/api/doclib/admin/download-requests', {
    params: { page: 1, size: 50, status: 'pending' },
  })
  requests.value = (res.data?.data || res.data || {}).list || []
}

async function loadFeedback() {
  if (!feedbackOn.value) return
  const res = await http.get('/api/doclib/admin/feedback', {
    params: { page: 1, size: 50, status: 'pending' },
  })
  feedback.value = (res.data?.data || res.data || {}).list || []
}

async function handleReq(row, status) {
  await http.put(`/api/doclib/admin/download-requests/${row.id}`, { status })
  ElMessage.success(status === 'approved' ? '已通过' : '已驳回')
  await loadRequests()
}

async function handleFb(row, status) {
  await http.put(`/api/doclib/admin/feedback/${row.id}`, { status })
  ElMessage.success('已处理')
  await loadFeedback()
}

watch(tab, (v) => {
  if (v === 'requests') loadRequests()
  if (v === 'feedback') loadFeedback()
})

onMounted(async () => {
  await loadLogs()
  await loadRequests()
  await loadFeedback()
})
</script>

<style scoped>
.hero { margin-bottom: 1rem; }
.muted { color: var(--el-text-color-secondary); }
</style>
