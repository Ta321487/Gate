<template>
  <div>
    <div class="toolbar">
      <el-alert type="info" :closable="false" show-icon title="作业台：处理配送/出餐等订单状态" />
    </div>
    <OrdersAdmin />
  </div>
</template>

<script setup>
import OrdersAdmin from '../admin/OrdersAdmin.vue'
</script>

<style scoped>
.toolbar { margin-bottom: 12px; }
</style>
