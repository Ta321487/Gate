<template>
  <div>
    <section class="hero">
      <h1>{{ title }}</h1>
      <p>{{ lead }}</p>
      <p v-if="publishReviewOn && publishReviewHint" class="page-hint">{{ publishReviewHint }}</p>
      <p v-if="clearRuleOn && clearRuleLead" class="page-hint">{{ clearRuleLead }}</p>
      <p v-if="clearRuleOn && clearRuleBody" class="page-hint">{{ clearRuleTitle }}：{{ clearRuleBody }}</p>
    </section>
    <div class="card bal">
      <div class="ring" :style="{ '--pct': ringPct }">
        <div class="ring-inner">
          <div class="muted">当前余额</div>
          <strong class="num">{{ balance }}</strong>
          <span class="muted">小时</span>
        </div>
      </div>
      <div v-if="thicken.timebankCreditScore || thicken.timebankFreeze" class="meta">
        <p v-if="thicken.timebankCreditScore">
          {{ creditLabel }}：{{ creditScore }}
          <span v-if="creditHint" class="muted"> · {{ creditHint }}</span>
        </p>
        <p v-if="thicken.timebankFreeze">
          {{ frozenLabel }}：{{ frozenHours }} / 可用 {{ availableHours }}
          <span v-if="frozenHint" class="muted"> · {{ frozenHint }}</span>
        </p>
      </div>
    </div>
    <el-card v-if="thicken.timebankSkillCert" class="earn" shadow="never">
      <template #header>{{ skillTagsLabel }}</template>
      <el-form label-width="100px" @submit.prevent>
        <el-form-item :label="skillTagsLabel">
          <el-input v-model="skillTags" :placeholder="skillTagsPlaceholder" />
        </el-form-item>
        <p v-if="Number(skillCertified) === 1" class="muted">{{ skillCertifiedLabel }}</p>
        <p v-else-if="skillCertifiedHint" class="muted">{{ skillCertifiedHint }}</p>
        <el-button type="primary" :loading="skillBusy" @click="saveSkills">保存标签</el-button>
      </el-form>
    </el-card>
    <el-card v-if="thicken.timebankTransfer" class="earn" shadow="never">
      <template #header>{{ transferLabel }}</template>
      <p v-if="transferHint" class="muted">{{ transferHint }}</p>
      <el-form label-width="100px" @submit.prevent>
        <el-form-item :label="transferToLabel" required>
          <el-input v-model="transferTo" maxlength="64" />
        </el-form-item>
        <el-form-item :label="transferHoursLabel" required>
          <el-input-number v-model="transferHours" :min="0.5" :max="100" :step="0.5" />
        </el-form-item>
        <el-button type="primary" :loading="transferBusy" @click="doTransfer">{{ transferLabel }}</el-button>
      </el-form>
    </el-card>
    <el-card class="earn" shadow="never">
      <template #header>登记存入时长</template>
      <p v-if="thicken.timebankSkillAttach && skillAttachHint" class="muted">{{ skillAttachHint }}</p>
      <el-form label-width="100px" @submit.prevent>
        <el-form-item label="服务事项" required>
          <el-select v-model="serviceId" filterable placeholder="选择开放事项" style="width: 100%">
            <el-option
              v-for="s in services"
              :key="s.id"
              :label="s.title"
              :value="s.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="存入小时" required>
          <el-input-number v-model="hours" :min="0.5" :max="100" :step="0.5" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="reason" maxlength="100" placeholder="可选" />
        </el-form-item>
        <el-button type="primary" :loading="busy" @click="earn">确认存入</el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../api/http'
import { getSchema } from '../utils/domainSchema'

const labels = computed(() => getSchema().labels || {})
const thicken = computed(() => getSchema()?.interactThicken || {})
const title = computed(() => labels.value.tbAccountTitle || '我的时长')
const lead = computed(
  () =>
    labels.value.tbAccountLead ||
    '查看志愿时长余额；可对服务事项登记存入，核销须提交申请经审核扣减。',
)
const publishReviewOn = computed(() => !!thicken.value.timebankPublishReview)
const publishReviewHint = computed(() => labels.value.tbPublishReviewHint || '')
const clearRuleOn = computed(() => !!thicken.value.timebankClearRule)
const clearRuleTitle = computed(() => labels.value.tbClearRuleTitle || '时长清零规则')
const clearRuleLead = computed(() => labels.value.tbClearRuleLead || '')
const creditLabel = computed(() => labels.value.tbCreditScoreLabel || '信用分')
const creditHint = computed(() => labels.value.tbCreditScoreHint || '')
const frozenLabel = computed(() => labels.value.tbFrozenHoursLabel || '冻结时长')
const frozenHint = computed(() => labels.value.tbFrozenHoursHint || '')
const skillTagsLabel = computed(() => labels.value.tbSkillTagsLabel || '技能标签')
const skillTagsPlaceholder = computed(
  () => labels.value.tbSkillTagsPlaceholder || '多个标签用逗号分隔',
)
const skillCertifiedLabel = computed(() => labels.value.tbSkillCertifiedLabel || '技能已认证')
const skillCertifiedHint = computed(() => labels.value.tbSkillCertifiedHint || '')
const skillAttachHint = computed(() => labels.value.tbSkillAttachHint || '')
const transferLabel = computed(() => labels.value.tbTransferLabel || '转让时长')
const transferHint = computed(() => labels.value.tbTransferHint || '')
const transferToLabel = computed(() => labels.value.tbTransferToLabel || '对方账号')
const transferHoursLabel = computed(() => labels.value.tbTransferHoursLabel || '转让小时')
const transferDone = computed(() => labels.value.tbTransferDone || '已转让')
const balance = ref('0')
const availableHours = ref('0')
const frozenHours = ref('0')
const creditScore = ref(100)
const skillTags = ref('')
const skillCertified = ref(0)
const clearRuleBody = ref('')
const services = ref([])
const serviceId = ref(null)
const hours = ref(1)
const reason = ref('')
const busy = ref(false)
const skillBusy = ref(false)
const transferBusy = ref(false)
const transferTo = ref('')
const transferHours = ref(1)

/** 相对演示目标的环形进度（目标至少 40 小时，随余额抬升） */
const ringPct = computed(() => {
  const n = Number(balance.value) || 0
  const goal = Math.max(40, Math.ceil(n / 40) * 40 || 40)
  return `${Math.min(100, Math.round((n / goal) * 100))}%`
})

function applyAccount(a) {
  balance.value = a.balanceHours ?? a.balance_hours ?? 0
  availableHours.value = a.availableHours ?? a.available_hours ?? balance.value
  frozenHours.value = a.frozenHours ?? a.frozen_hours ?? 0
  creditScore.value = a.creditScore ?? a.credit_score ?? 100
  skillTags.value = a.skillTags ?? a.skill_tags ?? ''
  skillCertified.value = a.skillCertified ?? a.skill_certified ?? 0
}

async function load() {
  const tasks = [
    http.get('/api/timebank/account'),
    http.get('/api/timebank/services'),
  ]
  if (clearRuleOn.value) tasks.push(http.get('/api/timebank/clear-rule'))
  const [acc, svc, rule] = await Promise.all(tasks)
  applyAccount(acc.data?.data || acc.data || {})
  services.value = svc.data?.data || svc.data || []
  if (rule) {
    const r = rule.data?.data || rule.data || {}
    clearRuleBody.value = r.body || ''
  }
}

async function earn() {
  if (!serviceId.value) {
    ElMessage.warning('请选择服务事项')
    return
  }
  busy.value = true
  try {
    const res = await http.post('/api/timebank/earn', {
      serviceId: serviceId.value,
      hours: hours.value,
      reason: reason.value,
    })
    applyAccount(res.data?.data || res.data || {})
    ElMessage.success('已存入')
    reason.value = ''
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '存入失败')
  } finally {
    busy.value = false
  }
}

async function saveSkills() {
  skillBusy.value = true
  try {
    const res = await http.post('/api/timebank/skills', { skillTags: skillTags.value })
    applyAccount(res.data?.data || res.data || {})
    ElMessage.success('已保存')
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '保存失败')
  } finally {
    skillBusy.value = false
  }
}

async function doTransfer() {
  if (!transferTo.value.trim()) {
    ElMessage.warning(`请填写${transferToLabel.value}`)
    return
  }
  transferBusy.value = true
  try {
    const res = await http.post('/api/timebank/transfer', {
      toUsername: transferTo.value.trim(),
      hours: transferHours.value,
    })
    applyAccount(res.data?.data || res.data || {})
    ElMessage.success(transferDone.value)
    transferTo.value = ''
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '转让失败')
  } finally {
    transferBusy.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 1rem; }
.bal {
  padding: 1.25rem;
  margin-bottom: 1rem;
  display: flex;
  justify-content: center;
}
.ring {
  --pct: 0%;
  width: 148px;
  height: 148px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background:
    radial-gradient(closest-side, var(--portal-surface, #fff) 72%, transparent 73% 100%),
    conic-gradient(var(--portal-accent, #0b6e75) var(--pct), color-mix(in srgb, var(--portal-line, #e2e8f0) 85%, transparent) 0);
}
.ring-inner { text-align: center; }
.num { display: block; font-size: 2rem; line-height: 1.1; margin: 4px 0; }
.muted { color: var(--el-text-color-secondary); font-size: 13px; }
.page-hint { color: var(--el-text-color-secondary); font-size: 13px; margin: 0.25rem 0; }
.meta { margin-top: 0.75rem; text-align: center; }
.earn { max-width: 520px; margin-bottom: 1rem; }
</style>
