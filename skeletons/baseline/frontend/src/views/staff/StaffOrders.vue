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
import { currentStaffPost } from '../../utils/staffPosts.js'

const orderNoun = computed(() => getSchema()?.entities?.order?.label || '订单')
const orderVerbs = computed(() => getSchema()?.entities?.order?.verbs || {})
const postId = computed(() => currentStaffPost())

const hint = computed(() => {
  const post = postId.value
  const ship = orderVerbs.value.ship || '发货'
  const confirm = orderVerbs.value.confirm || '确认'
  const complete = orderVerbs.value.complete || '完成'
  // 毕设骑手端：配送单列表 + 出餐/配送/送达（精简，无地图）
  if (post === 'rider') {
    return `配送单作业：查看待配送${orderNoun.value}，按序「${confirm}→${ship}→${complete}」推进到送达`
  }
  // 毕设拣货：待拣列表 + 确认出库
  if (post === 'picker') {
    return `拣货作业：按${orderNoun.value}拣配出库，主路径「${confirm}→${ship}→${complete}」`
  }
  if (hasTrait('food')) {
    return `作业台：处理${orderNoun.value}${ship}与配送状态`
  }
  if (hasTrait('slotCarrent') || getSchema()?.entities?.order?.fulfillMode === 'rental') {
    return `作业台：处理租车${orderNoun.value}取车/还车`
  }
  if (hasTrait('slotHotel') || getSchema()?.entities?.order?.fulfillMode === 'stay') {
    return `作业台：处理客房${orderNoun.value}入住/离店`
  }
  if (hasTrait('seatSelect') || getSchema()?.entities?.order?.fulfillMode === 'cinema') {
    return `作业台：处理影票${orderNoun.value}${ship}`
  }
  return `作业台：处理${orderNoun.value}${confirm}与${ship}`
})
</script>

<style scoped>
.toolbar { margin-bottom: 12px; }
</style>
