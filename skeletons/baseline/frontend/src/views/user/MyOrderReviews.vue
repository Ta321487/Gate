<template>
  <div>
    <section class="hero">
      <h1>{{ pageTitle }}</h1>
      <p>{{ pageLead }}</p>
      <el-button @click="load">刷新</el-button>
    </section>

    <article v-for="row in list" :key="row.id" class="card">
      <div class="hd">
        <strong>订单 #{{ row.orderId }}</strong>
        <el-rate :model-value="row.rating" disabled />
      </div>
      <p class="body">{{ row.body || '（无文字）' }}</p>
      <p class="sub" :title="row.createdAt || ''">{{ formatRelative(row.createdAt) }}</p>
      <div v-if="row.reply" class="reply-bubble">
        <span class="reply-tag">商家回复</span>
        <p>{{ row.reply }}</p>
      </div>
    </article>
    <EmptyHint v-if="!list.length" title="暂无评价" desc="完成订单后可在此查看评价与商家回复。" mark="评" />
    <div class="pager">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="size"
        background
        layout="total, sizes, prev, pager, next"
        :page-sizes="[10, 20, 50]"
        :total="total"
        @current-change="load"
        @size-change="load"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import http from '../../api/http'
import EmptyHint from '../../components/EmptyHint.vue'
import { formatRelative } from '../../utils/dates.js'
import { schemaLabels } from '../../utils/domainSchema.js'

const labels = computed(() => schemaLabels())
const pageTitle = computed(() => labels.value.orderReviewPageTitle || '我的评价')
const pageLead = computed(
  () => labels.value.orderReviewPageLead || '对已完成订单进行星级与文字评价。',
)

const list = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)

async function load() {
  const res = await http.get('/api/order-reviews', {
    params: { page: page.value, size: size.value },
  })
  list.value = res.data?.list || []
  total.value = res.data?.total || 0
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
  box-shadow: var(--portal-shadow, none);
  padding: var(--portal-pad, 14px) 16px;
  margin-bottom: var(--portal-gap, 12px);
}
.hd { display: flex; justify-content: space-between; gap: 8px; align-items: center; }
.body { margin: 8px 0; color: var(--portal-ink, #334155); font-size: 14px; white-space: pre-wrap; }
.sub { margin: 0; color: var(--portal-muted, #94a3b8); font-size: 12px; }
.reply-bubble {
  margin: 10px 0 0;
  padding: 10px 12px;
  background: var(--portal-accent-soft, #d7eef0);
  border-left: 3px solid var(--portal-accent, #0b6e75);
  border-radius: 0 var(--portal-radius-sm, 8px) var(--portal-radius-sm, 8px) 0;
  color: var(--portal-ink, #15202b);
}
.reply-tag {
  display: inline-block;
  font-size: 12px;
  color: var(--portal-accent, #0b6e75);
  margin-bottom: 4px;
}
.reply-bubble p {
  margin: 0;
  white-space: pre-wrap;
  font-size: 13px;
  line-height: 1.55;
}
.pager { margin-top: 16px; display: flex; justify-content: flex-end; }
</style>
