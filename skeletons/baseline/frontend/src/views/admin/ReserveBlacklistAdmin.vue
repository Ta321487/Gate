<template>
  <div>
    <h2>{{ title }}</h2>
    <p class="lead">{{ lead }}</p>
    <el-form inline @submit.prevent>
      <el-form-item label="账号">
        <el-input v-model="form.username" maxlength="64" placeholder="禁止预约的用户名" style="width: 200px" />
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

    <h3 class="sub">申诉处理</h3>
    <el-table :data="appeals" stripe>
      <el-table-column prop="username" label="账号" width="140" />
      <el-table-column prop="reason" label="申诉说明" show-overflow-tooltip />
      <el-table-column prop="status" label="状态" width="100" />
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <template v-if="row.status === 'pending'">
            <el-button link type="primary" @click="resolve(row, true)">通过</el-button>
            <el-button link type="danger" @click="resolve(row, false)">驳回</el-button>
          </template>
          <span v-else>—</span>
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
const title = computed(() => labels.value.reserveBlacklistTitle || '预约黑名单')
const lead = computed(
  () => labels.value.reserveBlacklistLead || '维护禁止预约的账号；名单内用户提交预约时将被拒绝。',
)
const list = ref([])
const appeals = ref([])
const form = reactive({ username: '', reason: '' })

async function load() {
  const res = await http.get('/api/reserve/blacklist')
  list.value = res.data || []
  const ap = await http.get('/api/reserve/blacklist/appeals')
  appeals.value = ap.data || []
}

async function add() {
  const username = (form.username || '').trim()
  if (!username) {
    ElMessage.warning('请填写账号')
    return
  }
  await http.post('/api/reserve/blacklist', { username, reason: (form.reason || '').trim() })
  ElMessage.success('已加入')
  form.username = ''
  form.reason = ''
  await load()
}

async function clear(row) {
  await http.post(`/api/reserve/blacklist/${row.id}/clear`)
  ElMessage.success('已移除')
  await load()
}

async function resolve(row, approve) {
  await http.post(`/api/reserve/blacklist/appeals/${row.id}/resolve`, { approve })
  ElMessage.success(approve ? '已通过并移出名单' : '已驳回')
  await load()
}

onMounted(load)
</script>

<style scoped>
.lead { color: var(--el-text-color-secondary); margin-bottom: 12px; }
.sub { margin-top: 24px; margin-bottom: 8px; font-size: 16px; }
</style>
