<template>
  <div>
    <div class="toolbar">
      <el-button type="primary" @click="openEdit()">新增分类</el-button>
      <el-button @click="load">刷新</el-button>
    </div>
    <el-table :data="list" stripe>
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="name" label="分类名" min-width="160" />
      <el-table-column prop="itemCount" :label="`${label}数`" width="100" />
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="visible" :title="form.id ? '编辑分类' : '新增分类'" width="420px">
      <el-form :model="form" label-width="72px" require-asterisk-position="right" @submit.prevent>
        <el-form-item label="名称" required>
          <el-input v-model="form.name" maxlength="32" show-word-limit placeholder="如：测量仪器" />
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
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'
import { archiveCopy } from '../../utils/domainSchema.js'

const archive = archiveCopy()
const label = computed(() => archive.label || '对象')

const list = ref([])
const visible = ref(false)
const form = reactive({ id: null, name: '' })

async function load() {
  const res = await http.get('/api/categories')
  list.value = res.data || res || []
}

function openEdit(row) {
  if (row) Object.assign(form, { id: row.id, name: row.name })
  else Object.assign(form, { id: null, name: '' })
  visible.value = true
}

async function save() {
  if (!form.name?.trim()) {
    ElMessage.warning('请填写分类名')
    return
  }
  if (form.id) await http.put(`/api/categories/${form.id}`, { name: form.name })
  else await http.post('/api/categories', { name: form.name })
  ElMessage.success('已保存')
  visible.value = false
  load()
}

async function remove(row) {
  const n = row.itemCount ?? row.bookCount ?? 0
  if (n > 0) {
    ElMessage.warning(`「${row.name}」下仍有 ${n} 条${label.value}，请先调整后再删`)
    return
  }
  await ElMessageBox.confirm(`确认删除分类「${row.name}」？`, '删除分类')
  await http.delete(`/api/categories/${row.id}`)
  ElMessage.success('已删除')
  load()
}

onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; gap: 8px; margin-bottom: 12px; }
</style>
