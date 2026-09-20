<template>
  <div>
    <p class="hint">这里是已经扣过的课时。</p>
    <el-button @click="load">刷新</el-button>
    <el-table :data="list" stripe>
      <el-table-column prop="username" label="会员" width="120" />
      <el-table-column prop="reservationId" label="预约" width="100" />
      <el-table-column prop="createdAt" label="时间" min-width="160" />
    </el-table>
    <p v-if="!list.length" class="empty">还没有消课记录。</p>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import http from '../../api/http'

const list = ref([])

async function load() {
  const res = await http.get('/api/lessons/uses')
  list.value = res.data || []
}

onMounted(load)
</script>

<style scoped>
.hint, .empty { color: var(--el-text-color-secondary); margin: 0 0 12px; }
</style>
