<template>
  <div>
    <div class="toolbar">
      <el-button type="primary" @click="open()">新增{{ typeLabel }}</el-button>
      <el-button @click="load">刷新</el-button>
    </div>
    <el-table :data="list" stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="name" :label="typeLabel + '名称'" min-width="160" />
      <el-table-column prop="sortNo" label="排序" width="90" />
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="open(row)">编辑</el-button>
          <el-button link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="visible" :title="(form.id ? '编辑' : '新增') + typeLabel" width="420px">
      <el-form :model="form" label-width="88px" require-asterisk-position="right">
        <el-form-item :label="typeLabel + '名称'" required>
          <el-input v-model="form.name" maxlength="64" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sortNo" :min="0" :max="999" />
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
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'

const typeLabel = ref('类型')
const list = ref([])
const visible = ref(false)
const form = reactive({ id: null, name: '', sortNo: 0 })

async function load() {
  const meta = await http.get('/api/admin/lookups/meta')
  typeLabel.value = meta.data.typeLabel || '类型'
  const res = await http.get('/api/admin/lookups/types')
  list.value = res.data
}

function open(row) {
  Object.assign(form, row
    ? { id: row.id, name: row.name || '', sortNo: row.sortNo ?? 0 }
    : { id: null, name: '', sortNo: 0 })
  visible.value = true
}

async function save() {
  if (!form.name.trim()) {
    ElMessage.warning('请填写名称')
    return
  }
  const body = { name: form.name, sortNo: form.sortNo }
  if (form.id) await http.put(`/api/admin/lookups/types/${form.id}`, body)
  else await http.post('/api/admin/lookups/types', body)
  ElMessage.success('已保存')
  visible.value = false
  load()
}

async function remove(row) {
  await ElMessageBox.confirm(`确认删除${typeLabel.value}「${row.name}」？`, '删除')
  await http.delete(`/api/admin/lookups/types/${row.id}`)
  ElMessage.success('已删除')
  load()
}

onMounted(load)
</script>

<style scoped>
.toolbar { margin-bottom: 12px; display: flex; gap: 8px; }
</style>
