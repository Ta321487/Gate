<template>
  <div>
    <section class="hero">
      <h1>{{ title }}</h1>
      <p class="muted">存入为正、核销为负。</p>
    </section>
    <el-table :data="list" stripe>
      <el-table-column prop="createdAt" label="时间" width="180" />
      <el-table-column prop="deltaHours" label="变动(小时)" width="120" />
      <el-table-column prop="reason" label="说明" />
      <el-table-column prop="refType" label="类型" width="100" />
    </el-table>
    <el-pagination
      v-if="total > size"
      class="pager"
      layout="prev, pager, next"
      :total="total"
      :page-size="size"
      v-model:current-page="page"
      @current-change="load"
    />
    <div v-if="!list.length" class="empty">暂无流水。</div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import http from '../utils/http'
import { getSchema } from '../utils/domainSchema'

const labels = computed(() => getSchema().labels || {})
const title = computed(() => labels.value.tbLedgerTitle || '时长流水')
const list = ref([])
const total = ref(0)
const page = ref(1)
const size = 10

async function load() {
  const res = await http.get('/api/timebank/ledger/mine', { params: { page: page.value, size } })
  const data = res.data?.data || res.data || {}
  list.value = data.list || []
  total.value = data.total || 0
}

watch(page, load)
onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 1rem; }
.muted { color: var(--el-text-color-secondary); }
.pager { margin-top: 1rem; }
.empty { color: var(--el-text-color-secondary); margin-top: 1rem; }
</style>
