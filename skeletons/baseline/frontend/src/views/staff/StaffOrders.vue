<template>
  <div>
    <div class="toolbar">
      <el-alert type="info" :closable="false" show-icon :title="hint" />
    </div>
    <OrdersAdmin />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import OrdersAdmin from '../admin/OrdersAdmin.vue'
import { hasTrait, getSchema } from '../../utils/domainSchema.js'

const orderNoun = computed(() => getSchema()?.entities?.order?.label || '订单')
const orderVerbs = computed(() => getSchema()?.entities?.order?.verbs || {})
const hint = computed(() => {
  if (hasTrait('food')) {
    const ship = orderVerbs.value.ship || '出餐'
    return `作业台：处理${orderNoun.value}${ship}与配送状态`
  }
  if (hasTrait('slotCarrent') || getSchema()?.entities?.order?.fulfillMode === 'rental') {
    return `作业台：处理租车${orderNoun.value}取车/还车`
  }
  if (hasTrait('slotHotel') || getSchema()?.entities?.order?.fulfillMode === 'stay') {
    return `作业台：处理客房${orderNoun.value}入住/离店`
  }
  if (hasTrait('seatSelect') || getSchema()?.entities?.order?.fulfillMode === 'cinema') {
    const ship = orderVerbs.value.ship || '出票'
    return `作业台：处理影票${orderNoun.value}${ship}`
  }
  const ship = orderVerbs.value.ship || '发货'
  const confirm = orderVerbs.value.confirm || '确认'
  return `作业台：处理${orderNoun.value}${confirm}与${ship}`
})
</script>

<style scoped>
.toolbar { margin-bottom: 12px; }
</style>
