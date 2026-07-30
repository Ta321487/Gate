<template>
  <div>
    <section class="hero">
      <h1>{{ title }}</h1>
      <p>{{ lead }}</p>
    </section>
    <div class="card bal">
      <div class="muted">当前余额</div>
      <strong class="num">{{ balance }}</strong>
      <span class="muted">小时</span>
    </div>
    <el-card class="earn" shadow="never">
      <template #header>登记存入时长</template>
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
const title = computed(() => labels.value.tbAccountTitle || '我的时长')
const lead = computed(
  () =>
    labels.value.tbAccountLead ||
    '查看志愿时长余额；可对服务事项登记存入，核销须提交申请经审核扣减。',
)
const balance = ref('0')
const services = ref([])
const serviceId = ref(null)
const hours = ref(1)
const reason = ref('')
const busy = ref(false)

async function load() {
  const [acc, svc] = await Promise.all([
    http.get('/api/timebank/account'),
    http.get('/api/timebank/services'),
  ])
  const a = acc.data?.data || acc.data || {}
  balance.value = a.balanceHours ?? a.balance_hours ?? 0
  services.value = svc.data?.data || svc.data || []
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
    const a = res.data?.data || res.data || {}
    balance.value = a.balanceHours ?? a.balance_hours ?? balance.value
    ElMessage.success('已存入')
    reason.value = ''
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '存入失败')
  } finally {
    busy.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 1rem; }
.bal { padding: 1rem 1.25rem; margin-bottom: 1rem; display: flex; align-items: baseline; gap: 0.5rem; }
.num { font-size: 2rem; }
.muted { color: var(--el-text-color-secondary); }
.earn { max-width: 520px; }
</style>
