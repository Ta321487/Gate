<template>
  <div>
    <section class="hero">
      <h1>{{ title }}</h1>
    </section>
    <el-table :data="list" stripe>
      <el-table-column prop="campaignTitle" label="评选活动" min-width="160" />
      <el-table-column prop="candidateName" label="候选人" min-width="120" />
      <el-table-column prop="createdAt" label="投票时间" min-width="160" />
    </el-table>
    <div v-if="!list.length" class="empty">暂无选票记录。</div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import http from '../utils/http'
import { getSchema } from '../utils/domainSchema'

const list = ref([])
const title = computed(() => (getSchema().labels || {}).voteMineTitle || '我的选票')

async function load() {
  const res = await http.get('/api/vote/ballots/mine', { params: { page: 1, size: 50 } })
  const data = res.data?.data || res.data || {}
  list.value = data.list || []
}
onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 1rem; }
.empty { margin-top: 1rem; color: var(--el-text-color-secondary); }
</style>
