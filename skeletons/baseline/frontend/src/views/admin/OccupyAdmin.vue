<template>
  <div>
    <h2>{{ title }}</h2>
    <el-table :data="list" stripe>
      <el-table-column prop="username" label="账号" width="140" />
      <el-table-column prop="title" label="事项" />
      <el-table-column prop="periodStart" label="开始" width="180" />
      <el-table-column prop="periodEnd" label="结束" width="180" />
      <el-table-column prop="status" label="状态" width="100" />
    </el-table>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import http from '../../api/http'
import { getSchema } from '../../utils/domainSchema'

const labels = computed(() => getSchema().labels || {})
const title = computed(() => labels.value.occupyAdminTitle || '占用明细')
const list = ref([])

async function load() {
  const res = await http.get('/api/occupy')
  list.value = (res.data && res.data.list) || []
}

onMounted(load)
</script>
