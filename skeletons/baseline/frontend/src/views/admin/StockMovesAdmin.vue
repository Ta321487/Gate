<template>
  <div>
    <h2>入出库登记</h2>
    <p class="lead">登记入库或出库后即时调整库存；单仓模式，无多仓调拨与 RFID。</p>
    <el-form inline class="filter" @submit.prevent>
      <el-form-item label="物资ID">
        <el-input-number v-model="form.itemId" :min="1" controls-position="right" />
      </el-form-item>
      <el-form-item label="类型">
        <el-select v-model="form.moveType" style="width: 110px">
          <el-option label="入库" value="in" />
          <el-option label="出库" value="out" />
        </el-select>
      </el-form-item>
      <el-form-item label="数量">
        <el-input-number v-model="form.qty" :min="1" :max="999999" controls-position="right" />
      </el-form-item>
      <el-form-item label="说明">
        <el-input v-model="form.remark" clearable placeholder="可选" style="width: 180px" />
      </el-form-item>
      <el-button type="primary" :loading="saving" @click="submit">登记过账</el-button>
    </el-form>
    <el-table :data="list" stripe>
      <el-table-column prop="createdAt" label="时间" width="180" />
      <el-table-column prop="moveType" label="类型" width="80">
        <template #default="{ row }">{{ row.moveType === 'in' ? '入库' : '出库' }}</template>
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
import { onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../utils/http'

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
  saving.value = true
  try {
    await http.post('/api/stock-io/moves', { ...form })
    ElMessage.success('已过账')
    form.qty = 1
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
.filter { margin-bottom: 1rem; }
.pager { margin-top: 1rem; }
</style>
