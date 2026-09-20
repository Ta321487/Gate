<template>
  <div>
    <p class="hint">提交后等待质检。通过后按期望价上架。当前抽成 {{ feePercent }}%。</p>
    <el-form label-width="88px" class="form">
      <el-form-item label="标题" required>
        <el-input v-model="form.title" maxlength="80" placeholder="例如：耳机" />
      </el-form-item>
      <el-form-item label="期望价" required>
        <el-input-number v-model="form.expectYuan" :min="0.01" :precision="2" :step="1" />
      </el-form-item>
      <el-form-item label="成色说明">
        <el-input v-model="form.conditionNote" maxlength="64" placeholder="例如：九成新，轻微使用" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="submit">提交</el-button>
      </el-form-item>
    </el-form>
    <el-table :data="items" stripe>
      <el-table-column prop="title" label="标题" min-width="140" />
      <el-table-column prop="expectYuan" label="期望价" width="100" />
      <el-table-column prop="conditionNote" label="成色说明" min-width="140" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">{{ statusText(row.status) }}</template>
      </el-table-column>
      <el-table-column prop="rejectReason" label="驳回原因" min-width="140" />
    </el-table>
    <p v-if="!items.length" class="empty">还没有寄卖记录。</p>
    <h3>提现</h3>
    <el-table :data="ledgers" stripe>
      <el-table-column prop="grossYuan" label="成交额" width="100" />
      <el-table-column label="抽成" width="80">
        <template #default="{ row }">{{ row.feePercent }}%</template>
      </el-table-column>
      <el-table-column prop="payoutYuan" label="应得" width="100" />
      <el-table-column label="提现" width="100">
        <template #default="{ row }">{{ withdrawText(row.withdrawStatus) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="110">
        <template #default="{ row }">
          <el-button v-if="row.withdrawStatus === 'ready'" link type="primary" @click="withdraw(row)">申请提现</el-button>
        </template>
      </el-table-column>
    </el-table>
    <p v-if="!ledgers.length" class="empty">还没有可提现的成交。</p>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/http'

const feePercent = ref(0)
const items = ref([])
const ledgers = ref([])
const form = reactive({ title: '', expectYuan: 1, conditionNote: '' })

const STATUS = { pending: '待质检', rejected: '已驳回', on_sale: '在售', sold: '已售' }
const WITHDRAW = { ready: '可提现', applied: '申请中', paid: '已打款' }

function statusText(v) { return STATUS[v] || v || '' }
function withdrawText(v) { return WITHDRAW[v] || v || '' }

async function load() {
  const res = await http.get('/api/consigns/mine')
  const data = res.data || {}
  feePercent.value = Number(data.feePercent) || 0
  items.value = data.items || []
  ledgers.value = data.ledgers || []
}

async function submit() {
  if (!String(form.title || '').trim()) {
    ElMessage.warning('请填写标题')
    return
  }
  if (!(Number(form.expectYuan) > 0)) {
    ElMessage.warning('请填写期望价')
    return
  }
  await http.post('/api/consigns', { ...form })
  ElMessage.success('已提交')
  form.title = ''
  form.conditionNote = ''
  await load()
}

async function withdraw(row) {
  await http.post('/api/consigns/withdraw', { id: row.id })
  ElMessage.success('已申请')
  await load()
}

onMounted(load)
</script>

<style scoped>
.hint, .empty { color: var(--el-text-color-secondary); margin: 0 0 12px; }
.form { max-width: 520px; margin-bottom: 16px; }
h3 { margin: 20px 0 12px; font-size: 16px; }
</style>
