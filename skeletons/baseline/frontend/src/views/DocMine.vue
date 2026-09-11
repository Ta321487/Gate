<template>
  <div>
    <section class="hero">
      <h1>{{ title }}</h1>
    </section>
    <el-table :data="list" stripe>
      <el-table-column label="资料" min-width="200">
        <template #default="{ row }">
          <span class="file-mark" aria-hidden="true">{{ fileTypeMark(row.fileUrl || row.title) }}</span>
          {{ row.title }}
        </template>
      </el-table-column>
      <el-table-column prop="downloadedAt" label="下载时间" min-width="160" />
    </el-table>
    <EmptyHint v-if="!list.length" title="暂无下载记录" desc="在资料库下载后会出现在这里。" mark="档" />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import http from '../api/http'
import EmptyHint from '../components/EmptyHint.vue'
import { getSchema } from '../utils/domainSchema'
import { fileTypeMark } from '../utils/statusTone.js'

const list = ref([])
const title = computed(() => (getSchema().labels || {}).docMineTitle || '我的下载')

async function load() {
  const res = await http.get('/api/doclib/mine', { params: { page: 1, size: 50 } })
  list.value = (res.data?.data || res.data || {}).list || []
}
onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 1rem; }
.file-mark {
  display: inline-grid;
  place-items: center;
  width: 22px;
  height: 22px;
  margin-right: 6px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 700;
  color: var(--portal-accent, #0b6e75);
  background: color-mix(in srgb, var(--portal-accent, #0b6e75) 12%, transparent);
  vertical-align: middle;
}
</style>
