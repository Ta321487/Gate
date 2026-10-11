<template>
  <div>
    <section class="hero">
      <h1>{{ campaign?.title || '投票' }}</h1>
      <p class="muted">
        {{ campaign?.isbn || castLead }} · 每人限 {{ campaign?.maxVotes || 1 }} 票
      </p>
    </section>
    <el-checkbox-group v-model="picked" class="cands" :disabled="abstaining">
      <label v-for="c in candidates" :key="c.id" class="card cand">
        <el-avatar :size="40" class="cand-av" :src="c.avatarUrl || undefined">
          {{ String(c.name || '?').slice(0, 1) }}
        </el-avatar>
        <div class="cand-body">
          <el-checkbox :label="c.id">{{ c.name }}</el-checkbox>
          <span class="muted">{{ c.intro || '' }}</span>
          <span v-if="c.slogan" class="slogan">{{ c.slogan }}</span>
        </div>
      </label>
    </el-checkbox-group>
    <div class="actions">
      <el-button type="primary" :loading="saving" @click="submit">提交选票</el-button>
      <el-button
        v-if="campaign?.allowAbstain"
        :loading="saving"
        @click="submitAbstain"
      >{{ abstainLabel }}</el-button>
      <el-button @click="showResults">查看公示</el-button>
      <el-button @click="$router.push(`/vote/poster/${route.params.id}`)">{{ posterLinkLabel }}</el-button>
      <el-button @click="$router.push('/vote/campaigns')">返回</el-button>
    </div>
    <div v-if="resultsVisible" class="results card">
      <h3>结果公示</h3>
      <p v-if="top3Hint && !resultsDelayed" class="muted">{{ top3Hint }}</p>
      <p v-if="resultsDelayed" class="muted delay-msg">{{ delayMsg }}</p>
      <template v-else>
        <div
          v-for="(r, idx) in results"
          :key="r.id || idx"
          class="row"
          :class="{ top3: idx < 3 }"
        >
          <div class="cand-hd">
            <el-avatar :size="32" :src="r.avatarUrl || undefined">
              {{ String(r.name || '?').slice(0, 1) }}
            </el-avatar>
            <span>{{ r.name }}</span>
            <strong>{{ r.votes }} 票</strong>
          </div>
          <div class="vote-bar" aria-hidden="true">
            <i :style="{ width: votePct(r) }" />
          </div>
        </div>
        <p v-if="!results.length" class="muted">暂无计票数据。</p>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import http from '../api/http'
import { getSchema } from '../utils/domainSchema'

const route = useRoute()
const router = useRouter()
const labels = computed(() => getSchema()?.labels || {})
const castLead = computed(() => labels.value.voteCastLead || '按限票数选择候选人后提交。')
const abstainLabel = computed(() => labels.value.voteAbstainLabel || '弃权')
const posterLinkLabel = computed(() => labels.value.votePosterLinkLabel || '十佳海报')
const delayMsg = computed(
  () => labels.value.voteResultDelayMsg || '结果尚未到公布时间',
)
const top3Hint = computed(() => labels.value.voteTop3Hint || '')
const realNameWarn = computed(
  () =>
    labels.value.voteRealNameWarn ||
    '本评选需实名后投票，请先在资料中填写真实姓名。',
)

const campaign = ref(null)
const candidates = ref([])
const picked = ref([])
const results = ref([])
const resultsVisible = ref(false)
const resultsDelayed = ref(false)
const saving = ref(false)
const abstaining = ref(false)
let pollTimer = null

function votePct(r) {
  const max = Math.max(1, ...results.value.map((x) => Number(x.votes) || 0))
  const n = Number(r?.votes) || 0
  return `${Math.round((n / max) * 100)}%`
}

function stopPoll() {
  if (pollTimer != null) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

function startPoll() {
  stopPoll()
  const sec = Number(campaign.value?.pollSeconds) || 0
  if (!resultsVisible.value || resultsDelayed.value || sec <= 0) return
  pollTimer = setInterval(() => {
    loadResults({ quiet: true })
  }, sec * 1000)
}

async function loadProfileRealName() {
  try {
    const me = await http.get('/api/profile')
    const data = me.data?.data || me.data || {}
    const extras = data.extras || {}
    return String(extras.realName || data.realName || '').trim()
  } catch {
    return ''
  }
}

async function ensureRealNameOk() {
  if (!campaign.value?.requireRealName) return true
  const name = await loadProfileRealName()
  if (name) return true
  ElMessage.warning(realNameWarn.value)
  return false
}

function isDelayError(e) {
  const status = e?.response?.status
  const msg = String(e?.response?.data?.message || e?.message || '')
  if (status === 400 && /延迟|尚未|公布|未到/.test(msg)) return true
  if (/结果尚未|延迟公布|未到公布/.test(msg)) return true
  return false
}

async function load() {
  const id = route.params.id
  const c = await http.get(`/api/vote/campaigns/${id}`)
  campaign.value = c.data?.data || c.data
  const list = await http.get(`/api/vote/campaigns/${id}/candidates`)
  candidates.value = list.data?.data || list.data || []
  picked.value = []
  resultsVisible.value = false
  results.value = []
  resultsDelayed.value = false
  stopPoll()
}

async function loadResults({ quiet = false } = {}) {
  if (campaign.value && campaign.value.resultPublished === false) {
    resultsDelayed.value = true
    results.value = []
    resultsVisible.value = true
    stopPoll()
    return
  }
  try {
    const res = await http.get(`/api/vote/campaigns/${route.params.id}/results`)
    const data = res.data?.data || res.data || []
    results.value = Array.isArray(data) ? data : []
    resultsDelayed.value = false
    resultsVisible.value = true
    startPoll()
  } catch (e) {
    if (isDelayError(e) || campaign.value?.resultPublished === false) {
      resultsDelayed.value = true
      results.value = []
      resultsVisible.value = true
      stopPoll()
      return
    }
    if (!quiet) {
      ElMessage.error(e?.response?.data?.message || e.message || '加载结果失败')
    }
  }
}

function showResults() {
  loadResults()
}

async function doCast(body) {
  if (!(await ensureRealNameOk())) return
  saving.value = true
  try {
    const res = await http.post(`/api/vote/campaigns/${route.params.id}/cast`, body)
    const payload = res.data?.data || res.data || {}
    ElMessage.success(body?.abstain ? '已弃权' : '投票成功')
    const hint = payload.ipHint
    if (hint && typeof hint === 'string') {
      ElMessage.warning(hint)
    }
    await loadResults()
    router.push('/vote/mine')
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '投票失败')
  } finally {
    saving.value = false
    abstaining.value = false
  }
}

async function submit() {
  const max = campaign.value?.maxVotes || 1
  if (!picked.value.length) {
    ElMessage.warning('请选择候选人')
    return
  }
  if (picked.value.length > max) {
    ElMessage.warning(`最多选择 ${max} 人`)
    return
  }
  await doCast({ candidateIds: picked.value })
}

async function submitAbstain() {
  abstaining.value = true
  picked.value = []
  await doCast({ abstain: true })
}

watch(() => route.params.id, load)
watch(
  () => [resultsVisible.value, resultsDelayed.value, campaign.value?.pollSeconds],
  () => {
    if (resultsVisible.value && !resultsDelayed.value) startPoll()
    else stopPoll()
  },
)
onMounted(load)
onUnmounted(stopPoll)
</script>

<style scoped>
.hero { margin-bottom: 1rem; }
.muted { color: var(--el-text-color-secondary); }
.slogan {
  color: var(--portal-accent, var(--el-color-primary));
  font-size: 0.9rem;
  line-height: 1.4;
}
.cands { display: grid; gap: 0.75rem; width: 100%; }
.cand { padding: 0.85rem 1rem; display: flex; gap: 0.75rem; align-items: flex-start; }
.cand-av { flex-shrink: 0; }
.cand-body { display: grid; gap: 0.35rem; min-width: 0; }
.actions { margin: 1rem 0; display: flex; gap: 0.5rem; flex-wrap: wrap; }
.results { padding: 1rem; margin-top: 0.5rem; }
.delay-msg { margin: 0.5rem 0 0; }
.row { padding: 0.5rem 0; border-bottom: 1px solid var(--el-border-color-lighter); }
.row.top3 {
  background: color-mix(in srgb, var(--portal-accent-soft, #e8f2f2) 70%, transparent);
  margin: 0 -0.5rem;
  padding-left: 0.5rem;
  padding-right: 0.5rem;
  border-radius: 6px;
  border-bottom-color: transparent;
}
.cand-hd { display: flex; align-items: center; gap: 10px; }
.cand-hd strong { margin-left: auto; }
.vote-bar {
  margin-top: 6px;
  height: 8px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--portal-line, #e2e8f0) 80%, transparent);
  overflow: hidden;
}
.vote-bar > i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--portal-accent, #0b6e75), color-mix(in srgb, var(--portal-accent, #0b6e75) 55%, #fff));
  transition: width 0.35s ease;
}
</style>
