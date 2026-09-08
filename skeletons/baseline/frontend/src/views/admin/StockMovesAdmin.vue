<template>
  <div>
    <h2>{{ title }}</h2>
    <p class="lead">{{ lead }}</p>
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
          :placeholder="form.moveType === 'scrap' ? '必填' : form.moveType === 'count' ? '可选补充' : '可选'"
          style="width: 180px"
        />
      </el-form-item>
      <el-button type="primary" :loading="saving" @click="submit">登记过账</el-button>
    </el-form>
    <p v-if="countOn && form.moveType === 'count'" class="hint">{{ countHint }}</p>
    <el-table :data="list" stripe>
      <el-table-column prop="createdAt" label="时间" width="180" />
      <el-table-column prop="moveType" label="类型" width="80">
        <template #default="{ row }">{{ typeLabel(row.moveType) }}</template>
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
import { ElMessage } from 'element-plus'
import http from '../../api/http'
import { getSchema, hasCap } from '../../utils/domainSchema.js'

const scrapOn = computed(() => hasCap('stock_scrap'))
const countOn = computed(() => hasCap('stock_count'))
const labels = computed(() => getSchema()?.labels || {})
const title = computed(() => labels.value.stockMovesTitle || '入出库登记')
const lead = computed(
  () =>
    labels.value.stockMovesLead ||
    '登记入库或出库后即时调整库存；单仓模式，无多仓调拨与 RFID。',
)
const countHint = computed(
  () => labels.value.stockCountHint || '录入实盘数量后过账：库存调整为实盘并记差额流水。',
)

function typeLabel(t) {
  if (t === 'in') return '入库'
  if (t === 'out') return '出库'
  if (t === 'scrap') return '报废'
  if (t === 'count') return '盘点'
  return t || ''
}

const list = ref([])
const total = ref(0)
const page = ref(1)
const size = 20
const saving = ref(false)
const form = reactive({ itemId: 1, moveType: 'in', qty: 1, remark: '' })

async function load() {
  const res = await http.get('/api/stock-io/moves', { params: { page: page.value, size } })
  const data = res.data?.data || res.data || {}
  list.value = data.list || []
  total.value = data.total || 0
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
    await http.post('/api/stock-io/moves', body)
    ElMessage.success('已过账')
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

watch(page, load)
onMounted(load)
</script>

<style scoped>
.lead { color: var(--el-text-color-secondary); margin: 0.25rem 0 1rem; }
.hint { color: var(--el-text-color-secondary); font-size: 13px; margin: -0.5rem 0 1rem; }
.filter { margin-bottom: 1rem; }
.pager { margin-top: 1rem; }
</style>
