<template>
  <div>
    <section class="hero">
      <h1>{{ title }}</h1>
      <p>{{ lead }}</p>
    </section>
    <el-table :data="list" stripe empty-text="暂无公示记录">
      <el-table-column prop="title" label="公示标题" min-width="200" />
      <el-table-column label="公示期" min-width="190">
        <template #default="{ row }">
          {{ row.startAt || '—' }} ~ {{ row.endAt || '—' }}
        </template>
      </el-table-column>
      <el-table-column label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="row.status === 'closed' ? 'info' : 'success'" size="small">
            {{ row.status === 'closed' ? '已结束' : '公示中' }}
          </el-tag>
        </template>
      </el-table-column>
    </el-table>
    <p v-if="!list.length" class="empty">还没有公示记录，公示开始后可在此查阅。</p>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import http from '../../api/http'
import { getSchema } from '../../utils/domainSchema.js'

const labels = getSchema()?.labels || {}
const title = labels.fundPublicityMineTitle || '公示查阅'
const lead = labels.fundPublicityMineLead || '查看本人申请项目的公示状态与公示期。'

const list = ref([])

function unwrap(res) {
  return res.data?.data ?? res.data
}

async function load() {
  const res = await http.get('/api/fund-publicity/mine')
  list.value = unwrap(res) || []
}

onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 14px; }
.hero h1 { margin: 0 0 4px; font-size: 20px; }
.hero p { margin: 0; color: var(--portal-muted, #64748b); font-size: 13px; }
.empty { color: var(--el-text-color-secondary); }
</style>
