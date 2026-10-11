<template>
  <div>
    <section class="hero">
      <h1>{{ form?.title || '填写问卷' }}</h1>
      <p v-if="form?.anonymous" class="muted">{{ labels.surveyAnonymousHint || '本问卷匿名填写' }}</p>
      <p v-if="draftHint" class="muted">{{ draftHint }}</p>
    </section>
    <div v-if="progressOn && visibleQs.length" class="progress-wrap">
      <div class="progress-meta">
        <span>{{ progressLabel }}</span>
        <span>{{ answeredRequired }} / {{ requiredTotal }}</span>
      </div>
      <el-progress :percentage="progressPct" :stroke-width="10" />
      <p v-if="progressHint" class="muted">{{ progressHint }}</p>
    </div>
    <div class="list">
      <article v-for="(q, idx) in visibleQs" :key="q.id" class="card item">
        <div class="stem">{{ idx + 1 }}. {{ q.stem }} <span v-if="q.required" class="req">*</span></div>
        <el-radio-group v-if="q.type === 'single'" v-model="answers[q.id]">
          <el-radio v-for="(opt, i) in parseOpts(q)" :key="i" :value="String.fromCharCode(65 + i)">
            {{ String.fromCharCode(65 + i) }}. {{ opt }}
          </el-radio>
        </el-radio-group>
        <el-checkbox-group v-else-if="q.type === 'multi'" v-model="multi[q.id]">
          <el-checkbox v-for="(opt, i) in parseOpts(q)" :key="i" :label="String.fromCharCode(65 + i)">
            {{ String.fromCharCode(65 + i) }}. {{ opt }}
          </el-checkbox>
        </el-checkbox-group>
        <div v-else-if="q.type === 'matrix'" class="matrix">
          <table>
            <thead>
              <tr>
                <th></th>
                <th v-for="(opt, i) in parseOpts(q)" :key="i">{{ String.fromCharCode(65 + i) }}. {{ opt }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, ri) in parseRows(q)" :key="ri">
                <td>{{ row }}</td>
                <td v-for="(opt, i) in parseOpts(q)" :key="i">
                  <el-radio
                    :model-value="matrixAns[q.id]?.[ri]"
                    :value="String.fromCharCode(65 + i)"
                    @change="setMatrix(q.id, ri, String.fromCharCode(65 + i))"
                  />
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <el-input v-else v-model="answers[q.id]" type="textarea" :rows="3" />
      </article>
      <div class="actions">
        <el-button v-if="draftOn" :loading="savingDraft" @click="saveDraft">
          {{ labels.surveyDraftSaveLabel || '保存草稿' }}
        </el-button>
        <el-button type="primary" :loading="posting" @click="submit">提交</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import http from '../api/http'
import { getSchema } from '../utils/domainSchema.js'

const route = useRoute()
const router = useRouter()
const schema = computed(() => getSchema() || {})
const labels = computed(() => schema.value.labels || {})
const thicken = computed(() => schema.value.interactThicken || {})
const progressOn = computed(() => !!thicken.value.surveyAnswerProgress)
const draftOn = computed(() => !!thicken.value.surveyDraft)
const thanksOn = computed(() => !!thicken.value.surveyThanks)
const progressLabel = computed(() => labels.value.surveyProgressLabel || '填写进度')
const progressHint = computed(() => labels.value.surveyProgressHint || '')
const draftHint = computed(() => (draftOn.value ? labels.value.surveyDraftHint || '' : ''))

const form = ref(null)
const questions = ref([])
const answers = reactive({})
const multi = reactive({})
const matrixAns = reactive({})
const posting = ref(false)
const savingDraft = ref(false)

function parseOpts(q) {
  try {
    const arr = JSON.parse(q.optionsJson || '[]')
    return Array.isArray(arr) ? arr : []
  } catch {
    return []
  }
}

function parseRows(q) {
  try {
    const arr = JSON.parse(q.matrixRows || '[]')
    return Array.isArray(arr) ? arr : []
  } catch {
    return []
  }
}

function setMatrix(qid, ri, letter) {
  if (!matrixAns[qid]) matrixAns[qid] = []
  matrixAns[qid][ri] = letter
}

function letterOf(q) {
  if (q.type === 'multi') return (multi[q.id] || []).slice().sort().join(',')
  if (q.type === 'matrix') return (matrixAns[q.id] || []).join('|')
  return answers[q.id] || ''
}

const visibleQs = computed(() => {
  const ordered = [...questions.value].sort((a, b) => (a.sortNo || 0) - (b.sortNo || 0))
  const out = []
  let jumpTo = null
  let ended = false
  for (const q of ordered) {
    if (ended) break
    if (jumpTo != null && (q.sortNo || 0) < jumpTo) continue
    jumpTo = null
    if (q.showWhenQid && q.showWhenLabel) {
      const dep = questions.value.find((x) => String(x.id) === String(q.showWhenQid))
      if (dep) {
        const ans = String(letterOf(dep)).toUpperCase()
        if (!ans.includes(String(q.showWhenLabel).toUpperCase())) continue
      }
    }
    out.push(q)
    if (q.skipWhenLabel != null && q.skipWhenLabel !== '' && q.skipToSort != null) {
      const ans = String(letterOf(q)).toUpperCase()
      if (ans.includes(String(q.skipWhenLabel).toUpperCase())) {
        const st = Number(q.skipToSort)
        if (st < 0) ended = true
        else jumpTo = st
      }
    }
  }
  return out
})

const requiredTotal = computed(() => visibleQs.value.filter((q) => q.required).length)
const answeredRequired = computed(() =>
  visibleQs.value.filter((q) => q.required && String(letterOf(q)).trim()).length,
)
const progressPct = computed(() =>
  requiredTotal.value ? Math.min(100, Math.round((answeredRequired.value / requiredTotal.value) * 100)) : 0,
)

function buildPayload() {
  return visibleQs.value.map((q) => ({
    questionId: q.id,
    answerText: letterOf(q),
  }))
}

async function load() {
  const id = route.params.id
  try {
    const fr = await http.get(`/api/survey/forms/${id}`)
    form.value = fr.data?.data || fr.data || { id, title: '问卷' }
  } catch {
    form.value = { id, title: '问卷' }
  }
  const res = await http.get(`/api/survey/forms/${id}/questions`)
  questions.value = res.data?.data || res.data || []
  for (const q of questions.value) {
    if (q.type === 'multi') multi[q.id] = []
    else if (q.type === 'matrix') matrixAns[q.id] = []
    else answers[q.id] = ''
  }
  if (draftOn.value) {
    try {
      const dr = await http.get(`/api/survey/forms/${id}/draft`)
      const raw = dr.data?.data || dr.data || {}
      const arr = raw.answers || []
      if (Array.isArray(arr)) {
        for (const a of arr) {
          const q = questions.value.find((x) => String(x.id) === String(a.questionId))
          if (!q) continue
          const text = a.answerText || ''
          if (q.type === 'multi') multi[q.id] = text ? text.split(',') : []
          else if (q.type === 'matrix') matrixAns[q.id] = text ? text.split('|') : []
          else answers[q.id] = text
        }
      }
    } catch {
      /* ignore */
    }
  }
}

async function saveDraft() {
  savingDraft.value = true
  try {
    await http.put(`/api/survey/forms/${route.params.id}/draft`, {
      answers: buildPayload(),
    })
    ElMessage.success(labels.value.surveyDraftSaved || '草稿已保存')
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '保存失败')
  } finally {
    savingDraft.value = false
  }
}

async function submit() {
  posting.value = true
  try {
    await http.post(`/api/survey/forms/${route.params.id}/submit`, { answers: buildPayload() })
    ElMessage.success('已提交')
    if (thanksOn.value) router.push(`/survey/thanks/${route.params.id}`)
    else router.push('/survey/mine')
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '提交失败')
  } finally {
    posting.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 1rem; }
.list { display: grid; gap: 0.85rem; }
.item { padding: 1rem; }
.stem { margin-bottom: 0.5rem; font-weight: 600; }
.req { color: var(--el-color-danger); }
.muted { color: var(--el-text-color-secondary); font-size: 0.9rem; }
.progress-wrap { margin: 0.75rem 0 1rem; max-width: 420px; }
.progress-meta { display: flex; justify-content: space-between; margin-bottom: 0.35rem; font-size: 0.9rem; }
.actions { display: flex; gap: 0.75rem; flex-wrap: wrap; }
.matrix { overflow-x: auto; }
.matrix table { border-collapse: collapse; width: 100%; font-size: 0.9rem; }
.matrix th, .matrix td { border: 1px solid var(--el-border-color); padding: 6px 8px; text-align: center; }
.matrix td:first-child, .matrix th:first-child { text-align: left; }
</style>
