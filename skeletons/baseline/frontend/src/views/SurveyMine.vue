<template>
  <div>
    <section class="hero"><h1>{{ title }}</h1></section>
    <el-table :data="list" stripe>
      <el-table-column prop="formTitle" label="问卷" />
      <el-table-column prop="submittedAt" label="提交时间" width="180" />
    </el-table>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import http from '../api/http'
import { getSchema } from '../utils/domainSchema'

const list = ref([])
const title = computed(() => (getSchema().labels || {}).surveyMineTitle || '我的答卷')

async function load() {
  const res = await http.get('/api/survey/responses/mine', { params: { page: 1, size: 50 } })
  list.value = (res.data?.data || res.data || {}).list || []
}
onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 1rem; }
</style>
