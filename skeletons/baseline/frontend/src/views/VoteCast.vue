<template>
  <div>
    <section class="hero">
      <h1>{{ campaign?.title || '投票' }}</h1>
      <p class="muted">{{ campaign?.isbn || '按限票数选择候选人后提交。' }} · 每人限 {{ campaign?.maxVotes || 1 }} 票</p>
    </section>
    <el-checkbox-group v-model="picked" class="cands">
      <label v-for="c in candidates" :key="c.id" class="card cand">
        <el-avatar :size="40" class="cand-av" :src="c.avatarUrl || undefined">
          {{ String(c.name || '?').slice(0, 1) }}
        </el-avatar>
        <div class="cand-body">
          <el-checkbox :label="c.id">{{ c.name }}</el-checkbox>
          <span class="muted">{{ c.intro || '' }}</span>
        </div>
      </label>
    </el-checkbox-group>
    <div class="actions">
      <el-button type="primary" :loading="saving" @click="submit">提交选票</el-button>
      <el-button @click="loadResults">查看公示</el-button>
      <el-button @click="$router.push('/vote/campaigns')">返回</el-button>
    </div>
    <div v-if="results.length" class="results card">
      <h3>结果公示</h3>
      <div v-for="r in results" :key="r.id" class="row">
        <div class="cand-hd">
          <el-avatar :size="32" :src="r.avatarUrl || undefined">{{ String(r.name || '?').slice(0, 1) }}</el-avatar>
          <span>{{ r.name }}</span>
          <strong>{{ r.votes }} 票</strong>
        </div>
        <div class="vote-bar" aria-hidden="true">
          <i :style="{ width: votePct(r) }" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import http from '../api/http'

const route = useRoute()
const router = useRouter()
const campaign = ref(null)
const candidates = ref([])
const picked = ref([])
const results = ref([])
const saving = ref(false)

function votePct(r) {
  const max = Math.max(1, ...results.value.map((x) => Number(x.votes) || 0))
  const n = Number(r?.votes) || 0
  return `${Math.round((n / max) * 100)}%`
}

async function load() {
  const id = route.params.id
  const c = await http.get(`/api/vote/campaigns/${id}`)
  campaign.value = c.data?.data || c.data
  const list = await http.get(`/api/vote/campaigns/${id}/candidates`)
  candidates.value = list.data?.data || list.data || []
  picked.value = []
}

async function loadResults() {
  const res = await http.get(`/api/vote/campaigns/${route.params.id}/results`)
  results.value = res.data?.data || res.data || []
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
  saving.value = true
  try {
    await http.post(`/api/vote/campaigns/${route.params.id}/cast`, { candidateIds: picked.value })
    ElMessage.success('投票成功')
    await loadResults()
    router.push('/vote/mine')
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '投票失败')
  } finally {
    saving.value = false
  }
}

watch(() => route.params.id, load)
onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 1rem; }
.muted { color: var(--el-text-color-secondary); }
.cands { display: grid; gap: 0.75rem; width: 100%; }
.cand { padding: 0.85rem 1rem; display: flex; gap: 0.75rem; align-items: flex-start; }
.cand-av { flex-shrink: 0; }
.cand-body { display: grid; gap: 0.35rem; min-width: 0; }
.actions { margin: 1rem 0; display: flex; gap: 0.5rem; flex-wrap: wrap; }
.results { padding: 1rem; margin-top: 0.5rem; }
.row { padding: 0.5rem 0; border-bottom: 1px solid var(--el-border-color-lighter); }
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
