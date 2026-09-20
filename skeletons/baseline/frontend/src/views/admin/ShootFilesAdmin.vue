<template>
  <div>
    <p class="hint">标记已交片后，预约人才能打开文件。</p>
    <el-button @click="load">刷新</el-button>
    <el-table :data="list" stripe>
      <el-table-column prop="username" label="预约人" width="100" />
      <el-table-column prop="reservationId" label="预约" width="90" />
      <el-table-column prop="fileUrl" label="文件" min-width="180" />
      <el-table-column label="已交片" width="90">
        <template #default="{ row }">{{ Number(row.delivered) === 1 ? '是' : '否' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="90">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
        </template>
      </el-table-column>
    </el-table>
    <p v-if="!list.length" class="empty">还没有交片记录。</p>
    <el-dialog v-model="visible" title="交片" width="460px">
      <el-form label-width="72px">
        <el-form-item label="文件地址">
          <el-input v-model="form.fileUrl" maxlength="255" placeholder="https://" />
        </el-form-item>
        <el-form-item label="已交片">
          <el-switch v-model="form.delivered" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
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
const form = reactive({ id: null, fileUrl: '', delivered: false })

async function load() {
  const res = await http.get('/api/shoot/files')
  list.value = res.data || []
}

function openEdit(row) {
  Object.assign(form, {
    id: row.id,
    fileUrl: row.fileUrl || '',
    delivered: Number(row.delivered) === 1,
  })
  visible.value = true
}

async function save() {
  await http.post('/api/shoot/files', { ...form })
  ElMessage.success('已保存')
  visible.value = false
  await load()
}

onMounted(load)
</script>

<style scoped>
.hint, .empty { color: var(--el-text-color-secondary); margin: 0 0 12px; }
</style>
