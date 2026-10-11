<template>
  <div>
    <section class="hero">
      <h1>{{ pageTitle }}</h1>
      <p>{{ pageLead }}</p>
    </section>
    <div class="list">
      <article v-for="p in list" :key="p.id" class="card item">
        <div class="meta">
          <strong>{{ p.title }}</strong>
          <span v-if="p.durationMin">限时 {{ p.durationMin }} 分钟</span>
          <span v-if="passScoreOn && p.passScore">{{ passScoreLabel }} {{ p.passScore }}%</span>
          <span v-if="p.hasEntryCode">需入场口令</span>
        </div>
        <div class="actions">
          <el-button type="primary" @click="openStart(p)">开始考试</el-button>
        </div>
      </article>
    </div>
    <div v-if="!list.length" class="empty">暂无已发布试卷。</div>

    <el-dialog v-model="codeVisible" :title="entryCodeLabel" width="400px">
      <p v-if="entryCodeHint" class="hint">{{ entryCodeHint }}</p>
      <el-form label-width="90px" @submit.prevent>
        <el-form-item :label="entryCodeLabel" required>
          <el-input
            v-model="entryCode"
            :placeholder="entryCodePlaceholder"
            maxlength="64"
            show-password
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="codeVisible = false">取消</el-button>
        <el-button type="primary" :loading="starting" @click="confirmStart">进入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import http from '../api/http'
import { getSchema } from '../utils/domainSchema'

const router = useRouter()
const list = ref([])
const codeVisible = ref(false)
const entryCode = ref('')
const starting = ref(false)
const pendingPaper = ref(null)
const schema = computed(() => getSchema() || {})
const labels = computed(() => schema.value.labels || {})
const thicken = computed(() => schema.value.interactThicken || {})
const pageTitle = computed(() => labels.value.examPapersTitle || '在线考试')
const pageLead = computed(
  () => labels.value.examPapersLead || '选择已发布试卷开考；客观题交卷自动判分，主观题由教师阅卷。',
)
const passScoreOn = computed(() => !!thicken.value.examPassScore)
const passScoreLabel = computed(() => labels.value.examPassScoreLabel || '及格线')
const entryCodeOn = computed(() => !!thicken.value.examEntryCode)
const entryCodeLabel = computed(() => labels.value.examEntryCodeLabel || '入场口令')
const entryCodePlaceholder = computed(
  () => labels.value.examEntryCodePlaceholder || '请输入监考老师提供的口令',
)
const entryCodeHint = computed(() => labels.value.examEntryCodeHint || '')
const entryCodeRequired = computed(() => labels.value.examEntryCodeRequired || '请输入入场口令')
const entryCodeDeny = computed(() => labels.value.examEntryCodeDeny || '入场口令不正确')
const lateEnterDeny = computed(() => labels.value.examLateEnterDeny || '')
const lockAfterSubmitDeny = computed(() => labels.value.examLockAfterSubmitDeny || '')

async function load() {
  const res = await http.get('/api/exam/papers')
  list.value = res.data?.data || res.data || []
}

function openStart(paper) {
  pendingPaper.value = paper
  if (entryCodeOn.value && paper.hasEntryCode) {
    entryCode.value = ''
    codeVisible.value = true
    return
  }
  start(paper.id, '')
}

async function confirmStart() {
  if (!entryCode.value.trim()) {
    ElMessage.warning(entryCodeRequired.value)
    return
  }
  await start(pendingPaper.value.id, entryCode.value.trim())
}

async function start(paperId, code) {
  starting.value = true
  try {
    const body = { mode: 'exam' }
    if (code) body.entryCode = code
    const res = await http.post(`/api/exam/papers/${paperId}/start`, body)
    const attempt = res.data?.data || res.data
    codeVisible.value = false
    router.push(`/exam/take/${attempt.id}`)
  } catch (e) {
    const msg = e?.response?.data?.message || e.message || '无法开考'
    if (msg.includes('口令') && entryCodeDeny.value) ElMessage.error(entryCodeDeny.value)
    else if (msg.includes('迟到') && lateEnterDeny.value) ElMessage.error(lateEnterDeny.value)
    else if (msg.includes('再考') && lockAfterSubmitDeny.value) ElMessage.error(lockAfterSubmitDeny.value)
    else ElMessage.error(msg)
  } finally {
    starting.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 1.25rem; }
.hero h1 { margin: 0 0 0.35rem; font-size: 1.5rem; }
.hero p { margin: 0; color: var(--el-text-color-secondary); }
.list { display: grid; gap: 0.75rem; }
.item { padding: 1rem 1.1rem; }
.meta { display: flex; gap: 1rem; align-items: baseline; margin-bottom: 0.75rem; flex-wrap: wrap; }
.actions { display: flex; gap: 0.5rem; }
.empty { color: var(--el-text-color-secondary); padding: 2rem 0; }
.hint { color: var(--el-text-color-secondary); font-size: 13px; margin: 0 0 0.75rem; }
</style>
