<template>
  <div>
    <p class="lead">{{ pageLead }}</p>
    <div class="tools">
      <el-button type="success" @click="openCreate">新增</el-button>
    </div>
    <el-table :data="list" stripe row-key="id" empty-text="暂无组织">
      <el-table-column prop="name" :label="nameLabel" min-width="160" />
      <el-table-column label="上级" min-width="140">
        <template #default="{ row }">{{ parentName(row) }}</template>
      </el-table-column>
      <el-table-column prop="sortOrder" label="排序" width="90" />
      <el-table-column label="启用" width="90">
        <template #default="{ row }">
          <el-tag :type="row.enabled ? 'success' : 'info'" size="small">{{ row.enabled ? '是' : '否' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="visible" :title="form.id ? '编辑组织' : '新增组织'" width="420px" destroy-on-close>
      <el-form label-position="top">
        <el-form-item :label="nameLabel" required>
          <el-input v-model="form.name" maxlength="64" />
        </el-form-item>
        <el-form-item :label="parentLabel">
          <el-select v-model="form.parentId" clearable style="width: 100%" :placeholder="rootLabel">
            <el-option
              v-for="o in parentOptions"
              :key="o.id"
              :label="o.name"
              :value="o.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sortOrder" :min="0" :max="9999" />
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
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'
import { getSchema } from '../../utils/domainSchema.js'

const labels = computed(() => getSchema()?.labels || {})
const pageLead = computed(() => labels.value.orgPageLead || '维护院系或部门树。')
const nameLabel = computed(() => labels.value.orgNameLabel || '名称')
const parentLabel = computed(() => labels.value.orgParentLabel || '上级')
const rootLabel = computed(() => labels.value.orgRootLabel || '（顶级）')

const list = ref([])
const visible = ref(false)
const form = reactive({ id: null, name: '', parentId: null, sortOrder: 100, enabled: true })

const parentOptions = computed(() =>
  list.value.filter((o) => o.id !== form.id),
)

function parentName(row) {
  if (!row.parentId) return rootLabel.value
  return list.value.find((o) => o.id === row.parentId)?.name || '—'
}

async function load() {
  const res = await http.get('/api/admin/org')
  list.value = res.data || []
}

function openCreate() {
  form.id = null
  form.name = ''
  form.parentId = null
  form.sortOrder = 100
  form.enabled = true
  visible.value = true
}

function openEdit(row) {
  form.id = row.id
  form.name = row.name || ''
  form.parentId = row.parentId || null
  form.sortOrder = row.sortOrder ?? 100
  form.enabled = !!row.enabled
  visible.value = true
}

async function save() {
  const body = {
    name: form.name,
    parentId: form.parentId || null,
    sortOrder: form.sortOrder,
    enabled: form.enabled,
  }
  if (form.id) await http.put(`/api/admin/org/${form.id}`, body)
  else await http.post('/api/admin/org', body)
  ElMessage.success('已保存')
  visible.value = false
  load()
}

async function remove(row) {
  await ElMessageBox.confirm(`确认删除「${row.name}」？`, '删除')
  await http.delete(`/api/admin/org/${row.id}`)
  ElMessage.success('已删除')
  load()
}

onMounted(load)
</script>

<style scoped>
.lead { margin: 0 0 12px; color: var(--el-text-color-secondary); font-size: 13px; }
.tools { margin-bottom: 12px; }
</style>
