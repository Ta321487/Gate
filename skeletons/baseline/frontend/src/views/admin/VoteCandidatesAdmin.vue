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
      <el-input v-model="draft.name" placeholder="姓名" style="width: 140px" />
      <el-input v-model="draft.intro" :placeholder="introLabel" style="width: 200px" />
      <el-input v-model="draft.slogan" :placeholder="sloganPlaceholder" style="width: 200px" />
      <el-input v-model="draft.avatarUrl" :placeholder="avatarLabel + ' URL（可选）'" style="width: 220px" />
      <el-input-number v-model="draft.sortNo" :min="0" />
      <el-button type="primary" @click="create">新增</el-button>
    </div>
    <el-table :data="list" stripe style="margin-top: 1rem">
      <el-table-column :label="avatarLabel" width="72">
        <template #default="{ row }">
          <el-avatar :size="36" :src="row.avatarUrl || undefined">
            {{ String(row.name || '?').slice(0, 1) }}
          </el-avatar>
        </template>
      </el-table-column>
      <el-table-column prop="name" label="姓名" />
      <el-table-column prop="intro" :label="introLabel" />
      <el-table-column prop="slogan" :label="sloganLabel" />
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
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/http'
import { getSchema } from '../../utils/domainSchema'

const labels = computed(() => getSchema()?.labels || {})
const introLabel = computed(() => labels.value.voteIntroLabel || '图文简介')
const sloganLabel = computed(() => labels.value.voteSloganLabel || '拉票文案')
const sloganPlaceholder = computed(() => labels.value.voteSloganPlaceholder || '一句话拉票（选填）')
const avatarLabel = computed(() => labels.value.voteAvatarLabel || '头像')

const campaigns = ref([])
const campaignId = ref(null)
const list = ref([])
const draft = reactive({ name: '', intro: '', slogan: '', sortNo: 0, avatarUrl: '' })

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
  draft.slogan = ''
  draft.avatarUrl = ''
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
