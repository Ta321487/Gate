<template>
  <div class="card">
    <h2>{{ title }}</h2>
    <el-table :data="rows" stripe empty-text="还没有佣金记录">
      <el-table-column prop="orderId" label="订单" width="100" />
      <el-table-column prop="buyer" label="下单人" width="140" />
      <el-table-column prop="inviter" label="邀请人" width="140" />
      <el-table-column prop="amountYuan" label="金额" width="120" />
      <el-table-column prop="createdAt" label="时间" min-width="180" />
    </el-table>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import http from '../../api/http'
import { getSchema } from '../../utils/domainSchema.js'

const title = computed(() => getSchema()?.labels?.commissionMenu || '佣金台账')
const rows = ref([])

onMounted(async () => {
  const res = await http.get('/api/admin/commissions')
  rows.value = res.data || []
})
</script>
