<template>
  <div>
    <section class="hero">
      <h1>{{ campaign?.title || '投票' }}</h1>
      <p class="muted">{{ campaign?.isbn || '按限票数选择候选人后提交。' }} · 每人限 {{ campaign?.maxVotes || 1 }} 票</p>
    </section>
    <el-checkbox-group v-model="picked" class="cands">
      <label v-for="c in candidates" :key="c.id" class="card cand">
        <el-checkbox :label="c.id">{{ c.name }}</el-checkbox>
        <span class="muted">{{ c.intro || '' }}</span>
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
        <span>{{ r.name }}</span>
        <strong>{{ r.votes }} 票</strong>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import http from '../utils/http'

const route = useRoute()
const router = useRouter()
const campaign = ref(null)
const candidates = ref([])
const picked = ref([])
const results = ref([])
const saving = ref(false)

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
.cand { padding: 0.85rem 1rem; display: grid; gap: 0.35rem; }
.actions { margin: 1rem 0; display: flex; gap: 0.5rem; flex-wrap: wrap; }
.results { padding: 1rem; margin-top: 0.5rem; }
.row { display: flex; justify-content: space-between; padding: 0.35rem 0; border-bottom: 1px solid var(--el-border-color-lighter); }
</style>
