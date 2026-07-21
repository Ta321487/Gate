<template>
  <div>
    <section class="hero">
      <h1>{{ pageTitle }}</h1>
      <p>{{ pageLead }}</p>
    </section>

    <el-tabs v-model="tab" @tab-change="onTab">
      <el-tab-pane label="可领取" name="claim" />
      <el-tab-pane label="我的券" name="mine" />
    </el-tabs>

    <template v-if="tab === 'claim'">
      <article v-for="row in templates" :key="row.id" class="card">
        <div class="hd">
          <strong>{{ row.label || row.code }}</strong>
          <el-tag size="small" effect="plain">{{ row.code }}</el-tag>
        </div>
        <p class="sub">
          满 ¥{{ Number(row.minYuan || 0).toFixed(0) }} 减 ¥{{ Number(row.offYuan || 0).toFixed(0) }}
          <template v-if="row.expireAt"> · 至 {{ row.expireAt }}</template>
          <template v-if="Number(row.totalQuota) > 0">
            · 余 {{ Math.max(0, Number(row.totalQuota) - Number(row.claimed || 0)) }} 张
          </template>
        </p>
        <el-button size="small" type="primary" @click="claim(row)">领取</el-button>
      </article>
      <div v-if="!templates.length" class="empty">暂无可领券</div>
    </template>

    <template v-else>
      <el-radio-group v-model="status" size="small" class="filter" @change="loadMine">
        <el-radio-button label="">全部</el-radio-button>
        <el-radio-button label="unused">未使用</el-radio-button>
        <el-radio-button label="used">已使用</el-radio-button>
        <el-radio-button label="expired">已过期</el-radio-button>
      </el-radio-group>
      <article v-for="row in list" :key="row.id" class="card">
        <div class="hd">
          <strong>{{ row.label || row.code }}</strong>
          <el-tag size="small" effect="plain">{{ statusLabel(row.status) }}</el-tag>
        </div>
        <p class="sub">
          {{ row.code }} · 满 ¥{{ Number(row.minYuan || 0).toFixed(0) }} 减 ¥{{ Number(row.offYuan || 0).toFixed(0) }}
          <template v-if="row.expireAt"> · 至 {{ row.expireAt }}</template>
        </p>
        <p v-if="row.usedAt" class="sub">使用于 {{ row.usedAt }}<template v-if="row.orderId"> · 订单 #{{ row.orderId }}</template></p>
      </article>
      <div v-if="!list.length" class="empty">暂无优惠券</div>
      <div class="pager">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="size"
          background
          layout="total, prev, pager, next"
          :total="total"
          @current-change="loadMine"
        />
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/http'
import { schemaLabels } from '../../utils/domainSchema.js'

const labels = computed(() => schemaLabels())
const pageTitle = computed(() => labels.value.couponsPageTitle || '优惠券')
const pageLead = computed(
  () => labels.value.couponsPageLead || '领取可用券，下单时选用券码抵扣。',
)

const tab = ref('claim')
const templates = ref([])
const list = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const status = ref('')

function statusLabel(st) {
  return ({ unused: '未使用', used: '已使用', expired: '已过期' }[st] || st)
}

async function loadTemplates() {
  const res = await http.get('/api/coupons/templates')
  templates.value = res.data || []
}

async function loadMine() {
  const res = await http.get('/api/coupons/mine', {
    params: {
      page: page.value,
      size: size.value,
      status: status.value || undefined,
    },
  })
  list.value = res.data?.list || []
  total.value = res.data?.total || 0
}

function onTab() {
  if (tab.value === 'claim') loadTemplates()
  else loadMine()
}

async function claim(row) {
  await http.post(`/api/coupons/${row.id}/claim`)
  ElMessage.success(`已领取 ${row.code}`)
  loadTemplates()
}

onMounted(() => {
  loadTemplates()
})
</script>

<style scoped>
.hero { margin-bottom: 12px; }
.hero h1 { margin: 0 0 6px; font-size: 22px; }
.hero p { margin: 0; color: #64748b; font-size: 13px; }
.filter { margin-bottom: 12px; }
.card {
  background: var(--portal-surface, #fff);
  border: var(--portal-border-width, 1px) solid var(--portal-line, #e2e8f0);
  border-radius: var(--portal-radius, 12px);
  box-shadow: var(--portal-shadow, none);
  padding: var(--portal-pad, 14px) 16px;
  margin-bottom: var(--portal-gap, 12px);
}
.hd { display: flex; justify-content: space-between; gap: 8px; align-items: center; }
.sub { margin: 6px 0 10px; color: #64748b; font-size: 12px; }
.empty { text-align: center; color: #94a3b8; padding: 40px 0; }
.pager { margin-top: 16px; display: flex; justify-content: flex-end; }
</style>
