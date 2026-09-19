<template>
  <div>
    <div class="toolbar">
      <h2>主观题阅卷</h2>
      <el-button @click="load">刷新</el-button>
    </div>
    <el-table :data="queue" stripe @row-click="open">
      <el-table-column prop="id" label="答卷" width="80" />
      <el-table-column prop="paperTitle" label="试卷" />
      <el-table-column prop="username" label="考生" width="140" />
      <el-table-column prop="submittedAt" label="交卷时间" />
      <el-table-column label="操作" width="100">
        <template #default="{ row }">
          <el-button link type="primary" @click.stop="open(row)">阅卷</el-button>
        </template>
      </el-table-column>
    </el-table>
    <p v-if="!queue.length" class="empty">暂无待阅答卷。</p>

    <el-dialog v-model="visible" title="教师打分" width="640px">
      <div v-for="q in questions" :key="q.questionId" class="q">
        <p><strong>[{{ typeLabel(q.type) }}]</strong> {{ q.stem }}（满分 {{ q.maxScore }}）</p>
        <p v-if="q.type === 'subjective'" class="ref">参考答案：{{ q.answerKey || '（无）' }}</p>
        <p>考生作答：{{ q.userAnswer || '（空）' }}</p>
        <div v-if="q.type === 'subjective' && q.pending" class="mark">
          <el-input-number v-model="scores[q.questionId]" :min="0" :max="q.maxScore" />
          <el-button type="primary" :loading="saving" @click="mark(q)">保存分数</el-button>
        </div>
        <p v-else-if="q.type === 'subjective'">已评 {{ q.earnedScore }} 分</p>
        <p v-else>客观题 {{ q.earnedScore }} / {{ q.maxScore }}</p>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/http'

const queue = ref([])
const visible = ref(false)
const questions = ref([])
const saving = ref(false)
const currentId = ref(null)
const scores = reactive({})

function typeLabel(t) {
  return { single: '单选', multi: '多选', judge: '判断', subjective: '主观' }[t] || t
}

async function load() {
  const res = await http.get('/api/exam/admin/review')
  queue.value = res.data?.data || res.data || []
}

async function open(row) {
  currentId.value = row.id
  const res = await http.get(`/api/exam/admin/review/${row.id}`)
  const list = res.data?.data || res.data || []
  questions.value = list
  for (const q of list) {
    if (q.pending) scores[q.questionId] = 0
  }
  visible.value = true
}

async function mark(q) {
  saving.value = true
  try {
    await http.post(`/api/exam/admin/review/${currentId.value}/mark`, {
      questionId: q.questionId,
      score: scores[q.questionId] ?? 0,
    })
    ElMessage.success('已保存')
    await open({ id: currentId.value })
    await load()
    if (!questions.value.some((item) => item.pending)) {
      visible.value = false
      ElMessage.success('本卷已出总分')
    }
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem; }
.toolbar h2 { margin: 0; }
.empty { color: var(--el-text-color-secondary); }
.q { padding: 0.75rem 0; border-bottom: 1px solid var(--el-border-color-lighter); }
.ref { color: var(--el-text-color-secondary); }
.mark { display: flex; gap: 0.5rem; align-items: center; }
</style>
