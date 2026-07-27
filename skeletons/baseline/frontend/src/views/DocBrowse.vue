<template>
  <div>
    <section class="hero">
      <h1>{{ title }}</h1>
      <p>{{ lead }}</p>
    </section>
    <div class="list">
      <article v-for="d in list" :key="d.id" class="card item">
        <div>
          <strong>{{ d.title }}</strong>
          <div class="muted">{{ d.author || '—' }} · 权限 {{ levelLabel(d.accessLevel) }}</div>
          <div class="muted">{{ d.isbn || '' }}</div>
        </div>
        <el-button type="primary" :loading="busyId === d.id" @click="dl(d)">下载</el-button>
      </article>
    </div>
    <div v-if="!list.length" class="empty">暂无开放资料。</div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../utils/http'
import { getSchema } from '../utils/domainSchema'

const list = ref([])
const busyId = ref(null)
const labels = computed(() => getSchema().labels || {})
const title = computed(() => labels.value.docBrowseTitle || '文库浏览')
const lead = computed(
  () => labels.value.docBrowseLead || '浏览开放资料，按权限下载；下载将记入台账。',
)

function levelLabel(lv) {
  if (lv === 'staff') return '管理人员'
  if (lv === 'public') return '开放'
  return '登录可下'
}

async function load() {
  const res = await http.get('/api/doclib/items')
  list.value = res.data?.data || res.data || []
}

async function dl(d) {
  busyId.value = d.id
  try {
    const res = await http.post(`/api/doclib/items/${d.id}/download`)
    const data = res.data?.data || res.data || {}
    ElMessage.success('已记入台账')
    if (data.url) window.open(data.url, '_blank')
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '下载失败')
  } finally {
    busyId.value = null
  }
}

onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 1rem; }
.list { display: grid; gap: 0.75rem; }
.item { padding: 1rem; display: flex; gap: 1rem; align-items: center; justify-content: space-between; flex-wrap: wrap; }
.muted { color: var(--el-text-color-secondary); font-size: 0.9rem; margin-top: 0.25rem; }
.empty { color: var(--el-text-color-secondary); }
</style>
