<template>
  <div>
    <section class="hero">
      <h1>{{ title }}</h1>
      <el-select v-model="paperId" placeholder="选择试卷" style="width: 240px" @change="load">
        <el-option v-for="p in papers" :key="p.id" :label="p.title" :value="p.id" />
      </el-select>
    </section>
    <el-table :data="list" stripe>
      <el-table-column type="index" label="#" width="60" />
      <el-table-column prop="username" label="考生" />
      <el-table-column prop="score" label="得分" width="100" />
      <el-table-column prop="submittedAt" label="交卷时间" />
    </el-table>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import http from '../api/http'
import { getSchema } from '../utils/domainSchema'

const papers = ref([])
const paperId = ref(null)
const list = ref([])
const title = computed(() => (getSchema().labels || {}).examRankTitle || '成绩排行')

async function loadPapers() {
  const res = await http.get('/api/exam/papers')
  papers.value = res.data?.data || res.data || []
  if (papers.value.length && !paperId.value) {
    paperId.value = papers.value[0].id
    await load()
  }
}

async function load() {
  if (!paperId.value) return
  const res = await http.get(`/api/exam/papers/${paperId.value}/rank`, { params: { page: 1, size: 50 } })
  const data = res.data?.data || res.data || {}
  list.value = data.list || []
}

onMounted(loadPapers)
</script>

<style scoped>
.hero { margin-bottom: 1rem; display: grid; gap: 0.75rem; }
</style>
