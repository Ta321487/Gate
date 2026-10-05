<template>
  <div class="wrap">
    <h1>{{ pageTitle }}</h1>
    <p class="lead">{{ pageLead }}</p>
    <el-form @submit.prevent="query">
      <el-form-item :label="codeLabel">
        <el-input v-model="code" maxlength="32" clearable placeholder="请输入查询码" style="max-width:360px" />
      </el-form-item>
      <el-button type="primary" :loading="loading" @click="query">查询</el-button>
    </el-form>
    <p v-if="resultText" class="result" :class="{ ok: found, miss: found === false }">{{ resultText }}</p>
    <p v-if="found && detail" class="sub">
      <template v-if="detail.itemTitle">{{ pageTitle }}：{{ detail.itemTitle }}</template>
      <template v-if="detail.status"> · {{ statusLabel }} {{ detail.status }}</template>
      <template v-if="detail.approveAt"> · {{ atLabel }} {{ detail.approveAt }}</template>
      <template v-if="detail.certIssueNo"> · {{ issueNoLabel }} {{ detail.certIssueNo }}</template>
    </p>
    <p v-if="found && deepenHint" class="sub">{{ deepenHint }}</p>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../api/http'
import { getSchema } from '../utils/domainSchema.js'

const labels = computed(() => getSchema()?.labels || {})
const pageTitle = computed(() => labels.value.certVerifyPageTitle || '证明真伪查询')
const pageLead = computed(() => labels.value.certVerifyPageLead || '请输入查询码，核对证明是否由本系统开具。')
const codeLabel = computed(() => labels.value.certVerifyCodeLabel || '真伪查询码')
const okText = computed(() => labels.value.certVerifyOkText || '查得该证明，信息属实。')
const missText = computed(() => labels.value.certVerifyMissText || '未查到对应证明，请核对查询码。')
const statusLabel = computed(() => labels.value.certVerifyStatusLabel || '办理状态')
const atLabel = computed(() => labels.value.certVerifyAtLabel || '办结时间')
const issueNoLabel = computed(() => labels.value.certVerifyIssueNoLabel || '开具流水号')
const deepenHint = computed(() => labels.value.certVerifyPageDeepenHint || '')

const code = ref('')
const loading = ref(false)
const found = ref(null)
const detail = ref(null)
const resultText = computed(() => {
  if (found.value === true) return okText.value
  if (found.value === false) return missText.value
  return ''
})

async function query() {
  const c = (code.value || '').trim()
  if (!c) {
    ElMessage.warning(`请填写${codeLabel.value}`)
    return
  }
  loading.value = true
  found.value = null
  detail.value = null
  try {
    const res = await http.get('/api/tickets/verify', { params: { code: c } })
    const data = res.data?.data ?? res.data ?? {}
    found.value = !!data.found
    detail.value = data.found ? data : null
  } catch (e) {
    found.value = false
    ElMessage.error(e?.response?.data?.message || '查询失败，请稍后重试')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.wrap {
  max-width: 640px;
  margin: 48px auto;
  padding: 0 20px;
}
h1 {
  margin: 0 0 8px;
  font-size: 1.6rem;
}
.lead {
  color: #666;
  margin: 0 0 24px;
}
.result {
  margin-top: 20px;
  font-size: 1.05rem;
}
.result.ok {
  color: #067a3e;
}
.result.miss {
  color: #a33;
}
.sub {
  color: #666;
  margin-top: 8px;
}
</style>
