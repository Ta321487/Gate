<template>
  <div>
    <div class="toolbar">
      <h2 class="title">{{ labels.scheduleJobsMenu || '定时任务' }}</h2>
      <el-button @click="load">刷新</el-button>
    </div>
    <p class="hint">{{ labels.scheduleJobsHint || '以下为本系统已启用的定时任务；本页只读说明，不能改调度。' }}</p>
    <p v-if="delayMs" class="meta">扫描间隔约 {{ Math.round(delayMs / 1000) }} 秒</p>
    <el-table :data="list" stripe v-loading="loading">
      <el-table-column prop="title" label="任务" min-width="160" />
      <el-table-column prop="detail" label="说明" min-width="220" show-overflow-tooltip />
      <el-table-column prop="threshold" label="阈值" width="140" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag size="small" :type="row.armed ? 'success' : 'info'">
            {{ row.armed ? '已启用' : '未启用' }}
          </el-tag>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import http from '../../api/http'
import { schemaLabels } from '../../utils/domainSchema.js'

const labels = schemaLabels()
const list = ref([])
const loading = ref(false)
const delayMs = ref(0)

async function load() {
  loading.value = true
  try {
    const res = await http.get('/api/admin/schedule-jobs')
    list.value = Array.isArray(res.data?.list) ? res.data.list : []
    delayMs.value = Number(res.data?.delayMs || 0)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.title { margin: 0; flex: 1; font-size: 18px; }
.hint { margin: 0 0 6px; color: var(--portal-muted, #909399); font-size: 13px; line-height: 1.5; }
.meta { margin: 0 0 12px; font-size: 12px; color: var(--portal-muted, #909399); }
</style>
