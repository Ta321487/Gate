<template>
  <div>
    <section class="hero">
      <h1>计票公示</h1>
      <p class="muted">查看各候选人得票与选票明细。</p>
    </section>
    <el-select v-model="campaignId" placeholder="评选活动" style="width: 280px" @change="load">
      <el-option v-for="c in campaigns" :key="c.id" :label="c.title" :value="c.id" />
    </el-select>
    <el-table :data="results" stripe style="margin-top: 1rem">
      <el-table-column prop="name" label="候选人" />
      <el-table-column prop="votes" label="得票" width="100" />
      <el-table-column prop="intro" label="简介" />
    </el-table>
    <h3 style="margin-top: 1.5rem">选票明细</h3>
    <el-table :data="ballots" stripe>
      <el-table-column prop="username" label="投票人" />
      <el-table-column prop="candidateName" label="候选人" />
      <el-table-column prop="createdAt" label="时间" />
    </el-table>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import http from '../../api/http'

const campaigns = ref([])
const campaignId = ref(null)
const results = ref([])
const ballots = ref([])

async function loadCampaigns() {
  const res = await http.get('/api/vote/campaigns')
  campaigns.value = res.data?.data || res.data || []
  if (!campaignId.value && campaigns.value.length) {
    campaignId.value = campaigns.value[0].id
    await load()
  }
}

async function load() {
  if (!campaignId.value) return
  const r = await http.get(`/api/vote/admin/campaigns/${campaignId.value}/results`)
  results.value = r.data?.data || r.data || []
  const b = await http.get(`/api/vote/admin/campaigns/${campaignId.value}/ballots`, {
    params: { page: 1, size: 50 },
  })
  ballots.value = (b.data?.data || b.data || {}).list || []
}

onMounted(loadCampaigns)
</script>

<style scoped>
.hero { margin-bottom: 1rem; }
.muted { color: var(--el-text-color-secondary); }
</style>
