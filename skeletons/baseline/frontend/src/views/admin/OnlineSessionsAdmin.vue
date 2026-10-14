<template>
  <div>
    <div class="toolbar">
      <h2 class="title">{{ labels.onlineSessionsMenu || '在线用户' }}</h2>
      <el-button @click="load">刷新</el-button>
    </div>
    <div class="table-scroll">
      <el-table :data="list" stripe v-loading="loading">
        <el-table-column prop="username" label="用户名" width="120" />
        <el-table-column prop="ip" label="IP" width="140" />
        <el-table-column prop="userAgent" label="设备" min-width="220" show-overflow-tooltip />
        <el-table-column prop="createdAt" label="登录时间" width="170" />
        <el-table-column prop="lastSeenAt" label="最近活动" width="170" />
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button link type="danger" @click="kick(row)">强制下线</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'
import { schemaLabels } from '../../utils/domainSchema.js'

const labels = schemaLabels()
const list = ref([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const res = await http.get('/api/admin/online-sessions')
    list.value = res.data || []
  } finally {
    loading.value = false
  }
}

async function kick(row) {
  await ElMessageBox.confirm(`确定将 ${row.username} 强制下线？`, '提示', { type: 'warning' })
  await http.post(`/api/admin/online-sessions/${encodeURIComponent(row.sessionId)}/kick`)
  ElMessage.success('已强制下线')
  load()
}

onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.title { margin: 0; font-size: 1.1rem; flex: 1; }
.table-scroll { overflow-x: auto; }
</style>
