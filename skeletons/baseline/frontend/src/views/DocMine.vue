<template>
  <div>
    <section class="hero">
      <h1>{{ title }}</h1>
    </section>
    <el-table :data="list" stripe>
      <el-table-column prop="title" label="资料" min-width="180" />
      <el-table-column prop="downloadedAt" label="下载时间" min-width="160" />
    </el-table>
    <div v-if="!list.length" class="empty">暂无下载记录。</div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import http from '../utils/http'
import { getSchema } from '../utils/domainSchema'

const list = ref([])
const title = computed(() => (getSchema().labels || {}).docMineTitle || '我的下载')

async function load() {
  const res = await http.get('/api/doclib/mine', { params: { page: 1, size: 50 } })
  list.value = (res.data?.data || res.data || {}).list || []
}
onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 1rem; }
.empty { margin-top: 1rem; color: var(--el-text-color-secondary); }
</style>
