<template>
  <div>
    <section class="hero">
      <div class="hero-row">
        <div>
          <h1>{{ pageTitle }}</h1>
          <p>{{ pageLead }}</p>
          <p v-if="resultHint" class="muted">{{ resultHint }}</p>
        </div>
        <div class="tools">
          <el-button @click="load">刷新</el-button>
        </div>
      </div>
    </section>

    <div class="list">
      <article v-for="row in list" :key="row.id" class="card">
        <div class="mark">互</div>
        <div class="meta">
          <h3>编号 {{ row.id }}</h3>
          <p class="sub">
            学生 {{ row.username || '—' }}
            <span v-if="row.applyAt"> · {{ row.applyAt }}</span>
          </p>
          <el-tag size="small" type="success" effect="plain">已互选</el-tag>
        </div>
      </article>
      <el-empty v-if="!list.length" :description="emptyText" />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import http from '../../api/http'
import { getSchema } from '../../utils/domainSchema'

const labels = computed(() => getSchema()?.labels || {})
const pageTitle = computed(() => labels.value.mutualResultTitle || '互选结果公示')
const pageLead = computed(() => labels.value.mutualResultLead || '已确认互选的名单（脱敏展示）。')
const resultHint = computed(() => labels.value.mutualResultHint || '')
const emptyText = computed(() => labels.value.mutualResultEmpty || '暂无已公示的互选结果')

const list = ref([])

async function load() {
  const res = await http.get('/api/tickets/mutual-match-result')
  const data = res.data || res
  list.value = Array.isArray(data) ? data : data.list || []
}

onMounted(load)
</script>

<style scoped>
.hero {
  margin-bottom: 16px;
}
.hero-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}
.muted {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
.list {
  display: grid;
  gap: 12px;
}
.card {
  display: flex;
  gap: 12px;
  padding: 14px 16px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  background: var(--el-bg-color);
}
.mark {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  background: var(--el-color-success-light-9);
  color: var(--el-color-success);
  font-weight: 600;
}
.meta h3 {
  margin: 0 0 4px;
  font-size: 16px;
}
.sub {
  margin: 0 0 8px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
</style>
