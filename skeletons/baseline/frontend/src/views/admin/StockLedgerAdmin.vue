<template>
  <div>
    <h2>库存流水</h2>
    <el-form inline class="filter" @submit.prevent>
      <el-form-item label="类型">
        <el-select v-model="moveType" clearable placeholder="全部" style="width: 120px">
          <el-option label="入库" value="in" />
          <el-option label="出库" value="out" />
        </el-select>
      </el-form-item>
      <el-button type="primary" @click="() => { page = 1; load() }">查询</el-button>
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
import { onMounted, ref, watch } from 'vue'
import http from '../../utils/http'

const list = ref([])
const total = ref(0)
const page = ref(1)
const size = 20
const moveType = ref('')

async function load() {
  const res = await http.get('/api/stock-io/moves', {
    params: { page: page.value, size, moveType: moveType.value || undefined },
  })
  const data = res.data?.data || res.data || {}
  list.value = data.list || []
  total.value = data.total || 0
}

watch(page, load)
onMounted(load)
</script>

<style scoped>
.filter { margin: 1rem 0; }
.pager { margin-top: 1rem; }
</style>
