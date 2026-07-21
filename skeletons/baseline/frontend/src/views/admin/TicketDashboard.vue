<template>
  <div class="dash">
    <header class="hd">
      <h2>工作台</h2>
      <p>{{ adminLabel }}概览、待办与统计分析。</p>
    </header>

    <div class="stats" :style="{ gridTemplateColumns: `repeat(${Math.min(cards.length, 4)}, 1fr)` }">
      <div
        class="stat"
        :class="{ clickable: !!s.to }"
        v-for="s in cards"
        :key="s.key"
        @click="s.to && $router.push(s.to)"
      >
        <div class="num">{{ s.value }}</div>
        <div class="label">{{ s.label }}</div>
      </div>
    </div>

    <section class="todo card">
      <h3>待办</h3>
      <template v-if="caps.includes('order_lines')">
        <div class="todo-row">
          <span>待确认{{ orderLabel }} {{ data.pendingOrders || 0 }}</span>
          <el-button type="primary" link @click="$router.push('/admin/orders')">去处理</el-button>
        </div>
      </template>
      <template v-else-if="caps.includes('slot_reserve') && !caps.includes('ticket_flow')">
        <div class="todo-row">
          <span>待办结{{ reservationLabel }} {{ data.confirmedReservations || 0 }}</span>
          <el-button type="primary" link @click="$router.push('/admin/reservations')">去办结</el-button>
        </div>
      </template>
      <template v-else>
        <div class="todo-row">
          <span>待受理 {{ data.pendingTickets || 0 }} {{ ticketUnit }}</span>
          <el-button type="primary" link @click="$router.push('/admin/tickets')">去受理</el-button>
        </div>
        <div v-if="!approveEndsFlow" class="todo-row">
          <span>处理中 {{ data.activeTickets || 0 }} {{ ticketUnit }}</span>
          <el-button link @click="$router.push('/admin/ticket-records')">看记录</el-button>
        </div>
        <div v-if="!approveEndsFlow && Number(data.rejectedTickets) > 0" class="todo-row">
          <span>{{ rejectedLabel }} {{ data.rejectedTickets || 0 }} {{ ticketUnit }}</span>
          <el-button link @click="$router.push({ path: '/admin/ticket-records', query: { status: 'rejected' } })">看记录</el-button>
        </div>
        <template v-else-if="approveEndsFlow">
          <div class="todo-row">
            <span>已通过 {{ data.approvedTickets || 0 }} · {{ rejectedLabel }} {{ data.rejectedTickets || 0 }}</span>
            <el-button link @click="$router.push('/admin/ticket-records')">看记录</el-button>
          </div>
        </template>
        <div v-if="ticket.allowRating" class="todo-row">
          <span>已评价 {{ data.ratedCount || 0 }} {{ ticketUnit }} · 均分 {{ data.avgRating ?? '—' }}</span>
          <el-button link @click="$router.push('/admin/ticket-records?rated=1')">看评价</el-button>
        </div>
        <div v-if="showOverdue" class="todo-row">
          <span>逾期 {{ data.overdueBorrow || 0 }} {{ ticketUnit }}</span>
          <el-button link @click="$router.push('/admin/overdue')">去{{ remindVerb }}</el-button>
        </div>
      </template>
    </section>

    <DashboardCharts :charts="data.charts || {}" :mode="chartMode" />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import http from '../../api/http'
import { getSchema, menuLabel, ticketCopy, reservationCopy } from '../../utils/domainSchema.js'
import DashboardCharts from '../../components/DashboardCharts.vue'

const data = ref({})
const adminLabel = computed(() => getSchema()?.roles?.admin?.label || '管理')
const userLabel = computed(() => getSchema()?.roles?.user?.label || '用户')
const caps = computed(() => getSchema()?.capabilities || [])
const showOverdue = computed(() => caps.value.includes('deadline'))
const showArchive = computed(() => caps.value.includes('archive') && data.value.bookTotal != null)
const ticket = computed(() => ticketCopy() || {})
const ticketUnit = computed(() => ticket.value.label || '单')
const approveEndsFlow = computed(
  () => !!(ticket.value.approveEndsFlow || data.value.approveEndsFlow),
)
const rejectedLabel = computed(() => ticket.value.states?.rejected || '已驳回')
const remindVerb = computed(() => ticket.value.verbs?.remind || '催办')
const orderLabel = computed(() => getSchema()?.entities?.order?.label || '订单')
const reservationLabel = computed(() => reservationCopy()?.label || '预约')

const chartMode = computed(() => {
  if (caps.value.includes('order_lines') && !caps.value.includes('ticket_flow')) return 'order'
  if (caps.value.includes('slot_reserve') && !caps.value.includes('ticket_flow')) return 'reservation'
  return 'ticket'
})

const cards = computed(() => {
  const list = []
  if (caps.value.includes('order_lines')) {
    list.push(
      { key: 'op', label: `待确认${orderLabel.value}`, value: data.value.pendingOrders ?? '—' },
      { key: 'oc', label: '已确认', value: data.value.confirmedOrders ?? '—' },
      { key: 'os', label: '履约中', value: data.value.shippedOrders ?? '—' },
      { key: 'od', label: '已完成', value: data.value.completedOrders ?? '—' },
    )
  } else if (caps.value.includes('slot_reserve') && !caps.value.includes('ticket_flow')) {
    list.push(
      { key: 'rp', label: `待确认${reservationLabel.value}`, value: data.value.pendingReservations ?? '—' },
      { key: 'rc', label: `已确认${reservationLabel.value}`, value: data.value.confirmedReservations ?? '—' },
      { key: 'rd', label: `已办结${reservationLabel.value}`, value: data.value.completedReservations ?? '—' },
    )
  } else {
    list.push(
      { key: 'pending', label: '待受理', value: data.value.pendingTickets ?? '—' },
    )
    if (!approveEndsFlow.value) {
      list.push({ key: 'active', label: '处理中', value: data.value.activeTickets ?? '—' })
      list.push({ key: 'done', label: '已完成', value: data.value.completedTickets ?? '—' })
      list.push({
        key: 'rejected',
        label: rejectedLabel.value,
        value: data.value.rejectedTickets ?? '—',
        to: '/admin/ticket-records?status=rejected',
      })
    } else {
      list.push(
        { key: 'approved', label: '已通过', value: data.value.approvedTickets ?? '—' },
        {
          key: 'rejected',
          label: rejectedLabel.value,
          value: data.value.rejectedTickets ?? '—',
          to: '/admin/ticket-records?status=rejected',
        },
        { key: 'done', label: '已处理', value: data.value.completedTickets ?? '—' },
      )
    }
    if (showOverdue.value && Number(data.value.overdueBorrow) > 0) {
      const insertAt = approveEndsFlow.value ? 1 : 2
      list.splice(insertAt, 0, { key: 'overdue', label: '逾期', value: data.value.overdueBorrow })
    }
  }
  list.push({ key: 'users', label: userLabel.value + '数', value: data.value.userTotal ?? '—' })
  if (ticket.value.allowRating && data.value.avgRating != null) {
    list.push({
      key: 'avg',
      label: `均分${data.value.ratedCount ? `（${data.value.ratedCount}）` : ''}`,
      value: data.value.avgRating,
      to: '/admin/ticket-records?rated=1',
    })
  }
  if (showArchive.value) {
    list.push({ key: 'items', label: menuLabel('admin', 'archive', '对象') + '数', value: data.value.bookTotal ?? '—' })
  }
  return list
})

async function load() {
  const res = await http.get('/api/admin/dashboard')
  data.value = res.data || {}
}

onMounted(load)
</script>

<style scoped>
.hd { margin-bottom: 18px; }
.hd h2 { margin: 0 0 6px; font-size: 20px; }
.hd p { margin: 0; color: #8a9aa6; font-size: 13px; }
.stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}
.stat {
  background: var(--portal-surface, #fff);
  border: var(--portal-border-width, 1px) solid var(--portal-line, #e4eaf0);
  border-radius: var(--portal-radius, 10px);
  box-shadow: var(--portal-shadow, none);
  padding: 14px 12px;
}
.stat.clickable {
  cursor: pointer;
  transition: border-color 0.15s ease;
}
.stat.clickable:hover {
  border-color: color-mix(in srgb, var(--portal-accent, #0b6e75) 40%, var(--portal-line, #e4eaf0));
}
.num { font-size: 22px; font-weight: 700; letter-spacing: -0.02em; }
.label { margin-top: 4px; font-size: 12px; color: #8a9aa6; }
.card {
  background: var(--portal-surface, #fff);
  border: var(--portal-border-width, 1px) solid var(--portal-line, #e4eaf0);
  border-radius: var(--portal-radius, 10px);
  box-shadow: var(--portal-shadow, none);
  padding: 16px;
}
.card h3 { margin: 0 0 12px; font-size: 15px; }
.todo-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 8px 0; border-top: 1px solid #f0f3f6; font-size: 14px;
}
.todo-row:first-of-type { border-top: none; }
@media (max-width: 900px) {
  .stats { grid-template-columns: repeat(2, 1fr) !important; }
}
</style>
