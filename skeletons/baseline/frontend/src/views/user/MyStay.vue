<template>
  <div>
    <p class="hint">每天的记录和照片都在这里。</p>
    <el-table :data="list" stripe>
      <el-table-column prop="dayKey" label="日期" width="120" />
      <el-table-column prop="note" label="记录" min-width="180" />
      <el-table-column label="照片" min-width="140">
        <template #default="{ row }">
          <a v-if="row.photoUrl" class="link" :href="row.photoUrl" target="_blank" rel="noopener noreferrer">查看</a>
          <span v-else>无</span>
        </template>
      </el-table-column>
    </el-table>
    <p v-if="!list.length" class="empty">还没有每日记录。</p>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import http from '../../api/http'

const list = ref([])

async function load() {
  const res = await http.get('/api/boarding/mine')
  list.value = res.data || []
}

onMounted(load)
</script>

<style scoped>
.hint, .empty { color: var(--el-text-color-secondary); margin: 0 0 12px; }
.link { color: var(--el-color-primary); }
</style>
