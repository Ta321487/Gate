<template>
  <div>
    <section class="hero">
      <h1>{{ title }}</h1>
      <p>{{ lead }}</p>
    </section>
    <div class="list">
      <article v-for="c in list" :key="c.id" class="card item">
        <div>
          <strong>{{ c.title }}</strong>
          <div class="muted">{{ c.author || '—' }} · 每人限 {{ c.maxVotes || 1 }} 票</div>
        </div>
        <el-button type="primary" @click="$router.push(`/vote/cast/${c.id}`)">去投票</el-button>
      </article>
    </div>
    <div v-if="!list.length" class="empty">暂无开放评选。</div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import http from '../utils/http'
import { getSchema } from '../utils/domainSchema'

const list = ref([])
const labels = computed(() => getSchema().labels || {})
const title = computed(() => labels.value.voteCampaignsTitle || '参与投票')
const lead = computed(
  () => labels.value.voteCampaignsLead || '选择开放中的评选活动，按限票数投给候选人。',
)

async function load() {
  const res = await http.get('/api/vote/campaigns')
  list.value = res.data?.data || res.data || []
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
