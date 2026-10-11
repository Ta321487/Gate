<template>
  <div>
    <section class="hero">
      <h1>{{ title }}</h1>
      <p>{{ lead }}</p>
    </section>
    <el-table :data="list" stripe>
      <el-table-column prop="rank" label="名次" width="80" />
      <el-table-column prop="username" label="账号" />
      <el-table-column prop="balanceHours" :label="hoursLabel" width="140" />
    </el-table>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import http from '../api/http'
import { getSchema } from '../utils/domainSchema'

const labels = computed(() => getSchema()?.labels || {})
const title = computed(() => labels.value.tbRankTitle || '时长排行榜')
const lead = computed(() => labels.value.tbRankLead || '按账户余额小时数排序，仅供参考。')
const hoursLabel = computed(() => labels.value.tbRankHoursLabel || '时长（小时）')
const list = ref([])

async function load() {
  const res = await http.get('/api/timebank/rank', { params: { limit: 30 } })
  list.value = res.data?.data || res.data || []
}

onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 1rem; }
</style>
