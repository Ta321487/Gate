<template>
  <div>
    <section class="hero no-print">
      <h1>{{ title }}</h1>
      <p>{{ lead }}</p>
      <el-button type="primary" :loading="loading" @click="load">刷新</el-button>
      <el-button v-if="payload" type="success" @click="printCert">{{ printLabel }}</el-button>
      <el-button @click="$router.push('/exam/attempts')">返回成绩</el-button>
    </section>
    <p v-if="error" class="error no-print">{{ error }}</p>
    <article v-if="payload" class="cert card" id="exam-cert">
      <h2>{{ title }}</h2>
      <p class="line"><span>{{ nameLabel }}</span>{{ payload.displayName || payload.username }}</p>
      <p class="line"><span>{{ paperLabel }}</span>{{ payload.paperTitle }}</p>
      <p class="line">
        <span>{{ scoreLabel }}</span>{{ payload.score }} / {{ payload.totalScore }}
      </p>
      <p class="line"><span>{{ passLabel }}</span>{{ payload.passScore }}%</p>
      <p class="line"><span>{{ dateLabel }}</span>{{ payload.submittedAt || '—' }}</p>
      <p class="foot">本页仅供本系统内证明，非权威认证。</p>
    </article>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import http from '../api/http'
import { getSchema } from '../utils/domainSchema'

const route = useRoute()
const labels = computed(() => getSchema()?.labels || {})
const title = computed(() => labels.value.examCertificateTitle || '考试及格证书')
const lead = computed(() => labels.value.examCertificateLead || '')
const printLabel = computed(() => labels.value.examCertificatePrintLabel || '打印证书')
const nameLabel = computed(() => labels.value.examCertificateNameLabel || '考生')
const paperLabel = computed(() => labels.value.examCertificatePaperLabel || '试卷')
const scoreLabel = computed(() => labels.value.examCertificateScoreLabel || '成绩')
const passLabel = computed(() => labels.value.examCertificatePassLabel || '及格线')
const dateLabel = computed(() => labels.value.examCertificateDateLabel || '发证日期')
const deny = computed(() => labels.value.examCertificateDeny || '未达到及格线，暂无证书。')
const payload = ref(null)
const error = ref('')
const loading = ref(false)

async function load() {
  loading.value = true
  error.value = ''
  payload.value = null
  try {
    const res = await http.get(`/api/exam/attempts/${route.params.id}/certificate`)
    payload.value = res.data?.data || res.data || null
  } catch (e) {
    error.value = e?.response?.data?.message || e.message || deny.value
  } finally {
    loading.value = false
  }
}

function printCert() {
  window.print()
}

onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 1rem; display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center; }
.hero h1 { width: 100%; margin: 0; }
.hero p { width: 100%; margin: 0; color: var(--el-text-color-secondary); }
.error { color: var(--el-color-danger); }
.cert {
  max-width: 640px;
  margin: 1.5rem auto;
  padding: 2rem 2.25rem;
  border: 2px solid var(--portal-accent, #0b6e75);
  text-align: center;
}
.cert h2 { margin: 0 0 1.25rem; letter-spacing: 0.08em; }
.line { margin: 0.65rem 0; font-size: 1.05rem; }
.line span { color: var(--el-text-color-secondary); margin-right: 0.5rem; }
.foot { margin-top: 1.5rem; font-size: 0.85rem; color: var(--el-text-color-secondary); }
@media print {
  .no-print { display: none !important; }
  .cert { border-color: #000; box-shadow: none; }
}
</style>
