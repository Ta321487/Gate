<template>
  <div>
    <h2>{{ title }}</h2>
    <p class="lead">{{ lead }}</p>
    <el-form inline @submit.prevent>
      <el-form-item label="账号">
        <el-input v-model="form.username" maxlength="64" placeholder="禁止报名的用户名" style="width: 200px" />
      </el-form-item>
      <el-form-item label="原因">
        <el-input v-model="form.reason" maxlength="120" placeholder="选填" style="width: 220px" />
      </el-form-item>
      <el-button type="primary" @click="add">加入黑名单</el-button>
    </el-form>
    <el-table :data="list" stripe>
      <el-table-column prop="username" label="账号" width="160" />
      <el-table-column prop="reason" label="原因" show-overflow-tooltip />
      <el-table-column label="操作" width="100">
        <template #default="{ row }">
          <el-button link type="danger" @click="clear(row)">移除</el-button>
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

const labels = computed(() => getSchema().labels || {})
const title = computed(() => labels.value.applyBlacklistTitle || '报名黑名单')
const lead = computed(
  () => labels.value.applyBlacklistLead || '维护禁止报名的账号；名单内用户提交报名时将被拒绝。',
)
const list = ref([])
const form = reactive({ username: '', reason: '' })

async function load() {
  const res = await http.get('/api/apply/blacklist')
  list.value = res.data || []
}

async function add() {
  const username = (form.username || '').trim()
  if (!username) {
    ElMessage.warning('请填写账号')
    return
  }
  await http.post('/api/apply/blacklist', { username, reason: (form.reason || '').trim() })
  ElMessage.success('已加入')
  form.username = ''
  form.reason = ''
  await load()
}

async function clear(row) {
  await http.post(`/api/apply/blacklist/${row.id}/clear`)
  ElMessage.success('已移除')
  await load()
}

onMounted(load)
</script>
