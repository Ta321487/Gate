<template>
  <div>
    <section class="hero">
      <h1>{{ label }}</h1>
      <p>查看{{ orderNoun }}状态与明细。</p>
      <el-select v-model="status" clearable placeholder="全部状态" style="width:140px" @change="load">
        <el-option
          v-for="opt in statusOptions"
          :key="opt.value"
          :label="opt.label"
          :value="opt.value"
        />
      </el-select>
    </section>

    <PageSkeleton v-if="loading" variant="list" :rows="4" />
    <template v-else>
    <article
      v-for="row in list"
      :key="row.id"
      class="card"
    >
      <div class="hd">
        <strong class="hd-title">
          <StatusChip :tone="orderTone(row.status)" compact />
          {{ orderNoun }} #{{ row.id }}
        </strong>
        <el-tag size="small" effect="plain">{{ displayStatus(row) }}</el-tag>
      </div>
      <ImmSteps v-if="row.status !== 'cancelled'" :steps="orderProgressSteps(row.status, { marketplace })" />
      <p class="sub">
        <span :title="row.createdAt || ''">{{ formatRelative(row.createdAt) }}</span>
        · 合计 ¥{{ row.totalYuan }}
        <template v-if="Number(row.discountYuan) > 0"> · 优惠 ¥{{ row.discountYuan }}</template>
        <template v-if="row.couponCode"> · 券 {{ row.couponCode }}</template>
        <template v-if="Number(row.pointsEarned) > 0"> · 获积分 {{ row.pointsEarned }}</template>
      </p>
      <p v-if="payCountdownText(row)" class="pay-cd" :class="{ urgent: isUrgentCountdown(paySecondsLeft(row)) }">
        {{ payCountdownText(row) }}
      </p>
      <p v-if="row.refundStatus" class="sub refund">
        售后：{{ refundLabel(row.refundStatus) }}
        <template v-if="row.refundReason"> · {{ row.refundReason }}</template>
      </p>
      <p v-if="hasShipInfo(row)" class="ship">
        <template v-if="isStay || isCinema">
          <template v-if="row.remark">备注：{{ row.remark }}</template>
        </template>
        <template v-else>
          <template v-if="row.deliveryType">{{ row.deliveryType }} · </template>
          <template v-if="row.receiverName || row.receiverPhone">
            {{ row.receiverName }} {{ row.receiverPhone }}
          </template>
          <template v-if="row.addressLine"> · {{ row.addressLine }}</template>
          <template v-if="isFood && row.tasteNote"><br />口味：{{ row.tasteNote }}</template>
          <template v-if="!isFood && row.trackingNo"><br />物流单号：{{ row.trackingNo }}</template>
          <template v-if="isFood && row.pickupCode">
            <br />取餐码：{{ row.pickupCode }}
            <CodeQrBlock :code="row.pickupCode" label="取餐码" />
          </template>
          <template v-if="row.remark"><br />备注：{{ row.remark }}</template>
        </template>
      </p>
      <ul class="lines">
        <li v-for="ln in row.lines || []" :key="ln.id">
          {{ ln.title }} × {{ ln.qty }}（¥{{ Number(ln.lineYuan || 0).toFixed(2) }}）
          <template v-if="marketplace && lineShop(ln)"> · {{ lineShop(ln) }}</template>
        </li>
      </ul>
      <div class="acts">
        <el-button v-if="canPay(row)" size="small" type="primary" @click="openPay(row)">去付款</el-button>
        <el-button v-if="canShowTrace(row)" size="small" @click="openTrace(row)">物流轨迹</el-button>
        <el-button
          v-if="canReceive(row)"
          size="small"
          type="success"
          @click="confirmReceive(row)"
        >确认收货</el-button>
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
    <EmptyHint
      v-if="!list.length"
      :title="`暂无${orderNoun}`"
      desc="去逛逛，把心仪商品加进购物车吧。"
      mark="单"
      cta-label="去浏览"
      @cta="$router.push('/archive')"
    />
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
    </template>

    <OrderTraceDialog v-model="traceVisible" :order-id="traceOrderId" />

    <el-dialog v-model="payVisible" title="去付款" width="420px" destroy-on-close>
      <p class="pay-tip">{{ demoPayHint }}</p>
      <el-form label-position="top">
        <el-form-item label="支付方式" required>
          <el-radio-group v-model="payForm.payChannel">
            <el-radio value="alipay">支付宝</el-radio>
            <el-radio value="wechat">微信</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="支付密码" required>
          <el-input
            v-model="payForm.payPassword"
            type="password"
            show-password
            maxlength="32"
            placeholder="请输入支付密码（至少 4 位）"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="payVisible = false">取消</el-button>
        <el-button type="primary" :loading="paying" @click="submitPay">确认支付</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'
import EmptyHint from '../../components/EmptyHint.vue'
import CodeQrBlock from '../../components/CodeQrBlock.vue'
import ImmSteps from '../../components/ImmSteps.vue'
import OrderTraceDialog from '../../components/OrderTraceDialog.vue'
import PageSkeleton from '../../components/PageSkeleton.vue'
import StatusChip from '../../components/StatusChip.vue'
import { formatRelative } from '../../utils/dates.js'
import { hasCap, hasTrait, getSchema, menuLabel } from '../../utils/domainSchema.js'
import {
  deadlineFromCreated,
  formatCountdownClock,
  isUrgentCountdown,
  secondsUntil,
  useNowTick,
} from '../../utils/useCountdown.js'
import { orderProgressSteps, orderTone } from '../../utils/statusTone.js'

const label = menuLabel('user', 'my_orders', '我的订单')
const orderNoun = computed(() => getSchema()?.entities?.order?.label || '订单')
const rawStates = computed(() => getSchema()?.entities?.order?.states || {})
const isFood = computed(() => hasTrait('food'))
const isStay = computed(
  () =>
    hasTrait('slotHotel')
    || hasTrait('slotCarrent')
    || getSchema()?.entities?.order?.fulfillMode === 'stay'
    || getSchema()?.entities?.order?.fulfillMode === 'rental',
)
const isCinema = computed(
  () => hasTrait('seatSelect') || getSchema()?.entities?.order?.fulfillMode === 'cinema',
)
const showTraceBase = computed(() => !isStay.value && !isFood.value && !isCinema.value)
const reviewOn = computed(() => hasCap('order_review'))
const marketplace = computed(() => !!getSchema()?.shopMarketplace)
const demoPay = computed(() => !!getSchema()?.demoPay || marketplace.value)
const demoPayHint = computed(
  () =>
    getSchema()?.labels?.demoPayHint
    || '选择支付宝或微信并输入支付密码完成本单（不对接商户 SDK，仍扣账户余额）。',
)
const timeoutMinutes = computed(() => {
  const n = Number(getSchema()?.orderTimeoutMinutes || 0)
  return Number.isFinite(n) && n > 0 ? n : 0
})
const timeoutHint = computed(
  () => getSchema()?.labels?.orderTimeoutHint || '',
)
const { nowMs } = useNowTick()
const loading = ref(false)
const list = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const status = ref(null)
const traceVisible = ref(false)
const traceOrderId = ref(null)
const reviewedIds = ref(new Set())
const payVisible = ref(false)
const paying = ref(false)
const payOrder = ref(null)
const payForm = reactive({ payChannel: 'alipay', payPassword: '' })

/** 多店买家筛选项：四态；pending 兜底仍可选「待付款」 */
const statusOptions = computed(() => {
  if (!marketplace.value) {
    return Object.entries(rawStates.value).map(([value, lab]) => ({ value, label: lab }))
  }
  const opts = [
    { value: 'confirmed', label: '待发货' },
    { value: 'shipped', label: '已发货' },
    { value: 'completed', label: '已完成' },
    { value: 'cancelled', label: '已取消' },
  ]
  if (rawStates.value.pending) opts.unshift({ value: 'pending', label: '待付款' })
  return opts
})

function displayStatus(row) {
  if (!row) return ''
  if (!marketplace.value) return rawStates.value[row.status] || row.status
  const st = row.status
  if (st === 'pending') return '待付款'
  if (st === 'confirmed') return '待发货'
  if (st === 'shipped' || st === 'in_transit' || st === 'signed') return '已发货'
  if (st === 'completed') return '已完成'
  if (st === 'cancelled') return '已取消'
  return rawStates.value[st] || st
}

function lineShop(ln) {
  return String(ln?.shopName || ln?.shop_name || '').trim()
}

function refundLabel(st) {
  return ({ pending: '待审核', approved: '已通过', rejected: '已驳回' }[st] || st)
}

function paySecondsLeft(row) {
  if (!row || row.status !== 'pending' || !timeoutMinutes.value) return null
  const deadline = deadlineFromCreated(row.createdAt, timeoutMinutes.value)
  if (deadline == null) return null
  return secondsUntil(deadline, nowMs.value)
}

function payCountdownText(row) {
  const sec = paySecondsLeft(row)
  if (sec == null) return ''
  if (sec <= 0) return timeoutHint.value || '支付已超时，订单将自动取消'
  const clock = formatCountdownClock(sec)
  return demoPay.value || marketplace.value
    ? `请在 ${clock} 内完成支付`
    : `请在 ${clock} 内确认，超时将自动取消`
}

function hasShipInfo(row) {
  if (!row) return false
  if (isStay.value || isCinema.value) return !!row.remark
  if (row.deliveryType || row.addressLine || row.receiverName || row.receiverPhone || row.remark) return true
  if (isFood.value) return !!(row.tasteNote || row.pickupCode)
  return !!row.trackingNo
}

function canPay(row) {
  return demoPay.value && row?.status === 'pending'
}

function canShowTrace(row) {
  if (!showTraceBase.value || !row) return false
  if (row.status === 'pending' || row.status === 'cancelled') return false
  return ['confirmed', 'shipped', 'in_transit', 'signed', 'completed'].includes(row.status)
}

function canRefund(row) {
  if (!row) return false
  if (!['shipped', 'in_transit', 'signed', 'completed'].includes(row.status)) return false
  const rs = row.refundStatus || ''
  return !rs || rs === 'rejected'
}

function canReceive(row) {
  if (!marketplace.value || !row) return false
  return ['shipped', 'in_transit', 'signed'].includes(row.status) && row.refundStatus !== 'pending'
}

function canReview(row) {
  if (!reviewOn.value || !row) return false
  if (!['signed', 'completed'].includes(row.status)) return false
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
      .filter((o) => ['signed', 'completed'].includes(o.status))
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
  loading.value = true
  try {
    const res = await http.get('/api/orders', {
      params: { page: page.value, size: size.value, status: status.value || undefined },
    })
    list.value = res.data?.list || []
    total.value = res.data?.total || 0
    await loadReviewsHint(list.value)
  } finally {
    loading.value = false
  }
}

async function cancel(row) {
  await ElMessageBox.confirm(`取消${orderNoun.value} #${row.id}？`, '取消')
  await http.post(`/api/orders/${row.id}/cancel`)
  ElMessage.success('已取消')
  load()
}

async function confirmReceive(row) {
  await ElMessageBox.confirm(`确认已收到${orderNoun.value} #${row.id}？`, '确认收货')
  await http.post(`/api/orders/${row.id}/receive`)
  ElMessage.success('已确认收货')
  load()
}

function openTrace(row) {
  traceOrderId.value = row.id
  traceVisible.value = true
}

function openPay(row) {
  payOrder.value = row
  payForm.payChannel = 'alipay'
  payForm.payPassword = ''
  payVisible.value = true
}

async function submitPay() {
  if (!payOrder.value) return
  if (!['alipay', 'wechat'].includes(payForm.payChannel)) {
    ElMessage.warning('请选择支付方式')
    return
  }
  if (String(payForm.payPassword || '').trim().length < 4) {
    ElMessage.warning('请输入支付密码（至少 4 位）')
    return
  }
  paying.value = true
  try {
    await http.post(`/api/orders/${payOrder.value.id}/pay`, {
      payChannel: payForm.payChannel,
      payPassword: payForm.payPassword,
    })
    ElMessage.success('支付成功')
    payVisible.value = false
    load()
  } finally {
    paying.value = false
  }
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

onMounted(() => {
  load()
})
</script>

<style scoped>
.hero { margin-bottom: 16px; }
.hero h1 { margin: 0 0 6px; font-size: 22px; }
.hero p { margin: 0 0 10px; color: var(--portal-muted, #64748b); font-size: 13px; }
.card {
  background: var(--portal-surface, #fff);
  border: var(--portal-border-width, 1px) solid var(--portal-line, #e2e8f0);
  border-radius: var(--portal-radius, 12px);
  box-shadow: var(--portal-shadow, none);
  padding: var(--portal-pad, 14px) 16px;
  margin-bottom: var(--portal-gap, 12px);
}
.hd { display: flex; justify-content: space-between; gap: 8px; align-items: center; }
.hd-title { display: inline-flex; align-items: center; gap: 8px; }
.sub { margin: 6px 0; color: var(--portal-muted, #64748b); font-size: 12px; }
.sub.refund { color: #b45309; }
.pay-cd { margin: 0 0 6px; color: #b45309; font-size: 13px; font-weight: 600; }
.pay-cd.urgent { color: #b91c1c; }
.ship { margin: 0 0 8px; color: var(--portal-muted, #475569); font-size: 12px; line-height: 1.5; }
.lines { margin: 0; padding-left: 18px; color: var(--portal-ink, #334155); font-size: 13px; }
.acts { margin-top: 10px; display: flex; flex-wrap: wrap; gap: 6px; }
.empty { text-align: center; color: var(--portal-muted, #94a3b8); padding: 40px 0; }
.pager { margin-top: 16px; display: flex; justify-content: flex-end; }
.pay-tip { margin: 0 0 12px; color: var(--portal-muted, #64748b); font-size: 13px; }
</style>
