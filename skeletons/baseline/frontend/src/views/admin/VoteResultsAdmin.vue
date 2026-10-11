<template>
  <div>
    <section class="hero">
      <h1>计票公示</h1>
      <p class="muted">查看各候选人得票与选票明细，并可导出结果。</p>
      <p v-if="exportHint" class="muted">{{ exportHint }}</p>
      <p v-if="ipHintLead" class="muted">{{ ipHintLead }}</p>
    </section>
    <el-select v-model="campaignId" placeholder="评选活动" style="width: 280px" @change="onCampaign">
      <el-option v-for="c in campaigns" :key="c.id" :label="c.title" :value="c.id" />
    </el-select>
    <el-button
      v-if="campaignId"
      type="primary"
      style="margin-left: 0.5rem"
      :loading="exporting"
      :title="exportHint"
      @click="exportCsv"
    >{{ exportLabel }}</el-button>

    <el-card v-if="campaignId" class="settings" shadow="never">
      <template #header>{{ settingsTitle }}</template>
      <el-form label-width="140px" class="settings-form">
        <el-form-item :label="labels.voteAnonymousLabel || '匿名计票明细'">
          <el-switch v-model="settings.anonymous" />
          <span class="hint">{{ labels.voteAnonymousHint }}</span>
        </el-form-item>
        <el-form-item :label="labels.voteAllowAbstainLabel || '允许弃权'">
          <el-switch v-model="settings.allowAbstain" />
        </el-form-item>
        <el-form-item :label="labels.voteRequireRealNameLabel || '实名后可投'">
          <el-switch v-model="settings.requireRealName" />
        </el-form-item>
        <el-form-item :label="labels.voteDailyLimitLabel || '每人每天限票'">
          <el-input-number v-model="settings.dailyVoteLimit" :min="0" :max="99" />
          <span class="hint">{{ labels.voteDailyLimitHint }}</span>
        </el-form-item>
        <el-form-item :label="labels.votePollSecondsLabel || '结果刷新间隔(秒)'">
          <el-input-number v-model="settings.pollSeconds" :min="0" :max="3600" />
          <span class="hint">{{ labels.votePollHint }}</span>
        </el-form-item>
        <el-form-item :label="labels.voteResultPublishAtLabel || '结果公布时间'">
          <el-date-picker
            v-model="settings.resultsPublishAt"
            type="datetime"
            value-format="YYYY-MM-DD HH:mm:ss"
            clearable
          />
          <span class="hint">{{ labels.voteResultDelayHint }}</span>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="saving" @click="saveSettings">{{ saveLabel }}</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-table :data="results" stripe style="margin-top: 1rem">
      <el-table-column type="index" label="#" width="50" />
      <el-table-column label="头像" width="72">
        <template #default="{ row }">
          <el-avatar :size="36" :src="row.avatarUrl || undefined">
            {{ String(row.name || '?').slice(0, 1) }}
          </el-avatar>
        </template>
      </el-table-column>
      <el-table-column prop="name" label="候选人" />
      <el-table-column prop="votes" label="得票" width="100" />
      <el-table-column prop="intro" :label="labels.voteIntroLabel || '简介'" />
      <el-table-column prop="slogan" :label="labels.voteSloganLabel || '拉票文案'" />
    </el-table>
    <h3 style="margin-top: 1.5rem">选票明细</h3>
    <el-table :data="ballots" stripe>
      <el-table-column prop="username" label="投票人" />
      <el-table-column prop="candidateName" label="候选人" />
      <el-table-column prop="clientIp" label="网络地址" width="140" />
      <el-table-column prop="createdAt" label="时间" />
    </el-table>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/http'
import { getSchema } from '../../utils/domainSchema'

const labels = computed(() => getSchema()?.labels || {})
const exportLabel = computed(() => labels.value.voteExportLabel || '导出结果')
const exportHint = computed(() => labels.value.voteExportHint || '')
const ipHintLead = computed(() => labels.value.voteIpHintLead || '')
const settingsTitle = computed(() => labels.value.voteSettingsTitle || '评选规则')
const saveLabel = computed(() => labels.value.voteSettingsSaveLabel || '保存规则')

const campaigns = ref([])
const campaignId = ref(null)
const results = ref([])
const ballots = ref([])
const exporting = ref(false)
const saving = ref(false)
const settings = reactive({
  anonymous: false,
  allowAbstain: false,
  requireRealName: false,
  dailyVoteLimit: 0,
  pollSeconds: 0,
  resultsPublishAt: null,
})

function fillSettings(c) {
  settings.anonymous = !!c?.anonymous
  settings.allowAbstain = !!c?.allowAbstain
  settings.requireRealName = !!c?.requireRealName
  settings.dailyVoteLimit = Number(c?.dailyVoteLimit) || 0
  settings.pollSeconds = Number(c?.pollSeconds) || 0
  settings.resultsPublishAt = c?.resultsPublishAt || null
}

async function loadCampaigns() {
  const res = await http.get('/api/vote/campaigns')
  campaigns.value = res.data?.data || res.data || []
  if (!campaignId.value && campaigns.value.length) {
    campaignId.value = campaigns.value[0].id
    await onCampaign()
  }
}

async function onCampaign() {
  if (!campaignId.value) return
  const detail = await http.get(`/api/vote/campaigns/${campaignId.value}`)
  fillSettings(detail.data?.data || detail.data)
  await load()
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

async function saveSettings() {
  saving.value = true
  try {
    await http.put(`/api/vote/admin/campaigns/${campaignId.value}/settings`, { ...settings })
    ElMessage.success('规则已保存')
    await onCampaign()
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function exportCsv() {
  exporting.value = true
  try {
    const res = await http.get(`/api/vote/admin/campaigns/${campaignId.value}/export`, {
      responseType: 'blob',
    })
    const blob = new Blob([res.data], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `vote_results_${campaignId.value}.csv`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '导出失败')
  } finally {
    exporting.value = false
  }
}

onMounted(loadCampaigns)
</script>

<style scoped>
.hero { margin-bottom: 1rem; }
.muted { color: var(--el-text-color-secondary); }
.settings { margin-top: 1rem; }
.settings-form .hint {
  display: block;
  margin-left: 0.75rem;
  color: var(--el-text-color-secondary);
  font-size: 0.85rem;
}
</style>
