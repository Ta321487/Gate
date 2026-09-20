<template>
  <div>
    <p class="hint">付款后可在此查看激活码或下载链接。</p>
    <el-button @click="load">刷新</el-button>
    <el-table :data="list" stripe style="margin-top: 12px">
      <el-table-column prop="orderId" label="订单" width="90" />
      <el-table-column prop="kind" label="类型" width="100" />
      <el-table-column prop="codeValue" label="激活码" min-width="160" />
      <el-table-column label="下载" min-width="180">
        <template #default="{ row }">
          <a v-if="row.linkUrl" :href="row.linkUrl" target="_blank">{{ row.linkUrl }}</a>
          <span v-else>—</span>
        </template>
      </el-table-column>
    </el-table>
    <p v-if="!list.length" class="empty">还没有交付内容。</p>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import http from '../../api/http'

const list = ref([])

async function load() {
  const res = await http.get('/api/digital/mine')
  list.value = res.data || []
}

onMounted(load)
</script>

<style scoped>
.hint, .empty { color: var(--el-text-color-secondary); }
</style>
