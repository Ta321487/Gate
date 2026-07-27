<template>
  <div>
    <section class="hero">
      <h1>下载台账</h1>
      <p class="muted">查看资料下载记录。</p>
    </section>
    <el-table :data="list" stripe>
      <el-table-column prop="title" label="资料" min-width="160" />
      <el-table-column prop="username" label="用户" width="120" />
      <el-table-column prop="downloadedAt" label="时间" min-width="160" />
    </el-table>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import http from '../../utils/http'

const list = ref([])

async function load() {
  const res = await http.get('/api/doclib/admin/logs', { params: { page: 1, size: 50 } })
  list.value = (res.data?.data || res.data || {}).list || []
}
onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 1rem; }
.muted { color: var(--el-text-color-secondary); }
</style>
