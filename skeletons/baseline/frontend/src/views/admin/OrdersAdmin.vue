<template>
  <div>
    <div class="toolbar">
      <el-select v-model="status" clearable placeholder="全部状态" style="width:140px" @change="load">
        <el-option v-for="(lab, key) in states" :key="key" :label="lab" :value="key" />
      </el-select>
      <el-button type="primary" @click="load">查询</el-button>
      <el-button :disabled="!list.length" @click="exportCsv">导出 CSV</el-button>
    </div>
    <el-table :data="list" stripe>
      <el-table-column prop="id" label="编号" width="80" />
      <el-table-column :label="userLabel" width="120">
        <template #default="{ row }">{{ personLabel(row) }}</template>
      </el-table-column>
      <el-table-column prop="totalYuan" label="金额" width="90" />
      <el-table-column :label="fulfillLabel" min-width="160" show-overflow-tooltip>
        <template #default="{ row }">
          <span v-if="row.deliveryType">{{ row.deliveryType }} · </span>
          <span v-if="row.addressLine || row.receiverName">
            {{ row.receiverName }} {{ row.receiverPhone }} {{ row.addressLine }}
          </span>
          <span v-if="isFood && row.tasteNote"> / 口味:{{ row.tasteNote }}</span>
          <span v-if="!row.addressLine && !(isFood && row.tasteNote) && !row.deliveryType">—</span>
        </template>
      </el-table-column>
      <el-table-column :label="shipLabel" min-width="120" show-overflow-tooltip>
        <template #default="{ row }">
          <template v-if="isFood">
            <span v-if="row.pickupCode">取餐码:{{ row.pickupCode }}</span>
            <span v-else>—</span>
          </template>
          <template v-else>
            <span v-if="row.trackingNo">单号:{{ row.trackingNo }}</span>
            <span v-else>—</span>
          </template>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="110">
        <template #default="{ row }">{{ states[row.status] || row.status }}</template>
      </el-table-column>
      <el-table-column prop="remark" label="备注" min-width="120" show-overflow-tooltip>
        <template #default="{ row }">{{ row.remark || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="showLoyaltyCols" label="优惠" width="90">
        <template #default="{ row }">
          <span v-if="Number(row.discountYuan) > 0">¥{{ row.discountYuan }}</span>
          <span v-else>—</span>
        </template>
      </el-table-column>
      <el-table-column v-if="showLoyaltyCols" label="获积分" width="80">
        <template #default="{ row }">{{ Number(row.pointsEarned) > 0 ? row.pointsEarned : '—' }}</template>
      </el-table-column>
      <el-table-column label="售后" width="100">
        <template #default="{ row }">
          <span v-if="row.refundStatus">{{ refundLabel(row.refundStatus) }}</span>
          <span v-else>—</span>
        </template>
      </el-table-column>
      <el-table-column label="明细" min-width="200">
        <template #default="{ row }">
          {{ (row.lines || []).map((x) => `${x.title}×${x.qty}`).join('；') }}
        </template>
      </el-table-column>
      <el-table-column prop="createdAt" label="下单时间" width="170" />
      <el-table-column label="操作" width="280" fixed="right">
        <template #default="{ row }">
          <el-button v-if="row.status === 'pending'" link type="primary" @click="act(row, 'confirm')">确认</el-button>
          <el-button
            v-if="row.status === 'pending' || row.status === 'confirmed'"
            link
            type="primary"
            @click="act(row, 'ship')"
          >{{ shipVerb }}</el-button>
          <el-button
            v-if="['pending', 'confirmed', 'shipped'].includes(row.status)"
            link
            type="success"
            @click="act(row, 'complete')"
          >完成</el-button>
          <el-button
            v-if="row.status === 'pending' || row.status === 'confirmed'"
            link
            type="danger"
            @click="act(row, 'cancel')"
          >取消</el-button>
          <el-button
            v-if="row.refundStatus === 'pending'"
            link
            type="success"
            @click="decideRefund(row, true)"
          >通过售后</el-button>
          <el-button
            v-if="row.refundStatus === 'pending'"
            link
            type="danger"
            @click="decideRefund(row, false)"
          >驳回售后</el-button>
        </template>
      </el-table-column>
    </el-table>
    <div class="pager">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="size"
        background
        layout="total, prev, pager, next"
        :total="total"
        @current-change="load"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'
import { hasTrait, getSchema, isPointsEnabled, isSpendDiscountEnabled, personLabel } from '../../utils/domainSchema.js'
import { downloadCsv } from '../../utils/csvDownload.js'

const order = computed(() => getSchema()?.entities?.order || {})
const states = computed(() => order.value.states || {})
const userLabel = computed(() => getSchema()?.roles?.user?.label || '用户')
const isFood = computed(() => hasTrait('food'))
const showLoyaltyCols = computed(() => isPointsEnabled() || isSpendDiscountEnabled())
const fulfillLabel = computed(() => (isFood.value ? '配送 / 口味' : '收货信息'))
const shipLabel = computed(() => (isFood.value ? '取餐码' : '物流单号'))
const shipVerb = computed(() => {
  if (order.value.verbs?.ship) return order.value.verbs.ship
  return isFood.value ? '出餐' : '发货'
})
const list = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const status = ref(null)

async function load() {
  const res = await http.get('/api/orders', {
    params: { page: page.value, size: size.value, status: status.value || undefined },
  })
  list.value = res.data?.list || []
  total.value = res.data?.total || 0
}

async function act(row, action) {
  let body = {}
  if (action === 'ship') {
    const food = isFood.value
    const { value } = await ElMessageBox.prompt(
      food ? '可填取餐码（留空自动生成）' : '请填写物流单号（可留空）',
      shipVerb.value,
      { inputPlaceholder: food ? '取餐码' : '物流单号', inputValue: '' },
    ).catch(() => ({ value: null }))
    if (value === null) return
    body = food ? { pickupCode: String(value || '').trim() } : { trackingNo: String(value || '').trim() }
  }
  await http.post(`/api/orders/${row.id}/${action}`, body)
  ElMessage.success('已更新')
  load()
}

function refundLabel(st) {
  return ({ pending: '待审', approved: '已通过', rejected: '已驳回' }[st] || st)
}

async function decideRefund(row, pass) {
  let note = ''
  if (!pass) {
    const { value } = await ElMessageBox.prompt('驳回说明（可选）', '驳回售后', {
      inputPlaceholder: '原因',
    }).catch(() => ({ value: null }))
    if (value === null) return
    note = String(value || '').trim()
  } else {
    await ElMessageBox.confirm(`通过订单 #${row.id} 售后？将回补库存并退演示余额。`, '通过售后')
  }
  await http.post(`/api/orders/${row.id}/refund`, { pass, note })
  ElMessage.success(pass ? '已通过售后' : '已驳回')
  load()
}

async function exportCsv() {
  const res = await http.get('/api/orders', {
    params: { page: 1, size: 5000, status: status.value || undefined },
  })
  const rows = res.data?.list || []
  if (!rows.length) {
    ElMessage.warning('当前筛选无数据可导出')
    return
  }
  const headers = isFood.value
    ? ['编号', userLabel.value, '金额', '配送方式', '地址', '口味', '取餐码', '状态', '备注', '优惠', '获积分', '明细', '下单时间']
    : ['编号', userLabel.value, '金额', '配送方式', '收货信息', '物流单号', '状态', '备注', '优惠', '获积分', '明细', '下单时间']
  const data = rows.map((row) => {
    const base = [
      row.id,
      personLabel(row, ''),
      row.totalYuan,
      row.deliveryType || '',
      [row.receiverName, row.receiverPhone, row.addressLine].filter(Boolean).join(' '),
    ]
    const tail = [
      states.value[row.status] || row.status,
      row.remark || '',
      Number(row.discountYuan) > 0 ? row.discountYuan : '',
      Number(row.pointsEarned) > 0 ? row.pointsEarned : '',
      (row.lines || []).map((x) => `${x.title}×${x.qty}`).join('；'),
      row.createdAt,
    ]
    if (isFood.value) {
      return [...base, row.tasteNote || '', row.pickupCode || '', ...tail]
    }
    return [...base, row.trackingNo || '', ...tail]
  })
  downloadCsv(`orders_${status.value || 'all'}_${Date.now()}.csv`, headers, data)
  ElMessage.success(`已导出 ${rows.length} 条（UTF-8，可用 Excel 直接打开）`)
}

onMounted(load)
</script>

<style scoped>
.toolbar { margin-bottom: 12px; display: flex; gap: 8px; }
.pager { margin-top: 16px; display: flex; justify-content: flex-end; }
</style>
