<template>
  <div>
    <p class="hint">交片后才能查看文件。</p>
    <el-table :data="list" stripe>
      <el-table-column prop="reservationId" label="预约" width="90" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">{{ Number(row.delivered) === 1 ? '已交片' : '未交片' }}</template>
      </el-table-column>
      <el-table-column label="文件" min-width="180">
        <template #default="{ row }">
          <a v-if="row.fileUrl" class="link" :href="row.fileUrl" target="_blank" rel="noopener noreferrer">查看</a>
          <span v-else>尚未交片</span>
        </template>
      </el-table-column>
    </el-table>
    <p v-if="!list.length" class="empty">还没有成片。</p>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import http from '../../api/http'

const list = ref([])

async function load() {
  const res = await http.get('/api/shoot/mine')
  list.value = res.data || []
}

onMounted(load)
</script>

<style scoped>
.hint, .empty { color: var(--el-text-color-secondary); margin: 0 0 12px; }
.link { color: var(--el-color-primary); }
</style>
