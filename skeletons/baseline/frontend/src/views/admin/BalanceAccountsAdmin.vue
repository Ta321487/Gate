<template>
  <div>
    <h2>{{ title }}</h2>
    <el-form inline @submit.prevent>
      <el-form-item label="账号">
        <el-input v-model="form.username" placeholder="用户名" style="width: 160px" />
      </el-form-item>
      <el-form-item :label="'增加（' + unit + '）'">
        <el-input-number v-model="form.qty" :min="1" :max="999" />
      </el-form-item>
      <el-button type="primary" @click="credit">调整</el-button>
    </el-form>
    <el-table :data="list" stripe>
      <el-table-column prop="username" label="账号" width="140" />
      <el-table-column label="余额" width="120">
        <template #default="{ row }">{{ row.balance }} {{ row.unitLabel || unit }}</template>
      </el-table-column>
      <el-table-column prop="updatedAt" label="更新时间" width="180" />
    </el-table>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/http'
import { getSchema } from '../../utils/domainSchema'

const labels = computed(() => getSchema().labels || {})
const title = computed(() => labels.value.balanceAccountsTitle || '额度账户')
const unit = computed(() => labels.value.balanceUnit || '次')
const list = ref([])
const form = reactive({ username: '', qty: 1 })

async function load() {
  const res = await http.get('/api/balance/accounts')
  list.value = (res.data && res.data.list) || []
}

async function credit() {
  if (!form.username) {
    ElMessage.warning('请填写账号')
    return
  }
  await http.post('/api/balance/credit', { username: form.username, qty: form.qty, reason: '管理端调整' })
  ElMessage.success('已调整')
  await load()
}

onMounted(load)
</script>
