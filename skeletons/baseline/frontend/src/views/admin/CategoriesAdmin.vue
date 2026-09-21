<template>
  <div>
    <div class="toolbar">
      <el-button type="primary" @click="openEdit()">新增{{ catLabel }}</el-button>
      <el-button @click="load">刷新</el-button>
    </div>
    <el-table :data="list" stripe>
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="name" :label="`${catLabel}名`" min-width="160" />
      <el-table-column v-if="multiCategory" prop="dimension" label="维度" width="120" />
      <el-table-column prop="itemCount" :label="`${label}数`" width="100" />
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="visible" :title="form.id ? `编辑${catLabel}` : `新增${catLabel}`" width="420px">
      <el-form :model="form" label-width="72px" require-asterisk-position="right" @submit.prevent>
        <el-form-item label="名称" required>
          <el-input v-model="form.name" maxlength="32" show-word-limit :placeholder="`${catLabel}名称`" />
        </el-form-item>
        <el-form-item v-if="multiCategory" label="维度" required>
          <el-select v-model="form.dimension" filterable allow-create default-first-option placeholder="如用途、材质" style="width:100%">
            <el-option v-for="d in dimensionOptions" :key="d" :label="d" :value="d" />
          </el-select>
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
import { archiveCopy, hasCap } from '../../utils/domainSchema.js'

const archive = archiveCopy()
const label = computed(() => archive.label || '对象')
const multiCategory = computed(() => !!archive.multiCategory || hasCap('multi_category'))
const catLabel = computed(() => {
  const f = (archive.fields || []).find((x) => x && (x.key === 'category' || x.key === 'categoryIds'))
  return f?.label || '分类'
})

const list = ref([])
const visible = ref(false)
const form = reactive({ id: null, name: '', dimension: '' })
const dimensionOptions = computed(() => {
  const set = new Set()
  for (const row of list.value || []) {
    const d = (row.dimension || '').trim()
    if (d) set.add(d)
  }
  ;['品类', '用途', '材质', '品牌', '目标'].forEach((d) => set.add(d))
  return [...set]
})

async function load() {
  const res = await http.get('/api/categories')
  list.value = res.data || res || []
}

function openEdit(row) {
  if (row) Object.assign(form, { id: row.id, name: row.name, dimension: row.dimension || '' })
  else Object.assign(form, { id: null, name: '', dimension: dimensionOptions.value[0] || '品类' })
  visible.value = true
}

async function save() {
  if (!form.name?.trim()) {
    ElMessage.warning(`请填写${catLabel.value}名`)
    return
  }
  if (multiCategory.value && !form.dimension?.trim()) {
    ElMessage.warning('请填写维度')
    return
  }
  const body = { name: form.name }
  if (multiCategory.value) body.dimension = form.dimension
  if (form.id) await http.put(`/api/categories/${form.id}`, body)
  else await http.post('/api/categories', body)
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
  await ElMessageBox.confirm(`确认删除${catLabel.value}「${row.name}」？`, `删除${catLabel.value}`)
  await http.delete(`/api/categories/${row.id}`)
  ElMessage.success('已删除')
  load()
}

onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; gap: 8px; margin-bottom: 12px; }
</style>
