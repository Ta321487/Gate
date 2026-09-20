<template>
  <div>
    <p class="hint">还车后在这里验损。无损退全部押金，有损从押金里扣。</p>
    <el-button @click="load">刷新</el-button>
    <el-table :data="list" stripe style="margin-top: 12px">
      <el-table-column prop="id" label="订单" width="80" />
      <el-table-column prop="username" label="租用人" width="120" />
      <el-table-column prop="depositYuan" label="押金" width="100" />
      <el-table-column prop="rentYuan" label="租金" width="100" />
      <el-table-column prop="lateFeeYuan" label="逾期费" width="100" />
      <el-table-column label="操作" min-width="220">
        <template #default="{ row }">
          <el-button link type="primary" @click="open(row)">验损退押</el-button>
        </template>
      </el-table-column>
    </el-table>
    <p v-if="!list.length" class="empty">暂无待验损订单。</p>
    <el-dialog v-model="visible" title="验损退押" width="440px">
      <el-form label-width="88px">
        <el-form-item label="扣款(元)">
          <el-input-number v-model="form.deductYuan" :min="0" :precision="2" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="form.note" type="textarea" maxlength="200" />
        </el-form-item>
        <el-form-item label="维修中">
          <el-switch v-model="form.repair" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="submit">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/http'

const list = ref([])
const visible = ref(false)
const form = reactive({ id: null, deductYuan: 0, note: '', repair: false })

async function load() {
  const res = await http.get('/api/rental-bond/inspect')
  list.value = res.data || []
}

function open(row) {
  Object.assign(form, { id: row.id, deductYuan: 0, note: '', repair: false })
  visible.value = true
}

async function submit() {
  await http.post(`/api/rental-bond/inspect/${form.id}`, {
    deductYuan: form.deductYuan,
    note: form.note,
    repair: form.repair,
  })
  ElMessage.success('已处理押金')
  visible.value = false
  await load()
}

onMounted(load)
</script>

<style scoped>
.hint, .empty { color: var(--el-text-color-secondary); }
</style>
