<template>
  <div>
    <section class="hero">
      <div class="hero-row">
        <div>
          <h1>答题中</h1>
          <p v-if="attempt">
            试卷 #{{ attempt.paperId }} · {{ attempt.mode === 'practice' ? '练习' : '考试' }}
          </p>
          <p v-if="blurOn && blurWarn" class="blur-warn">{{ blurWarn }}</p>
          <p v-if="blurOn" class="blur-count">{{ blurCountLabel }}：{{ blurCount }}</p>
        </div>
        <div
          v-if="showTimer"
          class="exam-cd"
          :class="{ 'cd-urgent': isUrgentCountdown(remainSec, 120) }"
        >
          剩余 {{ formatCountdownClock(remainSec) }}
        </div>
      </div>
      <div v-if="progressOn && !submitted" class="progress-wrap">
        <div class="progress-meta">
          <span>{{ progressLabel }}</span>
          <span>{{ answeredCount }} / {{ questions.length }}</span>
        </div>
        <el-progress :percentage="progressPct" :stroke-width="10" />
        <p v-if="progressHint" class="muted">{{ progressHint }}</p>
      </div>
    </section>
    <div v-if="submitted" class="card result">
      <template v-if="result.practice">
        <h2>{{ practiceNoScoreHint }}</h2>
        <p v-if="result.selfCheckTotal != null">
          自测参考 {{ result.selfCheckScore }} / {{ result.selfCheckTotal }}
        </p>
      </template>
      <template v-else-if="result.status === 'reviewing'">
        <h2>已交卷，主观题待教务主管阅卷</h2>
        <p>{{ examObjectiveGradedLead }}</p>
        <p v-if="examObjectiveGradeHint" class="grade-hint">{{ examObjectiveGradeHint }}</p>
      </template>
      <h2 v-else>得分 {{ result.score }} / {{ result.totalScore }}</h2>
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
            <el-radio
              v-for="(opt, i) in parseOpts(q)"
              :key="i"
              :value="optValue(opt, i, q.type)"
            >
              {{ optLabel(opt, i, q.type) }}. {{ optContent(opt, q.type) }}
            </el-radio>
          </el-radio-group>
        </div>
        <div v-else-if="q.type === 'multi'" class="opts">
          <el-checkbox-group v-model="multi[q.id]">
            <el-checkbox
              v-for="(opt, i) in parseOpts(q)"
              :key="i"
              :label="optValue(opt, i, 'multi')"
            >
              {{ optLabel(opt, i, 'multi') }}. {{ optContent(opt, 'multi') }}
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
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import http from '../api/http'
import { parseDateMs } from '../utils/dates.js'
import { getSchema } from '../utils/domainSchema.js'
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
const blurCount = ref(0)
const { nowMs } = useNowTick()
const schema = computed(() => getSchema() || {})
const labels = computed(() => schema.value.labels || {})
const thicken = computed(() => schema.value.interactThicken || {})
const progressOn = computed(() => !!thicken.value.examAnswerProgress)
const blurOn = computed(() => !!thicken.value.examBlurWarn)
const progressLabel = computed(() => labels.value.examProgressLabel || '答题进度')
const progressHint = computed(() => labels.value.examProgressHint || '')
const blurWarn = computed(() => labels.value.examBlurWarnLead || '')
const blurCountLabel = computed(() => labels.value.examBlurCountLabel || '切屏次数')
const practiceNoScoreHint = computed(
  () => labels.value.examPracticeNoScoreHint || '练习交卷仅供自测，不记正式得分。',
)
const examObjectiveGradedLead = computed(
  () => labels.value.examObjectiveGradedLead || '客观题已自动判分。总分在全部主观题阅完后公布。',
)
const examObjectiveGradeHint = computed(() => labels.value.examObjectiveGradeHint || '')

const answeredCount = computed(() => questions.value.filter((q) => isAnswered(q)).length)
const progressPct = computed(() => {
  if (!questions.value.length) return 0
  return Math.round((answeredCount.value / questions.value.length) * 100)
})

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

function optValue(opt, i, type) {
  if (type === 'judge') return typeof opt === 'object' ? String(opt.content ?? opt.label ?? '') : String(opt)
  if (typeof opt === 'object' && opt?.label) return String(opt.label)
  return String.fromCharCode(65 + i)
}

function optLabel(opt, i, type) {
  if (type === 'judge') return typeof opt === 'object' ? String(opt.content ?? '') : String(opt)
  if (typeof opt === 'object' && opt?.label) return String(opt.label)
  return String.fromCharCode(65 + i)
}

function optContent(opt, type) {
  if (type === 'judge') return typeof opt === 'object' ? String(opt.content ?? '') : String(opt)
  if (typeof opt === 'object') return String(opt.content ?? '')
  return String(opt)
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

async function onBlur() {
  if (!blurOn.value || submitted.value) return
  try {
    const res = await http.post(`/api/exam/attempts/${route.params.id}/blur`)
    const data = res.data?.data || res.data || {}
    blurCount.value = Number(data.blurCount ?? data.blur_count ?? blurCount.value + 1) || 0
  } catch {
    blurCount.value += 1
  }
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
    blurCount.value = Number(attempt.value?.blurCount ?? attempt.value?.blur_count ?? 0) || 0
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

onMounted(() => {
  load()
  if (typeof window !== 'undefined') {
    window.addEventListener('blur', onBlur)
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) onBlur()
    })
  }
})

onUnmounted(() => {
  if (typeof window !== 'undefined') {
    window.removeEventListener('blur', onBlur)
  }
})
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
.progress-wrap { margin-top: 0.75rem; max-width: 420px; }
.progress-meta { display: flex; justify-content: space-between; margin-bottom: 0.35rem; font-size: 0.9rem; }
.blur-warn { color: var(--el-color-warning); font-size: 0.9rem; margin: 0.35rem 0 0; }
.blur-count { color: var(--el-text-color-secondary); font-size: 0.85rem; margin: 0.2rem 0 0; }
.muted { color: var(--el-text-color-secondary); font-size: 0.85rem; margin: 0.35rem 0 0; }
.list { display: grid; gap: 0.85rem; }
.item { padding: 1rem; }
.stem { margin-bottom: 0.65rem; font-weight: 600; }
.opts { display: grid; gap: 0.35rem; }
.result { padding: 1.25rem; }
.grade-hint { margin-top: 0.5rem; color: var(--portal-muted, #64748b); font-size: 0.9rem; line-height: 1.45; }
.answer-sheet { display: flex; flex-wrap: wrap; gap: 0.35rem; margin-bottom: 0.5rem; }
.q-dot {
  width: 2rem; height: 2rem; border-radius: 6px; border: 1px solid var(--el-border-color);
  background: #fff; cursor: pointer;
}
.q-dot.filled { background: color-mix(in srgb, var(--portal-accent, #0b6e75) 18%, #fff); }
.q-dot.current { border-color: var(--portal-accent, #0b6e75); font-weight: 700; }
</style>
