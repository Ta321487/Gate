<template>
  <div>
    <div class="toolbar">
      <el-alert type="info" :closable="false" show-icon :title="hint" />
    </div>
    <ReservationsAdmin />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import ReservationsAdmin from '../admin/ReservationsAdmin.vue'
import { getSchema, reservationCopy } from '../../utils/domainSchema.js'

const resvNoun = computed(() => reservationCopy().label || '预约')
const hint = computed(() => `作业台：查看${resvNoun.value}与现场服务状态`)
</script>

<style scoped>
.toolbar { margin-bottom: 12px; }
</style>
