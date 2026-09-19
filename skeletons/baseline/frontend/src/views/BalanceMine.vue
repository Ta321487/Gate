<template>
  <div>
    <h2>{{ title }}</h2>
    <p class="lead">{{ lead }}</p>
    <el-descriptions v-if="account.username" :column="2" border>
      <el-descriptions-item label="账号">{{ account.username }}</el-descriptions-item>
      <el-descriptions-item label="可用额度">{{ account.balance }} {{ account.unitLabel || unit }}</el-descriptions-item>
    </el-descriptions>
    <el-empty v-else description="暂无额度账户" />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import http from '../api/http'
import { getSchema } from '../utils/domainSchema'

const labels = computed(() => getSchema().labels || {})
const title = computed(() => labels.value.balanceMineTitle || '我的额度')
const unit = computed(() => labels.value.balanceUnit || '次')
const lead = computed(() => labels.value.balanceMineLead || '查看本人可用额度；审批通过时扣减，余额不足将无法通过。')
const account = ref({})

async function load() {
  const res = await http.get('/api/balance/mine')
  account.value = res.data || {}
}

onMounted(load)
</script>
