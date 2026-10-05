<template>
  <div>
    <section class="hero">
      <h1>成绩查询</h1>
      <p>已登记的课程分数与课内名次。并列时分数相同则名次相同。</p>
      <p v-if="objectionHint" class="sub">{{ objectionHint }}</p>
      <p v-if="evalBeforeGradeHint" class="sub">{{ evalBeforeGradeHint }}</p>
      <p v-if="blockedHint" class="sub">{{ blockedHint }}</p>
    </section>
    <el-table :data="list" stripe>
      <el-table-column prop="termName" label="学期" />
      <el-table-column prop="courseTitle" label="课程" />
      <el-table-column prop="score" label="分数" width="100" />
      <el-table-column prop="rankNo" label="课内名次" width="110" />
      <el-table-column v-if="objectionOn" prop="objectionDueAt" :label="objectionWindowLabel" width="150">
        <template #default="{ row }">{{ row.objectionDueAt || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="objectionOn" label="操作" width="150">
        <template #default="{ row }">
          <el-button link type="primary" :disabled="!row.objectionOpen" @click="applyChange(row)">
            {{ row.objectionOpen ? '提交更正申请' : '已过时限' }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>
    <p v-if="!list.length" class="empty">还没有已登记的成绩。</p>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import http from '../api/http'
import { getSchema } from '../utils/domainSchema.js'

const router = useRouter()
const labels = getSchema()?.labels || {}
const objectionHint = computed(() => {
  const base = labels.objectionWindowHint || ''
  if (!base) return ''
  return objectionDays.value > 0 ? base.replace(/N/g, String(objectionDays.value)) : base
})
const objectionWindowLabel = labels.objectionWindowLabel || '异议登记截止日'

const list = ref([])
const objectionDays = ref(0)
const blockedHint = ref('')
const evalBeforeGradeHint = computed(() => labels.evalBeforeGradeHint || '')
// 入口按时限关：由 /api/grade-scores/mine 回显的 objectionOpen / objectionDueAt 决定
const objectionOn = computed(() => objectionDays.value > 0 || list.value.some((r) => r.objectionDueAt))

async function load() {
  blockedHint.value = ''
  try {
    const res = await http.get('/api/grade-scores/mine')
    list.value = res.data?.data || res.data || []
  } catch (e) {
    list.value = []
    blockedHint.value = e?.response?.data?.message || e?.message || '请先完成评教后再查看成绩'
  }
  try {
    const meta = await http.get('/api/grade-scores/meta')
    objectionDays.value = Number((meta.data?.data || meta.data || {}).objectionDays || 0)
  } catch (e) {
    objectionDays.value = 0
  }
}

function applyChange(row) {
  if (!row.objectionOpen) return
  router.push({ path: '/my-tickets', query: { courseId: row.courseId } })
}

onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 1rem; }
.hero h1 { margin: 0 0 0.35rem; font-size: 1.5rem; }
.hero p { margin: 0; color: var(--el-text-color-secondary); }
.sub { margin-top: 0.35rem; font-size: 13px; }
.empty { color: var(--el-text-color-secondary); padding: 2rem 0; }
</style>
