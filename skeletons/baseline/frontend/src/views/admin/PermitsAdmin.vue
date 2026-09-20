<template>
  <div>
    <div class="toolbar">
      <el-button @click="load">刷新</el-button>
    </div>
    <el-table :data="list" stripe>
      <el-table-column prop="username" label="用户" width="120" />
      <el-table-column label="对象" min-width="140">
        <template #default="{ row }">{{ row.itemId ? `商品 #${row.itemId}` : `分类 #${row.categoryId}` }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">{{ statusLabel(row.status) }}</template>
      </el-table-column>
      <el-table-column prop="rejectReason" label="驳回原因" min-width="160" />
      <el-table-column label="图片" width="80">
        <template #default="{ row }">
          <a v-if="row.imageUrl" :href="row.imageUrl" target="_blank" rel="noopener noreferrer">查看</a>
          <span v-else>—</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="140">
        <template #default="{ row }">
          <el-button v-if="row.status === 'pending'" link type="primary" @click="pass(row)">通过</el-button>
          <el-button v-if="row.status === 'pending'" link type="danger" @click="openReject(row)">驳回</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-dialog v-model="visible" title="驳回" width="420px">
      <el-form label-width="88px">
        <el-form-item label="原因" required>
          <el-input v-model="reason" type="textarea" :rows="3" maxlength="255" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="reject">确认驳回</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/http'

const list = ref([])
const visible = ref(false)
const reason = ref('')
const currentId = ref(null)

function statusLabel(s) {
  if (s === 'approved') return '已通过'
  if (s === 'rejected') return '已驳回'
  return '待审'
}

async function load() {
  const res = await http.get('/api/purchase-permits')
  list.value = res.data || []
}

async function pass(row) {
  await http.post('/api/purchase-permits/review', { id: row.id, status: 'approved' })
  ElMessage.success('已通过')
  load()
}

function openReject(row) {
  currentId.value = row.id
  reason.value = ''
  visible.value = true
}

async function reject() {
  if (!reason.value.trim()) {
    ElMessage.warning('请填写驳回原因')
    return
  }
  await http.post('/api/purchase-permits/review', {
    id: currentId.value,
    status: 'rejected',
    rejectReason: reason.value.trim(),
  })
  ElMessage.success('已驳回')
  visible.value = false
  load()
}

onMounted(load)
</script>
