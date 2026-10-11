<template>
  <div>
    <section class="hero">
      <h1>{{ title }}</h1>
      <p>{{ lead }}</p>
    </section>
    <el-card shadow="never" class="form">
      <el-form label-position="top" @submit.prevent>
        <el-form-item :label="reasonLabel" required>
          <el-input v-model="reason" type="textarea" :rows="3" maxlength="255" show-word-limit />
        </el-form-item>
        <el-button type="primary" :loading="busy" @click="submit">{{ submitLabel }}</el-button>
      </el-form>
    </el-card>
    <el-table :data="list" stripe class="tbl">
      <el-table-column prop="createdAt" label="时间" width="180" />
      <el-table-column prop="reason" label="说明" />
      <el-table-column prop="status" label="状态" width="100" />
      <el-table-column prop="adminRemark" label="处理说明" />
    </el-table>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../api/http'
import { getSchema } from '../utils/domainSchema'

const labels = computed(() => getSchema()?.labels || {})
const title = computed(() => labels.value.tbAppealTitle || '时长申诉')
const lead = computed(() => labels.value.tbAppealLead || '对核销或流水有异议时可提交申诉。')
const reasonLabel = computed(() => labels.value.tbAppealReasonLabel || '申诉说明')
const submitLabel = computed(() => labels.value.tbAppealSubmitLabel || '提交申诉')
const done = computed(() => labels.value.tbAppealDone || '申诉已提交')
const reason = ref('')
const busy = ref(false)
const list = ref([])

async function load() {
  const res = await http.get('/api/timebank/appeal/mine', { params: { page: 1, size: 20 } })
  const data = res.data?.data || res.data || {}
  list.value = data.list || []
}

async function submit() {
  if (!reason.value.trim()) {
    ElMessage.warning(`请填写${reasonLabel.value}`)
    return
  }
  busy.value = true
  try {
    await http.post('/api/timebank/appeal', { reason: reason.value.trim() })
    ElMessage.success(done.value)
    reason.value = ''
    await load()
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '提交失败')
  } finally {
    busy.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 1rem; }
.form { max-width: 560px; margin-bottom: 1rem; }
.tbl { margin-top: 0.5rem; }
</style>
