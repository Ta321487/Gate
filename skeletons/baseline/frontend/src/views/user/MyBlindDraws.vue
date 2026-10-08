<template>
  <div>
    <section class="hero">
      <h1>{{ pageTitle }}</h1>
      <p>{{ pageLead }}</p>
      <el-button @click="load">刷新</el-button>
    </section>
    <article v-for="row in list" :key="`${row.orderId}-${row.drawTitle}`" class="card">
      <div class="hd">
        <strong>{{ row.drawTitle }}</strong>
        <el-tag v-if="row.hidden" size="small" type="warning" effect="plain">隐藏款</el-tag>
      </div>
      <p class="sub">{{ row.boxTitle || '盲盒' }} · 订单 #{{ row.orderId }}</p>
      <p class="sub" v-if="row.createdAt">{{ row.createdAt }}</p>
    </article>
    <EmptyHint v-if="!list.length" :title="emptyTitle" desc="抽盒后会出现在这里。" mark="赏" />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import http from '../../api/http'
import EmptyHint from '../../components/EmptyHint.vue'
import { getSchema, schemaLabels } from '../../utils/domainSchema.js'

const labels = computed(() => schemaLabels())
const pageTitle = computed(() => labels.value.blindDrawsPageTitle || '中赏记录')
const pageLead = computed(() => labels.value.blindDrawsPageLead || '查看已抽中的奖品记录。')
const emptyTitle = computed(() => labels.value.blindDrawsEmpty || '还没有抽中记录')
const list = ref([])

async function load() {
  if (!getSchema()?.tradeThicken?.blindDraws && !getSchema()?.capabilities?.includes?.('blind_box')) {
    list.value = []
    return
  }
  const res = await http.get('/api/blind-boxes/draws', { params: { limit: 50 } })
  list.value = Array.isArray(res.data) ? res.data : []
}

onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 16px; display: flex; flex-wrap: wrap; justify-content: space-between; gap: 8px; }
.hero h1 { margin: 0 0 6px; font-size: 22px; width: 100%; }
.hero p { margin: 0; color: var(--portal-muted, #64748b); font-size: 13px; width: 100%; }
.card {
  background: var(--portal-surface, #fff);
  border: var(--portal-border-width, 1px) solid var(--portal-line, #e2e8f0);
  border-radius: var(--portal-radius, 12px);
  padding: var(--portal-pad, 14px) 16px;
  margin-bottom: var(--portal-gap, 12px);
}
.hd { display: flex; justify-content: space-between; gap: 8px; align-items: center; }
.sub { margin: 6px 0 0; color: var(--portal-muted, #94a3b8); font-size: 12px; }
</style>
