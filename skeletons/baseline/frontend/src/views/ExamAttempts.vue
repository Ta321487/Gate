<template>
  <div>
    <section class="hero">
      <h1>{{ title }}</h1>
    </section>
    <el-table :data="list" stripe>
      <el-table-column prop="paperId" label="试卷" width="90" />
      <el-table-column prop="mode" label="模式" width="90" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">{{ statusText(row.status) }}</template>
      </el-table-column>
      <el-table-column label="得分" width="140">
        <template #default="{ row }">
          <span v-if="row.status === 'reviewing'">待阅卷</span>
          <span v-else>{{ row.score }} / {{ row.totalScore }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="submittedAt" label="交卷时间" />
      <el-table-column v-if="certOn" label="证书" width="120">
        <template #default="{ row }">
          <el-button
            v-if="row.status === 'submitted' && row.mode !== 'practice'"
            link
            type="primary"
            @click="$router.push(`/exam/certificate/${row.id}`)"
          >
            {{ certOpenLabel }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination
      class="pager"
      v-model:current-page="page"
      v-model:page-size="size"
      layout="total, sizes, prev, pager, next"
      :page-sizes="[10, 20, 50]"
      :total="total"
      @current-change="load"
      @size-change="load"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import http from '../api/http'
import { getSchema } from '../utils/domainSchema'

const list = ref([])
const page = ref(1)
const size = ref(10)
const total = ref(0)
const schema = computed(() => getSchema() || {})
const labels = computed(() => schema.value.labels || {})
const thicken = computed(() => schema.value.interactThicken || {})
const title = computed(() => labels.value.examAttemptsTitle || '我的成绩')
const certOn = computed(() => !!thicken.value.examCertificate)
const certOpenLabel = computed(() => labels.value.examCertificateOpenLabel || '查看证书')

function statusText(s) {
  return { in_progress: '答题中', submitted: '已出分', reviewing: '待阅卷' }[s] || s
}

async function load() {
  const res = await http.get('/api/exam/attempts/mine', { params: { page: page.value, size: size.value } })
  const data = res.data?.data || res.data || {}
  list.value = data.list || []
  total.value = data.total || 0
}

onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 1rem; }
.pager { margin-top: 1rem; }
</style>
