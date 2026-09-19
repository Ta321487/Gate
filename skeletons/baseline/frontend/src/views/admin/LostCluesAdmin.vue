<template>
  <div>
    <h2>{{ title }}</h2>
    <p class="lead">{{ lead }}</p>
    <el-table :data="list" stripe>
      <el-table-column prop="id" label="编号" width="70" />
      <el-table-column prop="lostItemId" label="启事" width="80" />
      <el-table-column label="来源" min-width="120">
        <template #default="{ row }">
          <span v-if="row.userId">用户 {{ row.userId }}</span>
          <span v-else>游客 {{ row.guestName || '匿名' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="guestContact" label="联系方式" width="120" />
      <el-table-column label="类型" width="80">
        <template #default="{ row }">{{ row.type === 'ask' ? '询问' : '线索' }}</template>
      </el-table-column>
      <el-table-column prop="content" label="内容" min-width="200" show-overflow-tooltip />
      <el-table-column prop="createdAt" label="时间" width="160" />
    </el-table>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import http from '../../api/http'
import { getSchema } from '../../utils/domainSchema'

const labels = computed(() => getSchema().labels || {})
const title = computed(() => labels.value.lostCluePageTitle || '线索留言')
const lead = computed(
  () =>
    labels.value.lostCluePageLead ||
    '路人可留线索或询问，不必注册；登录用户会记到本人名下。',
)
const list = ref([])

async function load() {
  const res = await http.get('/api/lost/message')
  list.value = res.data || []
}

onMounted(load)
</script>
