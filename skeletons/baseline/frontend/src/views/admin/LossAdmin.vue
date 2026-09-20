<template>
  <div>
    <p class="hint">通过后按不超过上限的金额记入余额。</p>
    <div class="toolbar">
      <span>开放申请</span>
      <el-switch v-model="enabled" />
      <span>单笔上限</span>
      <el-input-number v-model="capYuan" :min="0" :precision="2" :step="1" />
      <el-button type="primary" @click="save">保存</el-button>
      <el-button @click="load">刷新</el-button>
    </div>
    <el-table :data="list" stripe>
      <el-table-column prop="username" label="买家" width="100" />
      <el-table-column prop="orderId" label="订单" width="90" />
      <el-table-column prop="amountYuan" label="申请金额" width="110" />
      <el-table-column prop="paidYuan" label="已退" width="90" />
      <el-table-column prop="reason" label="原因" min-width="160" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">{{ statusText(row.status) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="140">
        <template #default="{ row }">
          <el-button v-if="row.status === 'pending'" link type="primary" @click="pass(row)">通过</el-button>
          <el-button v-if="row.status === 'pending'" link type="danger" @click="openReject(row)">驳回</el-button>
        </template>
      </el-table-column>
    </el-table>
    <p v-if="!list.length" class="empty">还没有赔付申请。</p>
    <el-dialog v-model="visible" title="驳回" width="420px">
      <el-form label-width="88px">
        <el-form-item label="驳回原因" required>
          <el-input v-model="reason" type="textarea" maxlength="200" placeholder="填写驳回原因" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="reject">驳回</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/http'

const enabled = ref(false)
const capYuan = ref(0)
const list = ref([])
const visible = ref(false)
const reason = ref('')
const currentId = ref(0)
const STATUS = { pending: '待处理', approved: '已通过', rejected: '已驳回' }

function statusText(v) { return STATUS[v] || v || '' }

async function load() {
  const pol = await http.get('/api/weigh/policy')
  const data = pol.data || {}
  enabled.value = Number(data.enabled) === 1 || data.enabled === true
  capYuan.value = Number(data.capYuan) || 0
  const res = await http.get('/api/weigh/claims')
  list.value = res.data || []
}

async function save() {
  await http.post('/api/weigh/policy', { enabled: enabled.value, capYuan: capYuan.value })
  ElMessage.success('已保存')
  await load()
}

async function pass(row) {
  await http.post('/api/weigh/pass', { id: row.id })
  ElMessage.success('已通过')
  await load()
}

function openReject(row) {
  currentId.value = row.id
  reason.value = ''
  visible.value = true
}

async function reject() {
  if (!String(reason.value || '').trim()) {
    ElMessage.warning('请填写驳回原因')
    return
  }
  await http.post('/api/weigh/reject', { id: currentId.value, reason: reason.value })
  ElMessage.success('已驳回')
  visible.value = false
  await load()
}

onMounted(load)
</script>

<style scoped>
.hint, .empty { color: var(--el-text-color-secondary); margin: 0 0 12px; }
.toolbar { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
</style>
