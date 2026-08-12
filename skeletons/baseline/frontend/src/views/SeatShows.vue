<template>
  <div>
    <section class="hero">
      <h1>{{ title }}</h1>
      <p>{{ lead }}</p>
    </section>
    <div class="list">
      <article v-for="s in list" :key="s.id" class="card item">
        <div>
          <strong>{{ s.title }}</strong>
          <div class="muted">
            {{ s.isbn || '—' }}
            <template v-if="s.startAt"> · {{ s.startAt }}</template>
            · 票价 ¥{{ s.author || 0 }}
            · 座位 {{ s.seatRows || 6 }}×{{ s.seatCols || 8 }}
            · 余座 {{ s.stock }}
          </div>
        </div>
        <el-button type="primary" @click="go(s.id)">选座</el-button>
      </article>
    </div>
    <div v-if="!list.length" class="empty">暂无开放场次。</div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import http from '../api/http'
import { getSchema } from '../utils/domainSchema'

const router = useRouter()
const list = ref([])
const labels = computed(() => getSchema().labels || {})
const title = computed(() => labels.value.seatShowsTitle || '场次选座')
const lead = computed(
  () => labels.value.seatShowsLead || '选择场次后进入座位图；确认后生成订单并占座（无真锁座）。',
)

async function load() {
  const res = await http.get('/api/seats/shows')
  list.value = res.data?.data || res.data || []
}

function go(id) {
  router.push(`/seats/map/${id}`)
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
