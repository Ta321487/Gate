<template>
  <div>
    <section class="hero">
      <h1>{{ title }}</h1>
      <p>{{ lead }}</p>
    </section>
    <div class="list">
      <article v-for="f in list" :key="f.id" class="card item">
        <strong>{{ f.title }}</strong>
        <span class="muted">{{ f.author || '—' }}</span>
        <el-button type="primary" @click="$router.push(`/survey/fill/${f.id}`)">去填写</el-button>
      </article>
    </div>
    <div v-if="!list.length" class="empty">暂无开放问卷。</div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import http from '../utils/http'
import { getSchema } from '../utils/domainSchema'

const list = ref([])
const labels = computed(() => getSchema().labels || {})
const title = computed(() => labels.value.surveyFormsTitle || '填写问卷')
const lead = computed(
  () => labels.value.surveyFormsLead || '选择已发布问卷填写提交；每人每卷限填一次。',
)

async function load() {
  const res = await http.get('/api/survey/forms')
  list.value = res.data?.data || res.data || []
}
onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 1rem; }
.list { display: grid; gap: 0.75rem; }
.item { padding: 1rem; display: flex; gap: 1rem; align-items: center; justify-content: space-between; flex-wrap: wrap; }
.muted { color: var(--el-text-color-secondary); }
.empty { color: var(--el-text-color-secondary); }
</style>
