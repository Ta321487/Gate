<template>
  <div class="dash">
    <header class="hd">
      <h2>工作台</h2>
      <p>{{ adminLabel }}概览与待办入口。</p>
    </header>

    <div class="stats" :style="{ gridTemplateColumns: `repeat(${cards.length}, 1fr)` }">
      <div class="stat" v-for="s in cards" :key="s.key">
        <div class="num">{{ s.value }}</div>
        <div class="label">{{ s.label }}</div>
      </div>
    </div>

    <section class="todo card">
      <h3>待办</h3>
      <template v-if="caps.includes('order_lines')">
        <div class="todo-row">
          <span>待确认订单 {{ data.pendingOrders || 0 }}</span>
          <el-button type="primary" link @click="$router.push('/admin/orders')">去处理</el-button>
        </div>
      </template>
      <template v-else-if="caps.includes('slot_reserve')">
        <div class="todo-row">
          <span>已预约 {{ data.confirmedReservations || 0 }}</span>
          <el-button type="primary" link @click="$router.push('/admin/reservations')">看预约</el-button>
        </div>
      </template>
      <template v-else>
        <div class="todo-row">
          <span>待受理 {{ data.pendingTickets || 0 }} 单</span>
          <el-button type="primary" link @click="$router.push('/admin/tickets')">去受理</el-button>
        </div>
        <div class="todo-row">
          <span>处理中 {{ data.activeTickets || 0 }} 单</span>
          <el-button link @click="$router.push('/admin/ticket-records')">看记录</el-button>
        </div>
        <div v-if="showOverdue" class="todo-row">
          <span>逾期 {{ data.overdueBorrow || 0 }} 单</span>
          <el-button link @click="$router.push('/admin/overdue')">去催还</el-button>
        </div>
      </template>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import http from '../../api/http'
import { getSchema, menuLabel } from '../../utils/domainSchema.js'

const data = ref({})
const adminLabel = computed(() => getSchema()?.roles?.admin?.label || '管理')
const userLabel = computed(() => getSchema()?.roles?.user?.label || '用户')
const caps = computed(() => getSchema()?.capabilities || [])
const showOverdue = computed(() => caps.value.includes('deadline'))
const showArchive = computed(() => caps.value.includes('archive') && data.value.bookTotal != null)

const cards = computed(() => {
  const list = []
  if (caps.value.includes('order_lines')) {
    list.push(
      { key: 'op', label: '待确认订单', value: data.value.pendingOrders ?? '—' },
      { key: 'oc', label: '已确认', value: data.value.confirmedOrders ?? '—' },
      { key: 'os', label: '履约中', value: data.value.shippedOrders ?? '—' },
      { key: 'od', label: '已完成', value: data.value.completedOrders ?? '—' },
    )
  } else if (caps.value.includes('slot_reserve')) {
    list.push(
      { key: 'rp', label: '待确认预约', value: data.value.pendingReservations ?? '—' },
      { key: 'rc', label: '已预约', value: data.value.confirmedReservations ?? '—' },
    )
  } else {
    list.push(
      { key: 'pending', label: '待受理', value: data.value.pendingTickets ?? '—' },
      { key: 'active', label: '处理中', value: data.value.activeTickets ?? '—' },
      { key: 'done', label: '已完成', value: data.value.completedTickets ?? '—' },
    )
    if (showOverdue.value && Number(data.value.overdueBorrow) > 0) {
      list.splice(2, 0, { key: 'overdue', label: '逾期', value: data.value.overdueBorrow })
    }
  }
  list.push({ key: 'users', label: userLabel.value + '数', value: data.value.userTotal ?? '—' })
  if (showArchive.value) {
    list.push({ key: 'items', label: menuLabel('admin', 'archive', '档案') + '数', value: data.value.bookTotal ?? '—' })
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
  background: #fff;
  border: 1px solid #e4eaf0;
  border-radius: 10px;
  padding: 14px 12px;
}
.num { font-size: 22px; font-weight: 700; letter-spacing: -0.02em; }
.label { margin-top: 4px; font-size: 12px; color: #8a9aa6; }
.card {
  background: #fff;
  border: 1px solid #e4eaf0;
  border-radius: 10px;
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
