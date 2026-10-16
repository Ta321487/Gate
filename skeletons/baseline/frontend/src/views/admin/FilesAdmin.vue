<template>
  <div class="card">
    <h2>{{ title }}</h2>
    <el-table :data="rows" stripe empty-text="还没有上传文件">
      <el-table-column prop="name" label="文件名" min-width="220" />
      <el-table-column label="大小" width="120">
        <template #default="{ row }">{{ formatSize(row.size) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="140">
        <template #default="{ row }">
          <el-button link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'
import { getSchema } from '../../utils/domainSchema.js'

const title = computed(() => getSchema()?.labels?.filesMenu || '文件')
const rows = ref([])

function formatSize(n) {
  const v = Number(n) || 0
  if (v < 1024) return `${v} B`
  if (v < 1024 * 1024) return `${(v / 1024).toFixed(1)} KB`
  return `${(v / 1024 / 1024).toFixed(1)} MB`
}

async function load() {
  const res = await http.get('/api/admin/uploads')
  rows.value = res.data || []
}

async function remove(row) {
  await ElMessageBox.confirm(`删除文件「${row.name}」？`, '删除文件')
  const extra = getSchema()?.uxCrosscut?.confirm ? { confirm: true } : {}
  await http.delete('/api/admin/uploads', { params: { name: row.name, ...extra } })
  ElMessage.success('已删除')
  load()
}

onMounted(load)
</script>
