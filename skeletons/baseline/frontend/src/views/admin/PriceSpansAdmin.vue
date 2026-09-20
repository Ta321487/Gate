<template>
  <div>
    <div class="toolbar">
      <el-button type="primary" @click="openCreate">新建节日价</el-button>
      <el-button @click="load">刷新</el-button>
    </div>
    <el-table :data="list" stripe>
      <el-table-column prop="name" label="名称" min-width="120" />
      <el-table-column label="日期" min-width="200">
        <template #default="{ row }">{{ row.dateFrom }} 至 {{ row.dateTo }}</template>
      </el-table-column>
      <el-table-column prop="rate" label="倍率" width="90" />
      <el-table-column label="状态" width="80">
        <template #default="{ row }">{{ row.enabled ? '启用' : '停用' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="90">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-dialog v-model="visible" :title="form.id ? '编辑节日价' : '新建节日价'" width="460px">
      <el-form label-width="88px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" maxlength="64" />
        </el-form-item>
        <el-form-item label="开始" required>
          <el-date-picker v-model="form.dateFrom" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="结束" required>
          <el-date-picker v-model="form.dateTo" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="倍率" required>
          <el-input-number v-model="form.rate" :min="1" :step="0.1" :precision="2" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.enabled" />
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
const form = reactive({
  id: null,
  name: '',
  dateFrom: '',
  dateTo: '',
  rate: 1.2,
  enabled: true,
})

async function load() {
  const res = await http.get('/api/delivery-windows/spans')
  list.value = res.data || []
}

function openCreate() {
  Object.assign(form, { id: null, name: '', dateFrom: '', dateTo: '', rate: 1.2, enabled: true })
  visible.value = true
}

function openEdit(row) {
  Object.assign(form, {
    id: row.id,
    name: row.name,
    dateFrom: row.dateFrom,
    dateTo: row.dateTo,
    rate: Number(row.rate || 1),
    enabled: !!row.enabled,
  })
  visible.value = true
}

async function save() {
  await http.post('/api/delivery-windows/spans', { ...form, enabled: form.enabled ? 1 : 0 })
  ElMessage.success('已保存')
  visible.value = false
  load()
}

onMounted(load)
</script>
