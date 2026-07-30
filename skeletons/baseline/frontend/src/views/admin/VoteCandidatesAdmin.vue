<template>
  <div>
    <section class="hero">
      <h1>候选人管理</h1>
      <p class="muted">先选评选活动，再维护候选人。</p>
    </section>
    <el-select v-model="campaignId" placeholder="评选活动" style="width: 280px" @change="loadCands">
      <el-option v-for="c in campaigns" :key="c.id" :label="c.title" :value="c.id" />
    </el-select>
    <div class="toolbar" v-if="campaignId">
      <el-input v-model="draft.name" placeholder="姓名" style="width: 160px" />
      <el-input v-model="draft.intro" placeholder="简介" style="width: 240px" />
      <el-input-number v-model="draft.sortNo" :min="0" />
      <el-button type="primary" @click="create">新增</el-button>
    </div>
    <el-table :data="list" stripe style="margin-top: 1rem">
      <el-table-column prop="name" label="姓名" />
      <el-table-column prop="intro" label="简介" />
      <el-table-column prop="sortNo" label="排序" width="80" />
      <el-table-column label="操作" width="100">
        <template #default="{ row }">
          <el-button link type="danger" @click="remove(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/http'

const campaigns = ref([])
const campaignId = ref(null)
const list = ref([])
const draft = reactive({ name: '', intro: '', sortNo: 0 })

async function loadCampaigns() {
  const res = await http.get('/api/vote/campaigns')
  campaigns.value = res.data?.data || res.data || []
  if (!campaignId.value && campaigns.value.length) {
    campaignId.value = campaigns.value[0].id
    await loadCands()
  }
}

async function loadCands() {
  if (!campaignId.value) return
  const res = await http.get(`/api/vote/admin/campaigns/${campaignId.value}/candidates`, {
    params: { page: 1, size: 50 },
  })
  list.value = (res.data?.data || res.data || {}).list || []
}

async function create() {
  await http.post('/api/vote/admin/candidates', { ...draft, campaignId: campaignId.value })
  ElMessage.success('已新增')
  draft.name = ''
  draft.intro = ''
  await loadCands()
}

async function remove(id) {
  await http.delete(`/api/vote/admin/candidates/${id}`)
  ElMessage.success('已删除')
  await loadCands()
}

onMounted(loadCampaigns)
</script>

<style scoped>
.hero { margin-bottom: 1rem; }
.muted { color: var(--el-text-color-secondary); }
.toolbar { margin-top: 1rem; display: flex; gap: 0.5rem; flex-wrap: wrap; }
</style>
