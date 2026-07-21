<template>
  <div>
    <section class="hero">
      <h1>{{ label }}</h1>
      <p>查看{{ orderNoun }}状态与明细。</p>
      <el-select v-model="status" clearable placeholder="全部状态" style="width:140px" @change="load">
        <el-option v-for="(lab, key) in states" :key="key" :label="lab" :value="key" />
      </el-select>
    </section>

    <article v-for="row in list" :key="row.id" class="card">
      <div class="hd">
        <strong>{{ orderNoun }} #{{ row.id }}</strong>
        <el-tag size="small" effect="plain">{{ states[row.status] || row.status }}</el-tag>
      </div>
      <p class="sub">
        {{ row.createdAt }} · 合计 ¥{{ row.totalYuan }}
        <template v-if="Number(row.discountYuan) > 0"> · 优惠 ¥{{ row.discountYuan }}</template>
        <template v-if="row.couponCode"> · 券 {{ row.couponCode }}</template>
        <template v-if="Number(row.pointsEarned) > 0"> · 获积分 {{ row.pointsEarned }}</template>
      </p>
      <p v-if="row.refundStatus" class="sub refund">
        售后：{{ refundLabel(row.refundStatus) }}
        <template v-if="row.refundReason"> · {{ row.refundReason }}</template>
      </p>
      <p v-if="hasShipInfo(row)" class="ship">
        <template v-if="row.deliveryType">{{ row.deliveryType }} · </template>
        <template v-if="row.receiverName || row.receiverPhone">
          {{ row.receiverName }} {{ row.receiverPhone }}
        </template>
        <template v-if="row.addressLine"> · {{ row.addressLine }}</template>
        <template v-if="isFood && row.tasteNote"><br />口味：{{ row.tasteNote }}</template>
        <template v-if="!isFood && row.trackingNo"><br />物流单号：{{ row.trackingNo }}</template>
        <template v-if="isFood && row.pickupCode"><br />取餐码：{{ row.pickupCode }}</template>
        <template v-if="row.remark"><br />备注：{{ row.remark }}</template>
      </p>
      <ul class="lines">
        <li v-for="ln in row.lines || []" :key="ln.id">{{ ln.title }} × {{ ln.qty }}（¥{{ ln.lineYuan }}）</li>
      </ul>
      <div class="acts">
        <el-button size="small" @click="openTrace(row)">物流轨迹</el-button>
        <el-button
          v-if="canRefund(row)"
          size="small"
          type="warning"
          @click="requestRefund(row)"
        >申请售后</el-button>
        <el-button
          v-if="canReview(row)"
          size="small"
          type="primary"
          @click="submitReview(row)"
        >评价</el-button>
        <el-button
          v-if="row.status === 'pending' || row.status === 'confirmed'"
          size="small"
          @click="cancel(row)"
        >取消</el-button>
      </div>
    </article>
    <div v-if="!list.length" class="empty">暂无{{ orderNoun }}</div>
    <div class="pager">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="size"
        background
        layout="total, prev, pager, next"
        :total="total"
        @current-change="load"
      />
    </div>

    <OrderTraceDialog v-model="traceVisible" :order-id="traceOrderId" />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'
import OrderTraceDialog from '../../components/OrderTraceDialog.vue'
import { hasCap, hasTrait, getSchema, menuLabel } from '../../utils/domainSchema.js'

const label = menuLabel('user', 'my_orders', '我的订单')
const orderNoun = computed(() => getSchema()?.entities?.order?.label || '订单')
const states = computed(() => getSchema()?.entities?.order?.states || {})
const isFood = computed(() => hasTrait('food'))
const reviewOn = computed(() => hasCap('order_review'))
const list = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const status = ref(null)
const traceVisible = ref(false)
const traceOrderId = ref(null)
const reviewedIds = ref(new Set())

function refundLabel(st) {
  return ({ pending: '待审核', approved: '已通过', rejected: '已驳回' }[st] || st)
}

function hasShipInfo(row) {
  if (!row) return false
  if (row.deliveryType || row.addressLine || row.receiverName || row.receiverPhone || row.remark) return true
  if (isFood.value) return !!(row.tasteNote || row.pickupCode)
  return !!row.trackingNo
}

function canRefund(row) {
  if (!row) return false
  if (!['shipped', 'completed'].includes(row.status)) return false
  const rs = row.refundStatus || ''
  return !rs || rs === 'rejected'
}

function canReview(row) {
  if (!reviewOn.value || !row || row.status !== 'completed') return false
  return !reviewedIds.value.has(row.id)
}

async function loadReviewsHint(orders) {
  if (!reviewOn.value) {
    reviewedIds.value = new Set()
    return
  }
  const done = new Set()
  await Promise.all(
    (orders || [])
      .filter((o) => o.status === 'completed')
      .map(async (o) => {
        try {
          const res = await http.get(`/api/order-reviews/by-order/${o.id}`)
          if (res.data?.id) done.add(o.id)
        } catch { /* ignore */ }
      }),
  )
  reviewedIds.value = done
}

async function load() {
  const res = await http.get('/api/orders', {
    params: { page: page.value, size: size.value, status: status.value || undefined },
  })
  list.value = res.data?.list || []
  total.value = res.data?.total || 0
  await loadReviewsHint(list.value)
}

async function cancel(row) {
  await ElMessageBox.confirm(`取消${orderNoun.value} #${row.id}？`, '取消')
  await http.post(`/api/orders/${row.id}/cancel`)
  ElMessage.success('已取消')
  load()
}

function openTrace(row) {
  traceOrderId.value = row.id
  traceVisible.value = true
}

async function requestRefund(row) {
  const { value } = await ElMessageBox.prompt('请填写售后原因', '申请售后', {
    inputPlaceholder: '如：商品破损、少件、口味不符…',
    inputValidator: (v) => (String(v || '').trim() ? true : '请填写原因'),
  }).catch(() => ({ value: null }))
  if (value == null) return
  await http.post(`/api/orders/${row.id}/refund`, { reason: String(value).trim() })
  ElMessage.success('已提交售后申请')
  load()
}

async function submitReview(row) {
  const { value: rating } = await ElMessageBox.prompt('请输入评分 1～5', '订单评价', {
    inputValue: '5',
    inputPattern: /^[1-5]$/,
    inputErrorMessage: '请输入 1～5',
  }).catch(() => ({ value: null }))
  if (rating == null) return
  const { value: body } = await ElMessageBox.prompt('评价内容（选填）', '订单评价', {
    inputPlaceholder: '口味、包装、配送体验…',
    inputValue: '',
  }).catch(() => ({ value: null }))
  if (body == null) return
  await http.post('/api/order-reviews', {
    orderId: row.id,
    rating: Number(rating),
    body: String(body || '').trim(),
  })
  ElMessage.success('评价已提交')
  load()
}

onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 16px; }
.hero h1 { margin: 0 0 6px; font-size: 22px; }
.hero p { margin: 0 0 10px; color: #64748b; font-size: 13px; }
.card {
  background: var(--portal-surface, #fff);
  border: var(--portal-border-width, 1px) solid var(--portal-line, #e2e8f0);
  border-radius: var(--portal-radius, 12px);
  box-shadow: var(--portal-shadow, none);
  padding: var(--portal-pad, 14px) 16px;
  margin-bottom: var(--portal-gap, 12px);
}
.hd { display: flex; justify-content: space-between; gap: 8px; align-items: center; }
.sub { margin: 6px 0; color: #64748b; font-size: 12px; }
.sub.refund { color: #b45309; }
.ship { margin: 0 0 8px; color: #475569; font-size: 12px; line-height: 1.5; }
.lines { margin: 0; padding-left: 18px; color: #334155; font-size: 13px; }
.acts { margin-top: 10px; display: flex; flex-wrap: wrap; gap: 6px; }
.empty { text-align: center; color: #94a3b8; padding: 40px 0; }
.pager { margin-top: 16px; display: flex; justify-content: flex-end; }
</style>
