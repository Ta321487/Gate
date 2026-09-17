<template>
  <div>
    <p class="lead">管理档案条下的用户评论（≠ 门户留言）。</p>
    <div class="toolbar">
      <el-input
        v-model="itemIdFilter"
        clearable
        placeholder="按内容编号筛选"
        style="width: 200px"
        @keyup.enter="load"
      />
      <el-button type="primary" @click="load">查询</el-button>
    </div>
    <div class="table-scroll">
      <el-table :data="list" stripe>
        <el-table-column prop="itemId" label="内容编号" width="110" />
        <el-table-column prop="nickname" label="用户" width="140">
          <template #default="{ row }">{{ row.nickname || row.username || '—' }}</template>
        </el-table-column>
        <el-table-column prop="body" label="评论" min-width="220" show-overflow-tooltip />
        <el-table-column prop="createdAt" label="时间" width="170" />
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button link type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
    <div class="pager">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="size"
        background
        layout="total, sizes, prev, pager, next"
        :page-sizes="[10, 20, 50]"
        :total="total"
        @current-change="load"
        @size-change="load"
      />
    </div>
  </div>
</template>

<script setup>
/** 条下评论管理：删除不当评论 */
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'

const list = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const itemIdFilter = ref('')

async function load() {
  const params = { page: page.value, size: size.value }
  const raw = String(itemIdFilter.value || '').trim()
  if (raw) {
    const n = Number(raw)
    if (Number.isFinite(n) && n > 0) params.itemId = n
  }
  try {
    const res = await http.get('/api/item-comments', { params })
    list.value = res.data?.list || []
    total.value = res.data?.total || 0
  } catch {
    list.value = []
    total.value = 0
  }
}

async function remove(row) {
  try {
    await ElMessageBox.confirm('确定删除该评论？', '提示', { type: 'warning' })
    await http.delete(`/api/item-comments/${row.id}`)
    ElMessage.success('已删除')
    load()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e?.response?.data?.message || '删除失败')
  }
}

onMounted(load)
</script>

<style scoped>
.lead { margin: 0 0 12px; color: var(--el-text-color-secondary); font-size: 14px; }
.toolbar { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
.pager { margin-top: 12px; display: flex; justify-content: flex-end; }
.table-scroll { overflow-x: auto; }
</style>
