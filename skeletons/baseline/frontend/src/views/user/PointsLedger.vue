<template>
  <div>
    <section class="hero">
      <h1>{{ pageTitle }}</h1>
      <p>{{ pageLead }}</p>
      <p v-if="freightHint" class="tip muted">{{ freightHint }}</p>
      <el-button @click="load">刷新</el-button>
    </section>
    <article v-for="(row, idx) in list" :key="idx" class="card">
      <div class="hd">
        <strong>{{ row.reason || row.kind || '积分变动' }}</strong>
        <span :class="Number(row.delta) >= 0 ? 'plus' : 'minus'">
          {{ Number(row.delta) >= 0 ? '+' : '' }}{{ row.delta }}
        </span>
      </div>
      <p class="sub">余额 {{ row.balanceAfter ?? row.pointsAfter ?? '—' }}
        <template v-if="row.createdAt"> · {{ row.createdAt }}</template>
      </p>
    </article>
    <EmptyHint v-if="!list.length" :title="emptyTitle" desc="积分变动后会出现在这里。" mark="分" />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import http from '../../api/http'
import EmptyHint from '../../components/EmptyHint.vue'
import { schemaLabels } from '../../utils/domainSchema.js'

const labels = computed(() => schemaLabels())
const pageTitle = computed(() => labels.value.pointsLedgerPageTitle || '积分明细')
const pageLead = computed(() => labels.value.pointsLedgerPageLead || '查看积分增减流水。')
const emptyTitle = computed(() => labels.value.pointsLedgerEmpty || '暂无积分流水')
const freightHint = computed(() => labels.value.pointsFreightHint || '')
const list = ref([])

async function load() {
  const res = await http.get('/api/loyalty/ledger', { params: { limit: 50 } })
  list.value = Array.isArray(res.data) ? res.data : (res.data?.list || [])
}

onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 16px; display: flex; flex-wrap: wrap; justify-content: space-between; gap: 8px; }
.hero h1 { margin: 0 0 6px; font-size: 22px; width: 100%; }
.hero p { margin: 0; color: var(--portal-muted, #64748b); font-size: 13px; width: 100%; }
.tip { margin-top: 6px !important; }
.card {
  background: var(--portal-surface, #fff);
  border: var(--portal-border-width, 1px) solid var(--portal-line, #e2e8f0);
  border-radius: var(--portal-radius, 12px);
  padding: var(--portal-pad, 14px) 16px;
  margin-bottom: var(--portal-gap, 12px);
}
.hd { display: flex; justify-content: space-between; gap: 8px; align-items: center; }
.plus { color: #0b6e75; font-weight: 600; }
.minus { color: #b45309; font-weight: 600; }
.sub { margin: 6px 0 0; color: var(--portal-muted, #94a3b8); font-size: 12px; }
</style>
