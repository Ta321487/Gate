<template>
  <div>
    <section class="hero">
      <h1>{{ pageTitle }}</h1>
      <p>{{ pageLead }}</p>
    </section>
    <div class="list">
      <article v-for="p in list" :key="p.id" class="card item">
        <strong>{{ p.title }}</strong>
        <el-button type="primary" @click="start(p.id)">开始练习</el-button>
      </article>
    </div>
    <div v-if="!list.length" class="empty">暂无试卷。</div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import http from '../utils/http'
import { getSchema } from '../utils/domainSchema'

const router = useRouter()
const list = ref([])
const labels = computed(() => getSchema().labels || {})
const pageTitle = computed(() => labels.value.examPracticeTitle || '刷题练习')
const pageLead = computed(
  () => labels.value.examPracticeLead || '练习模式不计排行；可反复作答。',
)

async function load() {
  const res = await http.get('/api/exam/papers')
  list.value = res.data?.data || res.data || []
}

async function start(paperId) {
  try {
    const res = await http.post(`/api/exam/papers/${paperId}/start`, { mode: 'practice' })
    const attempt = res.data?.data || res.data
    router.push(`/exam/take/${attempt.id}`)
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '无法开始练习')
  }
}

onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 1rem; }
.list { display: grid; gap: 0.75rem; }
.item { padding: 1rem; display: flex; justify-content: space-between; align-items: center; }
.empty { color: var(--el-text-color-secondary); }
</style>
