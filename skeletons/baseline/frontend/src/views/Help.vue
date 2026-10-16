<template>
  <div class="card">
    <h2>{{ doc.title || '使用说明' }}</h2>
    <p class="lead">{{ lead }}</p>
    <pre class="body">{{ doc.body }}</pre>
  </div>
</template>

<script setup>
import { onMounted, ref, computed } from 'vue'
import http from '../api/http'
import { getSchema } from '../utils/domainSchema.js'

const doc = ref({ title: '', body: '' })
const lead = computed(() => getSchema()?.labels?.helpLead || '阅读本系统的操作说明。')

onMounted(async () => {
  const res = await http.get('/api/help')
  doc.value = res.data || {}
})
</script>

<style scoped>
.lead { color: var(--el-text-color-secondary); }
.body { white-space: pre-wrap; font-family: inherit; line-height: 1.7; }
</style>
