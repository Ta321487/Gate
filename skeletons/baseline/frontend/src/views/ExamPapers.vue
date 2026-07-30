<template>
  <div>
    <section class="hero">
      <h1>{{ pageTitle }}</h1>
      <p>{{ pageLead }}</p>
    </section>
    <div class="list">
      <article v-for="p in list" :key="p.id" class="card item">
        <div class="meta">
          <strong>{{ p.title }}</strong>
          <span v-if="p.durationMin">限时 {{ p.durationMin }} 分钟</span>
        </div>
        <div class="actions">
          <el-button type="primary" @click="start(p.id, 'exam')">开始考试</el-button>
        </div>
      </article>
    </div>
    <div v-if="!list.length" class="empty">暂无已发布试卷。</div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import http from '../api/http'
import { getSchema } from '../utils/domainSchema'

const router = useRouter()
const list = ref([])
const labels = computed(() => getSchema().labels || {})
const pageTitle = computed(() => labels.value.examPapersTitle || '在线考试')
const pageLead = computed(
  () => labels.value.examPapersLead || '选择已发布试卷开考；提交后自动判分。',
)

async function load() {
  const res = await http.get('/api/exam/papers')
  list.value = res.data?.data || res.data || []
}

async function start(paperId, mode) {
  try {
    const res = await http.post(`/api/exam/papers/${paperId}/start`, { mode })
    const attempt = res.data?.data || res.data
    router.push(`/exam/take/${attempt.id}`)
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '无法开考')
  }
}

onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 1.25rem; }
.hero h1 { margin: 0 0 0.35rem; font-size: 1.5rem; }
.hero p { margin: 0; color: var(--el-text-color-secondary); }
.list { display: grid; gap: 0.75rem; }
.item { padding: 1rem 1.1rem; }
.meta { display: flex; gap: 1rem; align-items: baseline; margin-bottom: 0.75rem; }
.actions { display: flex; gap: 0.5rem; }
.empty { color: var(--el-text-color-secondary); padding: 2rem 0; }
</style>
