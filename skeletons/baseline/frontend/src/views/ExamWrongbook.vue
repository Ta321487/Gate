<template>
  <div>
    <section class="hero">
      <h1>{{ title }}</h1>
    </section>
    <el-table :data="list" stripe>
      <el-table-column prop="questionId" label="题号" width="90" />
      <el-table-column prop="stem" label="题干" />
      <el-table-column prop="lastAnswer" label="我的作答" width="160" />
      <el-table-column label="操作" width="100">
        <template #default="{ row }">
          <el-button link type="danger" @click="remove(row.id)">移除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../utils/http'
import { getSchema } from '../utils/domainSchema'

const list = ref([])
const title = computed(() => (getSchema().labels || {}).examWrongbookTitle || '错题本')

async function load() {
  const res = await http.get('/api/exam/wrongbook', { params: { page: 1, size: 50 } })
  const data = res.data?.data || res.data || {}
  list.value = data.list || []
}

async function remove(id) {
  await http.delete(`/api/exam/wrongbook/${id}`)
  ElMessage.success('已移除')
  await load()
}

onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 1rem; }
</style>
