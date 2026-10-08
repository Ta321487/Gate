<template>
  <div>
    <section class="hero">
      <h1>{{ title }}</h1>
      <p>{{ lead }}</p>
      <p v-if="denyHint" class="hint">{{ denyHint }}</p>
    </section>
    <el-form label-position="top" style="max-width: 480px">
      <el-form-item :label="reasonLabel" required>
        <el-input
          v-model="reason"
          type="textarea"
          :rows="4"
          maxlength="200"
          show-word-limit
          placeholder="请说明情况"
        />
      </el-form-item>
      <el-button type="primary" :loading="saving" @click="submit">提交申诉</el-button>
    </el-form>
    <h3 class="sub">我的申诉</h3>
    <el-table :data="list" stripe>
      <el-table-column prop="reason" label="说明" show-overflow-tooltip />
      <el-table-column prop="status" label="状态" width="120">
        <template #default="{ row }">{{ statusText(row.status) }}</template>
      </el-table-column>
      <el-table-column prop="createdAt" label="提交时间" width="180" />
    </el-table>
    <div v-if="!list.length" class="empty">暂无申诉记录</div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/http'
import { getSchema } from '../../utils/domainSchema'

const labels = computed(() => getSchema().labels || {})
const title = computed(() => labels.value.reserveBlacklistAppealTitle || '黑名单申诉')
const lead = computed(
  () => labels.value.reserveBlacklistAppealLead || '若被限制预约，可在此说明情况并提交申诉。',
)
const reasonLabel = computed(
  () => labels.value.reserveBlacklistAppealReasonLabel || '申诉说明',
)
const denyHint = computed(() => labels.value.reserveBlacklistDenyMessage || '')
const reason = ref('')
const list = ref([])
const saving = ref(false)

function statusText(st) {
  if (st === 'pending') return '处理中'
  if (st === 'approved') return '已通过'
  if (st === 'rejected') return '已驳回'
  return st || '—'
}

async function load() {
  const res = await http.get('/api/reserve/blacklist/appeals')
  list.value = res.data || []
}

async function submit() {
  const r = (reason.value || '').trim()
  if (!r) {
    ElMessage.warning('请填写申诉说明')
    return
  }
  saving.value = true
  try {
    await http.post('/api/reserve/blacklist/appeals', { reason: r })
    ElMessage.success('已提交')
    reason.value = ''
    await load()
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 16px; }
.hero h1 { margin: 0 0 6px; font-size: 22px; }
.hero p { margin: 0; color: var(--el-text-color-secondary); }
.sub { margin-top: 28px; margin-bottom: 8px; font-size: 16px; }
.empty { color: var(--el-text-color-secondary); padding: 12px 0; }
</style>
