<template>
  <div>
    <h2>{{ title }}</h2>
    <el-table :data="list" stripe>
      <el-table-column prop="createdAt" label="时间" width="180" />
      <el-table-column label="变动" width="110">
        <template #default="{ row }">{{ row.deltaQty }} {{ row.unitLabel || unit }}</template>
      </el-table-column>
      <el-table-column prop="reason" label="说明" />
    </el-table>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import http from '../api/http'
import { getSchema } from '../utils/domainSchema'

const labels = computed(() => getSchema().labels || {})
const title = computed(() => labels.value.balanceLedgerTitle || '额度流水')
const unit = computed(() => labels.value.balanceUnit || '次')
const list = ref([])

async function load() {
  const res = await http.get('/api/balance/ledger/mine')
  list.value = (res.data && res.data.list) || []
}

onMounted(load)
</script>
