<template>
  <div>
    <div class="toolbar">
      <el-alert type="info" :closable="false" show-icon title="作业台：查看待办并办理（与后台受理同源接口）" />
    </div>
    <TicketsAdmin />
  </div>
</template>

<script setup>
import TicketsAdmin from '../admin/TicketsAdmin.vue'
</script>

<style scoped>
.toolbar { margin-bottom: 12px; }
</style>
