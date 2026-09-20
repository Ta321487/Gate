<template>
  <div>
    <p class="hint">填写报价。同意后上门，入库后再上架。</p>
    <el-button @click="load">刷新</el-button>
    <el-table :data="list" stripe>
      <el-table-column prop="username" label="提交人" width="100" />
      <el-table-column prop="bookTitle" label="书名" min-width="120" />
      <el-table-column prop="conditionNote" label="成色说明" min-width="120" />
      <el-table-column prop="slotName" label="上门时段" width="110" />
      <el-table-column prop="quoteYuan" label="报价" width="90" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">{{ statusText(row.status) }}</template>
      </el-table-column>
      <el-table-column label="操作" min-width="220">
        <template #default="{ row }">
          <template v-if="row.status === 'pending'">
            <el-input-number v-model="quotes[row.id]" :min="0" :precision="2" :step="1" />
            <el-button link type="primary" @click="quote(row)">报价</el-button>
          </template>
          <el-button v-else-if="row.status === 'agreed'" link type="primary" @click="act(row, 'pick')">确认上门</el-button>
          <el-button v-else-if="row.status === 'picked'" link type="primary" @click="act(row, 'stock')">入库</el-button>
          <el-button v-else-if="row.status === 'stocked'" link type="primary" @click="act(row, 'list')">上架</el-button>
        </template>
      </el-table-column>
    </el-table>
    <p v-if="!list.length" class="empty">还没有回收单。</p>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/http'

const STATUS = {
  pending: '待估价',
  quoted: '已报价',
  agreed: '已同意',
  picked: '已上门',
  stocked: '已入库',
  listed: '已上架',
  closed: '已结束',
}

const list = ref([])
const quotes = reactive({})

function statusText(status) {
  return STATUS[status] || status || ''
}

async function load() {
  const res = await http.get('/api/buybacks')
  list.value = res.data || []
}

async function quote(row) {
  const quoteYuan = quotes[row.id]
  if (quoteYuan == null) {
    ElMessage.warning('请填写报价')
    return
  }
  await http.post(`/api/buybacks/${row.id}/quote`, { quoteYuan })
  ElMessage.success('已报价')
  await load()
}

async function act(row, step) {
  await http.post(`/api/buybacks/${row.id}/${step}`)
  ElMessage.success('已保存')
  await load()
}

onMounted(load)
</script>

<style scoped>
.hint, .empty { color: var(--el-text-color-secondary); margin: 0 0 12px; }
</style>
