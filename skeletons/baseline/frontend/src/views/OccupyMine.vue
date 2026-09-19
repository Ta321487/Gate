<template>
  <div>
    <h2>{{ title }}</h2>
    <p class="lead">{{ lead }}</p>
    <el-table :data="list" stripe>
      <el-table-column prop="title" label="事项" />
      <el-table-column prop="periodStart" label="开始" width="180" />
      <el-table-column prop="periodEnd" label="结束" width="180" />
      <el-table-column prop="status" label="状态" width="100" />
    </el-table>
    <el-empty v-if="!list.length" description="暂无占用" />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import http from '../api/http'
import { getSchema } from '../utils/domainSchema'

const labels = computed(() => getSchema().labels || {})
const title = computed(() => labels.value.occupyMineTitle || '我的占用')
const lead = computed(
  () => labels.value.occupyMineLead || '查看本人已占用的起止时段；与已有占用相交时不可再提交。',
)
const list = ref([])

async function load() {
  const res = await http.get('/api/occupy/mine')
  list.value = (res.data && res.data.list) || []
}

onMounted(load)
</script>
