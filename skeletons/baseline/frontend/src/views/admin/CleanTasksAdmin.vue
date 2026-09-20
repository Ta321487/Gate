<template>
  <div>
    <p class="hint">{{ hint }}</p>
    <el-button @click="load">刷新</el-button>
    <el-table :data="list" stripe style="margin-top: 12px">
      <el-table-column prop="roomNo" label="房号" width="100" />
      <el-table-column prop="roomTypeTitle" label="房型" width="140" />
      <el-table-column prop="status" label="状态" width="100" />
      <el-table-column label="操作" min-width="140">
        <template #default="{ row }">
          <el-button link type="primary" @click="done(row)">打扫完成</el-button>
        </template>
      </el-table-column>
    </el-table>
    <p v-if="!list.length" class="empty">暂无待打扫房间。</p>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/http'
import { getSchema } from '../../utils/domainSchema.js'

const list = ref([])
const hint = computed(() => getSchema()?.labels?.cleanTasksHint || '完成打扫后点完成，房间回到空房。')

async function load() {
  const res = await http.get('/api/hotel-pms/clean-tasks')
  list.value = res.data || []
}

async function done(row) {
  await http.post(`/api/hotel-pms/rooms/${row.id}/clean-done`)
  ElMessage.success('已标为空房')
  await load()
}

onMounted(load)
</script>

<style scoped>
.hint { color: #666; margin-bottom: 12px; }
.empty { color: #999; margin-top: 16px; }
</style>
