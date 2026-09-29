<template>
  <div>
    <h2>{{ title }}</h2>
    <p class="lead">{{ lead }}</p>
    <p v-if="scrapFlowHint" class="hint">{{ scrapFlowHint }}</p>
    <el-form inline class="filter" @submit.prevent>
      <el-form-item label="物资ID">
        <el-input-number v-model="form.itemId" :min="1" controls-position="right" />
      </el-form-item>
      <el-form-item label="类型">
        <el-select v-model="form.moveType" style="width: 110px">
          <el-option label="入库" value="in" />
          <el-option label="出库" value="out" />
          <el-option v-if="scrapOn" label="报废" value="scrap" />
          <el-option v-if="countOn" label="盘点" value="count" />
        </el-select>
      </el-form-item>
      <el-form-item :label="form.moveType === 'count' ? '实盘数量' : '数量'">
        <el-input-number
          v-model="form.qty"
          :min="form.moveType === 'count' ? 0 : 1"
          :max="999999"
          controls-position="right"
        />
      </el-form-item>
      <el-form-item :label="form.moveType === 'scrap' ? '报废原因' : '说明'">
        <el-input
          v-model="form.remark"
          clearable
          :placeholder="remarkPlaceholder"
          style="width: 180px"
        />
      </el-form-item>
      <el-button type="primary" :loading="saving" @click="submit">
        {{ form.moveType === 'scrap' && scrapApproveOn ? '提交报废申请' : '登记过账' }}
      </el-button>
    </el-form>
    <p v-if="countOn && form.moveType === 'count'" class="hint">{{ countHint }}</p>
    <p v-if="countLockedHint" class="hint">{{ countLockedHint }}</p>
    <p v-if="blindHint" class="hint">{{ blindHint }}</p>

    <template v-if="scrapApproveOn">
      <h3 class="sub">{{ scrapPendingTitle }}</h3>
      <el-table :data="scrapList" stripe class="scrap-table">
        <el-table-column prop="createdAt" label="申请时间" width="180" />
        <el-table-column prop="itemId" label="物资ID" width="90" />
        <el-table-column prop="itemTitle" label="物资" min-width="120" />
        <el-table-column prop="qty" label="数量" width="80" />
        <el-table-column prop="reason" label="原因" min-width="140" />
        <el-table-column prop="applicant" label="申请人" width="110" />
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            {{ scrapStatusLabel(row.status) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <template v-if="row.status === 'pending'">
              <el-button link type="success" @click="approveScrap(row)">{{ scrapApproveVerb }}</el-button>
              <el-button link type="danger" @click="rejectScrap(row)">{{ scrapRejectVerb }}</el-button>
            </template>
            <span v-else class="muted">{{ row.handler || '—' }}</span>
          </template>
        </el-table-column>
      </el-table>
    </template>

    <h3 v-if="scrapApproveOn" class="sub">出入库流水</h3>
    <el-table :data="list" stripe>
      <el-table-column prop="createdAt" label="时间" width="180" />
      <el-table-column prop="moveType" label="类型" width="100">
        <template #default="{ row }">
          <StatusChip :tone="stockMoveTone(row.moveType)" :label="typeLabel(row.moveType)" />
        </template>
      </el-table-column>
      <el-table-column prop="itemId" label="物资ID" width="90" />
      <el-table-column prop="itemTitle" label="物资" min-width="140" />
      <el-table-column prop="qty" label="数量" width="80" />
      <el-table-column prop="operator" label="操作人" width="110" />
      <el-table-column prop="remark" label="说明" />
    </el-table>
    <el-pagination
      v-if="total > size"
      class="pager"
      layout="prev, pager, next"
      :total="total"
      :page-size="size"
      v-model:current-page="page"
      @current-change="load"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'
import StatusChip from '../../components/StatusChip.vue'
import { getSchema, hasCap } from '../../utils/domainSchema.js'
import { stockMoveTone } from '../../utils/statusTone.js'

const scrapOn = computed(() => hasCap('stock_scrap'))
const countOn = computed(() => hasCap('stock_count'))
const labels = computed(() => getSchema()?.labels || {})
const scrapApproveOn = computed(() => {
  const opts = getSchema()?.stockScrapOpts || {}
  return !!scrapOn.value && !!opts.approveFlow
})
const scrapFlowHint = computed(() =>
  scrapApproveOn.value ? labels.value.scrapApproveHint || '' : '',
)
const scrapPendingTitle = computed(() => labels.value.scrapPendingTitle || '待审报废单')
const scrapApproveVerb = computed(() => labels.value.scrapApproveVerb || '通过报废')
const scrapRejectVerb = computed(() => labels.value.scrapRejectVerb || '驳回报废')
const title = computed(() => labels.value.stockMovesTitle || '入出库登记')
const lead = computed(
  () =>
    labels.value.stockMovesLead ||
    '登记入库或出库后即时调整库存；单仓模式，无多仓调拨与 RFID。',
)
const countHint = computed(() => {
  const base = labels.value.stockCountHint || '录入实盘数量后过账：库存调整为实盘并记差额流水。'
  const extras = []
  const opts = getSchema()?.stockCountOpts || {}
  if (opts.countLock) extras.push('盘点锁定开启时不可出入库/报废。')
  if (opts.blindCount) extras.push('盲盘模式不回显账存，请先清点再过账。')
  if (opts.requireDiffReason) extras.push('有差额时须填写差异原因。')
  return extras.length ? `${base} ${extras.join(' ')}` : base
})
const countLockedHint = computed(() => {
  const opts = getSchema()?.stockCountOpts || {}
  return opts.countLock ? (labels.value.countLockHint || '盘点锁定期间请暂停出入库。') : ''
})
const blindHint = computed(() => {
  const opts = getSchema()?.stockCountOpts || {}
  return opts.blindCount ? (labels.value.blindCountHint || '') : ''
})
const remarkPlaceholder = computed(() => {
  if (form.moveType === 'scrap') return '必填'
  if (form.moveType === 'count') {
    const opts = getSchema()?.stockCountOpts || {}
    return opts.requireDiffReason ? '有差额时必填差异原因' : '可选补充'
  }
  return '可选'
})

function typeLabel(t) {
  if (t === 'in') return '入库'
  if (t === 'out') return '出库'
  if (t === 'scrap') return '报废'
  if (t === 'count') return '盘点'
  return t || ''
}

function scrapStatusLabel(s) {
  if (s === 'pending') return '待审'
  if (s === 'approved') return '已通过'
  if (s === 'rejected') return '已驳回'
  return s || ''
}

const list = ref([])
const scrapList = ref([])
const total = ref(0)
const page = ref(1)
const size = 20
const saving = ref(false)
const form = reactive({ itemId: 1, moveType: 'in', qty: 1, remark: '' })

async function loadScrap() {
  if (!scrapApproveOn.value) {
    scrapList.value = []
    return
  }
  try {
    const res = await http.get('/api/stock-io/scrap-requests', {
      params: { page: 1, size: 50, status: 'pending' },
    })
    const data = res.data?.data || res.data || {}
    scrapList.value = data.list || []
  } catch {
    scrapList.value = []
  }
}

async function load() {
  const res = await http.get('/api/stock-io/moves', { params: { page: page.value, size } })
  const data = res.data?.data || res.data || {}
  list.value = data.list || []
  total.value = data.total || 0
  await loadScrap()
}

async function submit() {
  if (form.moveType === 'scrap' && !String(form.remark || '').trim()) {
    ElMessage.warning('请填写报废原因')
    return
  }
  saving.value = true
  try {
    const body =
      form.moveType === 'count'
        ? { moveType: 'count', itemId: form.itemId, actualQty: form.qty, remark: form.remark }
        : { ...form }
    const res = await http.post('/api/stock-io/moves', body)
    const data = res.data?.data || res.data || {}
    if (data.pendingApproval) {
      ElMessage.success('报废申请已提交，待审批')
    } else {
      ElMessage.success('已过账')
    }
    form.qty = form.moveType === 'count' ? 0 : 1
    form.remark = ''
    page.value = 1
    await load()
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e?.message || '登记失败')
  } finally {
    saving.value = false
  }
}

async function approveScrap(row) {
  await ElMessageBox.confirm(`确认通过报废「${row.itemTitle || row.itemId}」×${row.qty}？`, scrapApproveVerb.value)
  try {
    await http.post(`/api/stock-io/scrap-requests/${row.id}/approve`, {})
    ElMessage.success('已通过并扣减库存')
    await load()
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e?.message || '操作失败')
  }
}

async function rejectScrap(row) {
  const { value } = await ElMessageBox.prompt('请填写驳回原因', scrapRejectVerb.value, {
    inputPattern: /\S+/,
    inputErrorMessage: '请填写驳回原因',
  })
  try {
    await http.post(`/api/stock-io/scrap-requests/${row.id}/reject`, { remark: value })
    ElMessage.success('已驳回')
    await load()
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e?.message || '操作失败')
  }
}

watch(page, load)
onMounted(load)
</script>

<style scoped>
.lead { color: var(--el-text-color-secondary); margin: 0.25rem 0 1rem; }
.hint { color: var(--el-text-color-secondary); font-size: 13px; margin: -0.5rem 0 1rem; }
.filter { margin-bottom: 1rem; }
.pager { margin-top: 1rem; }
.sub { margin: 1.25rem 0 0.75rem; font-size: 1rem; font-weight: 600; }
.scrap-table { margin-bottom: 1rem; }
.muted { color: var(--el-text-color-secondary); font-size: 13px; }
</style>
