<template>
  <div>
    <section class="hero">
      <h1>{{ title }}</h1>
    </section>
    <el-table :data="list" stripe>
      <el-table-column prop="paperId" label="试卷" width="90" />
      <el-table-column prop="mode" label="模式" width="90" />
      <el-table-column prop="status" label="状态" width="100" />
      <el-table-column label="得分" width="120">
        <template #default="{ row }">{{ row.score }} / {{ row.totalScore }}</template>
      </el-table-column>
      <el-table-column prop="submittedAt" label="交卷时间" />
    </el-table>
    <el-pagination
      class="pager"
      v-model:current-page="page"
      v-model:page-size="size"
      layout="total, prev, pager, next"
      :total="total"
      @current-change="load"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import http from '../api/http'
import { getSchema } from '../utils/domainSchema'

const list = ref([])
const page = ref(1)
const size = ref(10)
const total = ref(0)
const title = computed(() => (getSchema().labels || {}).examAttemptsTitle || '我的成绩')

async function load() {
  const res = await http.get('/api/exam/attempts/mine', { params: { page: page.value, size: size.value } })
  const data = res.data?.data || res.data || {}
  list.value = data.list || []
  total.value = data.total || 0
}

onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 1rem; }
.pager { margin-top: 1rem; }
</style>
