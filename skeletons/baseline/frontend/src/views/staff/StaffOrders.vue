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
const hint = computed(() => {
  if (hasTrait('food')) return `作业台：处理${orderNoun.value}出餐与配送状态`
  return `作业台：处理${orderNoun.value}履约状态`
})
</script>

<style scoped>
.toolbar { margin-bottom: 12px; }
</style>
