<template>
  <div>
    <p class="hint">单笔上限 {{ capYuan }} 元。通过后记入余额。</p>
    <el-form v-if="open" label-width="88px" class="form">
      <el-form-item label="订单" required>
        <el-select v-model="form.orderId" placeholder="请选择" style="width: 100%">
          <el-option v-for="row in orders" :key="row.id" :label="`#${row.id} ${row.status}`" :value="row.id" />
        </el-select>
        <p v-if="!orders.length" class="empty">还没有可申请的订单。</p>
      </el-form-item>
      <el-form-item label="金额" required>
        <el-input-number v-model="form.amountYuan" :min="0.01" :precision="2" :step="1" />
      </el-form-item>
      <el-form-item label="原因" required>
        <el-input v-model="form.reason" type="textarea" maxlength="200" placeholder="例如：到货短少" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="submit">提交</el-button>
      </el-form-item>
    </el-form>
    <p v-else class="empty">暂时不能申请损耗赔付。</p>
    <el-table :data="claims" stripe>
      <el-table-column prop="orderId" label="订单" width="90" />
      <el-table-column prop="amountYuan" label="申请金额" width="110" />
      <el-table-column prop="paidYuan" label="已退" width="90" />
      <el-table-column prop="reason" label="原因" min-width="160" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">{{ statusText(row.status) }}</template>
      </el-table-column>
    </el-table>
    <p v-if="!claims.length" class="empty">还没有赔付申请。</p>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/http'

const open = ref(false)
const capYuan = ref(0)
const claims = ref([])
const orders = ref([])
const form = reactive({ orderId: null, amountYuan: 1, reason: '' })
const STATUS = { pending: '待处理', approved: '已通过', rejected: '已驳回' }

function statusText(v) { return STATUS[v] || v || '' }

async function load() {
  const mine = await http.get('/api/weigh/mine')
  const data = mine.data || {}
  open.value = !!data.enabled
  capYuan.value = Number(data.capYuan) || 0
  claims.value = data.claims || []
  const res = await http.get('/api/orders', { params: { page: 1, size: 50 } })
  orders.value = (res.data?.list || []).filter((row) => row.status !== 'cancelled' && row.status !== 'pending')
}

async function submit() {
  if (!form.orderId) {
    ElMessage.warning('请选择订单')
    return
  }
  if (!(Number(form.amountYuan) > 0)) {
    ElMessage.warning('请填写金额')
    return
  }
  if (!String(form.reason || '').trim()) {
    ElMessage.warning('请填写原因')
    return
  }
  await http.post('/api/weigh/claims', { ...form })
  ElMessage.success('已提交')
  form.reason = ''
  await load()
}

onMounted(load)
</script>

<style scoped>
.hint, .empty { color: var(--el-text-color-secondary); margin: 0 0 12px; }
.form { max-width: 520px; }
</style>
