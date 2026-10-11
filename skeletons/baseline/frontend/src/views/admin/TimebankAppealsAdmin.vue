<template>
  <div>
    <h2>{{ title }}</h2>
    <el-table :data="list" stripe>
      <el-table-column prop="createdAt" label="时间" width="180" />
      <el-table-column prop="username" label="用户" width="120" />
      <el-table-column prop="reason" label="说明" />
      <el-table-column prop="status" label="状态" width="100" />
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <template v-if="row.status === 'pending'">
            <el-button link type="primary" @click="resolve(row, true)">{{ approveLabel }}</el-button>
            <el-button link type="danger" @click="resolve(row, false)">{{ rejectLabel }}</el-button>
          </template>
          <span v-else class="muted">{{ row.adminRemark || '—' }}</span>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'
import { getSchema } from '../../utils/domainSchema'

const labels = computed(() => getSchema()?.labels || {})
const title = computed(() => labels.value.tbAppealAdminTitle || '申诉处理')
const approveLabel = computed(() => labels.value.tbAppealApproveLabel || '通过')
const rejectLabel = computed(() => labels.value.tbAppealRejectLabel || '驳回')
const list = ref([])

async function load() {
  const res = await http.get('/api/timebank/admin/appeals', { params: { page: 1, size: 50 } })
  const data = res.data?.data || res.data || {}
  list.value = data.list || []
}

async function resolve(row, pass) {
  const { value } = await ElMessageBox.prompt('处理说明（可选）', pass ? approveLabel.value : rejectLabel.value, {
    inputPlaceholder: '可选',
    confirmButtonText: '确定',
    cancelButtonText: '取消',
  }).catch(() => ({ value: null }))
  if (value === null) return
  await http.post(`/api/timebank/admin/appeals/${row.id}/resolve`, {
    pass,
    adminRemark: value || '',
  })
  ElMessage.success('已处理')
  await load()
}

onMounted(load)
</script>

<style scoped>
.muted { color: var(--el-text-color-secondary); }
</style>
