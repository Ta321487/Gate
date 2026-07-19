<template>
  <div>
    <div class="toolbar">
      <el-alert type="info" :closable="false" show-icon title="作业台：查看预约与现场服务状态" />
    </div>
    <ReservationsAdmin />
  </div>
</template>

<script setup>
import ReservationsAdmin from '../admin/ReservationsAdmin.vue'
</script>

<style scoped>
.toolbar { margin-bottom: 12px; }
</style>
