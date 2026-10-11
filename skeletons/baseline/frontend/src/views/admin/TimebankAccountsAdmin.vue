<template>
  <div>
    <h2>时长账户</h2>
    <el-card class="adjust" shadow="never">
      <template #header>调整存入</template>
      <el-form inline @submit.prevent>
        <el-form-item label="用户名">
          <el-input v-model="form.username" style="width: 140px" />
        </el-form-item>
        <el-form-item label="小时">
          <el-input-number v-model="form.hours" :min="0.5" :max="500" :step="0.5" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="form.reason" style="width: 180px" />
        </el-form-item>
        <el-button type="primary" :loading="busy" @click="earn">存入</el-button>
      </el-form>
    </el-card>
    <el-card v-if="freezeOn" class="adjust" shadow="never">
      <template #header>{{ freezeAction }} / {{ unfreezeAction }}</template>
      <p v-if="frozenHint" class="hint">{{ frozenHint }}</p>
      <el-form inline @submit.prevent>
        <el-form-item label="用户名">
          <el-input v-model="freezeForm.username" style="width: 140px" />
        </el-form-item>
        <el-form-item label="小时">
          <el-input-number v-model="freezeForm.hours" :min="0.5" :max="500" :step="0.5" />
        </el-form-item>
        <el-button type="warning" :loading="freezeBusy" @click="doFreeze(true)">{{ freezeAction }}</el-button>
        <el-button :loading="freezeBusy" @click="doFreeze(false)">{{ unfreezeAction }}</el-button>
      </el-form>
    </el-card>
    <el-card v-if="skillOn" class="adjust" shadow="never">
      <template #header>{{ skillCertifiedLabel }}</template>
      <p v-if="skillCertifiedHint" class="hint">{{ skillCertifiedHint }}</p>
      <el-form inline @submit.prevent>
        <el-form-item label="用户名">
          <el-input v-model="skillForm.username" style="width: 140px" />
        </el-form-item>
        <el-form-item :label="skillTagsLabel">
          <el-input v-model="skillForm.skillTags" :placeholder="skillTagsPlaceholder" style="width: 220px" />
        </el-form-item>
        <el-form-item :label="skillCertifiedLabel">
          <el-switch v-model="skillForm.skillCertified" />
        </el-form-item>
        <el-button type="primary" :loading="skillBusy" @click="saveSkills">保存</el-button>
      </el-form>
    </el-card>
    <el-card v-if="clearRuleOn" class="adjust" shadow="never">
      <template #header>{{ clearRuleTitle }}</template>
      <p v-if="clearRuleLead" class="hint">{{ clearRuleLead }}</p>
      <el-input v-model="clearRuleBody" type="textarea" :rows="3" maxlength="512" show-word-limit />
      <el-button class="mt" type="primary" :loading="clearBusy" @click="saveClearRule">{{ clearRuleSaveLabel }}</el-button>
    </el-card>
    <el-table :data="list" stripe>
      <el-table-column prop="username" label="用户" width="120" />
      <el-table-column prop="balanceHours" label="余额(小时)" width="110" />
      <el-table-column v-if="freezeOn" prop="frozenHours" :label="frozenLabel" width="100" />
      <el-table-column v-if="creditOn" prop="creditScore" :label="creditLabel" width="90" />
      <el-table-column v-if="skillOn" prop="skillTags" :label="skillTagsLabel" />
      <el-table-column v-if="skillOn" prop="skillCertified" :label="skillCertifiedLabel" width="100">
        <template #default="{ row }">{{ Number(row.skillCertified) === 1 ? '是' : '否' }}</template>
      </el-table-column>
      <el-table-column prop="updatedAt" label="更新时间" width="180" />
    </el-table>
    <el-pagination
      v-if="total > size"
      class="pager"
      layout="prev, pager, next"
      :total="total"
      :page-size="size"
      v-model:current-page="page"
      @current-change="load"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/http'
import { getSchema } from '../../utils/domainSchema'

const labels = computed(() => getSchema()?.labels || {})
const thicken = computed(() => getSchema()?.interactThicken || {})
const freezeOn = computed(() => !!thicken.value.timebankFreeze)
const skillOn = computed(() => !!thicken.value.timebankSkillCert)
const creditOn = computed(() => !!thicken.value.timebankCreditScore)
const clearRuleOn = computed(() => !!thicken.value.timebankClearRule)
const freezeAction = computed(() => labels.value.tbFreezeAction || '冻结时长')
const unfreezeAction = computed(() => labels.value.tbUnfreezeAction || '解冻')
const frozenLabel = computed(() => labels.value.tbFrozenHoursLabel || '冻结时长')
const frozenHint = computed(() => labels.value.tbFrozenHoursHint || '')
const creditLabel = computed(() => labels.value.tbCreditScoreLabel || '信用分')
const skillTagsLabel = computed(() => labels.value.tbSkillTagsLabel || '技能标签')
const skillTagsPlaceholder = computed(
  () => labels.value.tbSkillTagsPlaceholder || '多个标签用逗号分隔',
)
const skillCertifiedLabel = computed(() => labels.value.tbSkillCertifiedLabel || '技能已认证')
const skillCertifiedHint = computed(() => labels.value.tbSkillCertifiedHint || '')
const clearRuleTitle = computed(() => labels.value.tbClearRuleTitle || '时长清零规则')
const clearRuleLead = computed(() => labels.value.tbClearRuleLead || '')
const clearRuleSaveLabel = computed(() => labels.value.tbClearRuleSaveLabel || '保存清零说明')

const list = ref([])
const total = ref(0)
const page = ref(1)
const size = 20
const busy = ref(false)
const freezeBusy = ref(false)
const skillBusy = ref(false)
const clearBusy = ref(false)
const clearRuleBody = ref('')
const form = reactive({ username: 'user', hours: 1, reason: '管理端调整' })
const freezeForm = reactive({ username: 'user', hours: 1 })
const skillForm = reactive({ username: 'user', skillTags: '', skillCertified: false })

async function load() {
  const res = await http.get('/api/timebank/admin/accounts', { params: { page: page.value, size } })
  const data = res.data?.data || res.data || {}
  list.value = data.list || []
  total.value = data.total || 0
}

async function loadClearRule() {
  if (!clearRuleOn.value) return
  const res = await http.get('/api/timebank/clear-rule')
  const data = res.data?.data || res.data || {}
  clearRuleBody.value = data.body || ''
}

async function earn() {
  if (!form.username) {
    ElMessage.warning('请填写用户名')
    return
  }
  busy.value = true
  try {
    await http.post('/api/timebank/admin/earn', { ...form })
    ElMessage.success('已存入')
    await load()
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '失败')
  } finally {
    busy.value = false
  }
}

async function doFreeze(freeze) {
  if (!freezeForm.username) {
    ElMessage.warning('请填写用户名')
    return
  }
  freezeBusy.value = true
  try {
    await http.post('/api/timebank/admin/freeze', {
      username: freezeForm.username,
      hours: freezeForm.hours,
      action: freeze ? 'freeze' : 'unfreeze',
    })
    ElMessage.success(freeze ? '已冻结' : '已解冻')
    await load()
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '失败')
  } finally {
    freezeBusy.value = false
  }
}

async function saveSkills() {
  if (!skillForm.username) {
    ElMessage.warning('请填写用户名')
    return
  }
  skillBusy.value = true
  try {
    await http.post('/api/timebank/admin/skills', { ...skillForm })
    ElMessage.success('已保存')
    await load()
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '失败')
  } finally {
    skillBusy.value = false
  }
}

async function saveClearRule() {
  clearBusy.value = true
  try {
    await http.post('/api/timebank/admin/clear-rule', { body: clearRuleBody.value })
    ElMessage.success('已保存')
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '失败')
  } finally {
    clearBusy.value = false
  }
}

watch(page, load)
onMounted(async () => {
  await load()
  await loadClearRule()
})
</script>

<style scoped>
.adjust { margin: 1rem 0; }
.pager { margin-top: 1rem; }
.hint { color: var(--el-text-color-secondary); font-size: 13px; margin-bottom: 0.5rem; }
.mt { margin-top: 0.75rem; }
</style>
