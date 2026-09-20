<template>
  <div>
    <p class="hint">质检通过后才会上架。申请中的提现可以确认打款。</p>
    <div class="toolbar">
      <span>抽成</span>
      <el-input-number v-model="feePercent" :min="0" :max="100" :step="1" :precision="0" />
      <span>%</span>
      <el-button type="primary" @click="saveRate">保存抽成</el-button>
      <el-button @click="load">刷新</el-button>
    </div>
    <el-table :data="items" stripe>
      <el-table-column prop="username" label="寄卖人" width="100" />
      <el-table-column prop="title" label="标题" min-width="140" />
      <el-table-column prop="expectYuan" label="期望价" width="100" />
      <el-table-column prop="conditionNote" label="成色说明" min-width="120" />
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
    <h3>提现</h3>
    <el-table :data="ledgers" stripe>
      <el-table-column prop="username" label="寄卖人" width="100" />
      <el-table-column prop="grossYuan" label="成交额" width="100" />
      <el-table-column prop="payoutYuan" label="应得" width="100" />
      <el-table-column label="提现" width="100">
        <template #default="{ row }">{{ withdrawText(row.withdrawStatus) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="110">
        <template #default="{ row }">
          <el-button v-if="row.withdrawStatus === 'applied'" link type="primary" @click="pay(row)">确认打款</el-button>
        </template>
      </el-table-column>
    </el-table>
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

const feePercent = ref(10)
const items = ref([])
const ledgers = ref([])
const visible = ref(false)
const reason = ref('')
const currentId = ref(0)

const STATUS = { pending: '待质检', rejected: '已驳回', on_sale: '在售', sold: '已售' }
const WITHDRAW = { ready: '可提现', applied: '申请中', paid: '已打款' }

function statusText(v) { return STATUS[v] || v || '' }
function withdrawText(v) { return WITHDRAW[v] || v || '' }

async function load() {
  const rate = await http.get('/api/consigns/rate')
  feePercent.value = Number((rate.data || {}).feePercent) || 0
  const list = await http.get('/api/consigns')
  items.value = list.data || []
  const books = await http.get('/api/consigns/ledgers')
  ledgers.value = books.data || []
}

async function saveRate() {
  await http.post('/api/consigns/rate', { feePercent: feePercent.value })
  ElMessage.success('已保存')
  await load()
}

async function pass(row) {
  await http.post('/api/consigns/pass', { id: row.id })
  ElMessage.success('已上架')
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
  await http.post('/api/consigns/reject', { id: currentId.value, reason: reason.value })
  ElMessage.success('已驳回')
  visible.value = false
  await load()
}

async function pay(row) {
  await http.post('/api/consigns/pay', { id: row.id })
  ElMessage.success('已确认')
  await load()
}

onMounted(load)
</script>

<style scoped>
.hint { color: var(--el-text-color-secondary); margin: 0 0 12px; }
.toolbar { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
h3 { margin: 20px 0 12px; font-size: 16px; }
</style>
