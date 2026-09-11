<template>
  <div>
    <section class="hero">
      <div class="hero-row">
        <div>
          <h1>答题中</h1>
          <p v-if="attempt">
            试卷 #{{ attempt.paperId }} · {{ attempt.mode === 'practice' ? '练习' : '考试' }}
          </p>
        </div>
        <div
          v-if="showTimer"
          class="exam-cd"
          :class="{ 'cd-urgent': isUrgentCountdown(remainSec, 120) }"
        >
          剩余 {{ formatCountdownClock(remainSec) }}
        </div>
      </div>
    </section>
    <div v-if="submitted" class="card result">
      <h2>得分 {{ result.score }} / {{ result.totalScore }}</h2>
      <el-button type="primary" @click="$router.push('/exam/attempts')">查看成绩</el-button>
    </div>
    <div v-else class="list">
      <div class="answer-sheet" aria-label="答题卡">
        <button
          v-for="(q, idx) in questions"
          :key="q.id"
          type="button"
          class="q-dot"
          :class="{ filled: isAnswered(q), current: focusIdx === idx }"
          @click="scrollTo(idx)"
        >
          {{ idx + 1 }}
        </button>
      </div>
      <article
        v-for="(q, idx) in questions"
        :key="q.id"
        :ref="(el) => setQRef(idx, el)"
        class="card item"
      >
        <div class="stem">{{ idx + 1 }}. [{{ typeLabel(q.type) }}] {{ q.stem }}（{{ q.score }}分）</div>
        <div v-if="q.type === 'single' || q.type === 'judge'" class="opts">
          <el-radio-group v-model="answers[q.id]">
            <el-radio v-for="(opt, i) in parseOpts(q)" :key="i" :value="optLetter(i, q.type, opt)">
              {{ optLetter(i, q.type, opt) }}. {{ displayOpt(opt, q.type) }}
            </el-radio>
          </el-radio-group>
        </div>
        <div v-else-if="q.type === 'multi'" class="opts">
          <el-checkbox-group v-model="multi[q.id]">
            <el-checkbox v-for="(opt, i) in parseOpts(q)" :key="i" :label="String.fromCharCode(65 + i)">
              {{ String.fromCharCode(65 + i) }}. {{ opt }}
            </el-checkbox>
          </el-checkbox-group>
        </div>
        <el-input v-else v-model="answers[q.id]" type="textarea" :rows="3" placeholder="简答…" />
      </article>
      <el-button type="primary" :loading="posting" @click="submit">交卷</el-button>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import http from '../api/http'
import { parseDateMs } from '../utils/dates.js'
import {
  formatCountdownClock,
  isUrgentCountdown,
  secondsUntil,
  useNowTick,
} from '../utils/useCountdown.js'

const route = useRoute()
const router = useRouter()
const questions = ref([])
const attempt = ref(null)
const durationMin = ref(0)
const answers = reactive({})
const multi = reactive({})
const posting = ref(false)
const submitted = ref(false)
const result = ref({})
const focusIdx = ref(0)
const qRefs = ref([])
const { nowMs } = useNowTick()

const deadlineMs = computed(() => {
  if (!attempt.value?.startedAt || !durationMin.value) return null
  const start = parseDateMs(attempt.value.startedAt)
  if (start == null) return null
  return start + durationMin.value * 60 * 1000
})

const remainSec = computed(() => {
  if (deadlineMs.value == null) return null
  return secondsUntil(deadlineMs.value, nowMs.value)
})

const showTimer = computed(
  () => !submitted.value && attempt.value?.mode !== 'practice' && remainSec.value != null,
)

function typeLabel(t) {
  return ({ single: '单选', multi: '多选', judge: '判断', subjective: '主观' }[t] || t)
}

function parseOpts(q) {
  try {
    const raw = q.optionsJson || '[]'
    const arr = typeof raw === 'string' ? JSON.parse(raw || '[]') : raw
    return Array.isArray(arr) ? arr : []
  } catch {
    return []
  }
}

function optLetter(i, type, opt) {
  if (type === 'judge') return String(opt)
  return String.fromCharCode(65 + i)
}

function displayOpt(opt, type) {
  return type === 'judge' ? opt : opt
}

function isAnswered(q) {
  if (q.type === 'multi') return (multi[q.id] || []).length > 0
  return String(answers[q.id] || '').trim().length > 0
}

function setQRef(idx, el) {
  if (el) qRefs.value[idx] = el
}

function scrollTo(idx) {
  focusIdx.value = idx
  const el = qRefs.value[idx]
  if (el?.$el) el.$el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  else if (el?.scrollIntoView) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

async function load() {
  const id = route.params.id
  const res = await http.get(`/api/exam/attempts/${id}/questions`)
  const payload = res.data?.data || res.data || {}
  if (Array.isArray(payload)) {
    questions.value = payload
    attempt.value = { id, paperId: payload[0]?.paperId, mode: 'exam' }
  } else {
    questions.value = payload.questions || []
    attempt.value = payload.attempt || { id, paperId: questions.value[0]?.paperId, mode: 'exam' }
    durationMin.value = Number(payload.durationMin) || 0
  }
  for (const q of questions.value) {
    if (q.type === 'multi') multi[q.id] = []
    else answers[q.id] = ''
  }
}

async function submit() {
  posting.value = true
  try {
    const payload = questions.value.map((q) => {
      let text = answers[q.id] || ''
      if (q.type === 'multi') text = (multi[q.id] || []).slice().sort().join(',')
      return { questionId: q.id, answerText: text }
    })
    const res = await http.post(`/api/exam/attempts/${route.params.id}/submit`, { answers: payload })
    result.value = res.data?.data || res.data || {}
    submitted.value = true
    ElMessage.success('已交卷')
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '交卷失败')
  } finally {
    posting.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 1rem; }
.hero-row { display: flex; justify-content: space-between; gap: 12px; align-items: flex-start; flex-wrap: wrap; }
.exam-cd {
  font-size: 15px;
  font-weight: 700;
  color: var(--portal-accent, #0b6e75);
  padding: 6px 12px;
  border-radius: 8px;
  background: color-mix(in srgb, var(--portal-accent, #0b6e75) 10%, transparent);
}
.list { display: grid; gap: 0.85rem; }
.item { padding: 1rem; }
.stem { margin-bottom: 0.65rem; font-weight: 600; }
.opts { display: grid; gap: 0.35rem; }
.result { padding: 1.25rem; }
</style>
