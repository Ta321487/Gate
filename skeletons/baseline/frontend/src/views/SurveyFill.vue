<template>
  <div>
    <section class="hero">
      <h1>{{ form?.title || '填写问卷' }}</h1>
    </section>
    <div class="list">
      <article v-for="(q, idx) in questions" :key="q.id" class="card item">
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
        <el-input v-else v-model="answers[q.id]" type="textarea" :rows="3" />
      </article>
      <el-button type="primary" :loading="posting" @click="submit">提交</el-button>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import http from '../api/http'

const route = useRoute()
const router = useRouter()
const form = ref(null)
const questions = ref([])
const answers = reactive({})
const multi = reactive({})
const posting = ref(false)

function parseOpts(q) {
  try {
    const arr = JSON.parse(q.optionsJson || '[]')
    return Array.isArray(arr) ? arr : []
  } catch {
    return []
  }
}

async function load() {
  const id = route.params.id
  const forms = await http.get('/api/survey/forms')
  const all = forms.data?.data || forms.data || []
  form.value = all.find((f) => String(f.id) === String(id)) || { id, title: '问卷' }
  const res = await http.get(`/api/survey/forms/${id}/questions`)
  questions.value = res.data?.data || res.data || []
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
    await http.post(`/api/survey/forms/${route.params.id}/submit`, { answers: payload })
    ElMessage.success('已提交')
    router.push('/survey/mine')
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
</style>
