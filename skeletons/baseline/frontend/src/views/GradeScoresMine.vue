<template>
  <div>
    <section class="hero">
      <h1>成绩查询</h1>
      <p>已登记的课程分数与课内名次。并列时分数相同则名次相同。</p>
    </section>
    <el-table :data="list" stripe>
      <el-table-column prop="termName" label="学期" />
      <el-table-column prop="courseTitle" label="课程" />
      <el-table-column prop="score" label="分数" width="100" />
      <el-table-column prop="rankNo" label="课内名次" width="110" />
    </el-table>
    <p v-if="!list.length" class="empty">还没有已登记的成绩。</p>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import http from '../api/http'

const list = ref([])

async function load() {
  const res = await http.get('/api/grade-scores/mine')
  list.value = res.data?.data || res.data || []
}

onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 1rem; }
.hero h1 { margin: 0 0 0.35rem; font-size: 1.5rem; }
.hero p { margin: 0; color: var(--el-text-color-secondary); }
.empty { color: var(--el-text-color-secondary); padding: 2rem 0; }
</style>
