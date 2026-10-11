<template>
  <div class="poster-page">
    <section class="hero no-print">
      <h1>{{ posterTitle }}</h1>
      <p class="muted">{{ campaign?.title || '' }} · {{ posterLead }}</p>
      <div class="actions">
        <el-button type="primary" @click="printPage">打印海报</el-button>
        <el-button @click="$router.push(`/vote/cast/${route.params.id}`)">返回投票</el-button>
      </div>
    </section>
    <p v-if="delayed" class="muted delay">{{ delayMsg }}</p>
    <div v-else class="poster card">
      <header class="poster-hd">
        <h2>{{ campaign?.title || posterTitle }}</h2>
        <p>{{ posterLead }}</p>
      </header>
      <ol class="rank">
        <li v-for="(r, idx) in top10" :key="r.id || idx" :class="{ top3: idx < 3 }">
          <span class="no">{{ idx + 1 }}</span>
          <el-avatar :size="44" :src="r.avatarUrl || undefined">
            {{ String(r.name || '?').slice(0, 1) }}
          </el-avatar>
          <div class="meta">
            <strong>{{ r.name }}</strong>
            <span class="muted">{{ r.intro || '' }}</span>
            <span v-if="r.slogan" class="slogan">{{ r.slogan }}</span>
          </div>
          <em>{{ r.votes }} 票</em>
        </li>
      </ol>
      <p v-if="!top10.length" class="muted">暂无计票数据。</p>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import http from '../api/http'
import { getSchema } from '../utils/domainSchema'

const route = useRoute()
const labels = computed(() => getSchema()?.labels || {})
const posterTitle = computed(() => labels.value.votePosterTitle || '十佳结果海报')
const posterLead = computed(() => labels.value.votePosterLead || '按得票展示前十名，可打印存档。')
const delayMsg = computed(() => labels.value.voteResultDelayMsg || '结果尚未到公布时间')

const campaign = ref(null)
const results = ref([])
const delayed = ref(false)
const top10 = computed(() => (results.value || []).slice(0, 10))

function printPage() {
  window.print()
}

async function load() {
  const id = route.params.id
  try {
    const c = await http.get(`/api/vote/campaigns/${id}`)
    campaign.value = c.data?.data || c.data
    if (campaign.value?.resultPublished === false) {
      delayed.value = true
      results.value = []
      return
    }
    const res = await http.get(`/api/vote/campaigns/${id}/results`)
    results.value = res.data?.data || res.data || []
    delayed.value = false
  } catch (e) {
    const msg = String(e?.response?.data?.message || e.message || '')
    if (/延迟|尚未|公布|未到/.test(msg) || campaign.value?.resultPublished === false) {
      delayed.value = true
      results.value = []
      return
    }
    ElMessage.error(msg || '加载失败')
  }
}

onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 1rem; }
.muted { color: var(--el-text-color-secondary); }
.actions { display: flex; gap: 0.5rem; margin-top: 0.75rem; }
.delay { margin: 1rem 0; }
.poster { padding: 1.25rem 1.5rem; }
.poster-hd { text-align: center; margin-bottom: 1rem; }
.poster-hd h2 { margin: 0 0 0.35rem; }
.rank { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.65rem; }
.rank li {
  display: grid;
  grid-template-columns: 2rem 44px 1fr auto;
  gap: 0.75rem;
  align-items: center;
  padding: 0.65rem 0.75rem;
  border-radius: 8px;
  border: 1px solid var(--el-border-color-lighter);
}
.rank li.top3 {
  background: color-mix(in srgb, var(--portal-accent-soft, #e8f2f2) 75%, transparent);
  border-color: transparent;
}
.no { font-weight: 700; text-align: center; }
.meta { display: grid; gap: 0.2rem; min-width: 0; }
.slogan { color: var(--portal-accent, var(--el-color-primary)); font-size: 0.9rem; }
.rank em { font-style: normal; font-weight: 700; white-space: nowrap; }

@media print {
  .no-print { display: none !important; }
  .poster { border: none; box-shadow: none; }
}
</style>
