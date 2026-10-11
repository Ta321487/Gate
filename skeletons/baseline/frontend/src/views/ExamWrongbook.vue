<template>
  <div>
    <section class="hero">
      <h1>{{ title }}</h1>
      <p v-if="exportOn && exportHint" class="hint">{{ exportHint }}</p>
      <el-button v-if="exportOn" @click="exportCsv">{{ exportLabel }}</el-button>
    </section>
    <el-table :data="list" stripe>
      <el-table-column prop="questionId" label="题号" width="90" />
      <el-table-column prop="stem" label="题干" />
      <el-table-column prop="type" label="题型" width="90" />
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
import http from '../api/http'
import { getSchema } from '../utils/domainSchema'

const list = ref([])
const schema = computed(() => getSchema() || {})
const labels = computed(() => schema.value.labels || {})
const thicken = computed(() => schema.value.interactThicken || {})
const title = computed(() => labels.value.examWrongbookTitle || '错题本')
const exportOn = computed(() => !!thicken.value.examWrongbookExport)
const exportLabel = computed(() => labels.value.examWrongbookExportLabel || '导出错题')
const exportHint = computed(() => labels.value.examWrongbookExportHint || '')

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

async function exportCsv() {
  try {
    const res = await http.get('/api/exam/wrongbook/export', { responseType: 'blob' })
    const blob = new Blob([res.data], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'exam_wrongbook.csv'
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('已导出')
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '导出失败')
  }
}

onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 1rem; }
.hint { color: var(--el-text-color-secondary); font-size: 13px; }
</style>
