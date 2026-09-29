<template>
  <div>
    <h2 class="title">{{ pageTitle }}</h2>
    <p class="lead">{{ pageLead }}</p>

    <el-form inline class="toolbar" @submit.prevent>
      <el-form-item label="编码" required>
        <el-input v-model="form.code" maxlength="32" placeholder="如 A-01" style="width: 140px" />
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="form.remark" maxlength="255" placeholder="可选" style="width: 200px" />
      </el-form-item>
      <el-button type="primary" :loading="saving" @click="add">新增</el-button>
      <el-button @click="load">刷新</el-button>
    </el-form>

    <div class="table-scroll">
      <el-table :data="list" stripe>
        <el-table-column prop="code" label="编码" width="120" />
        <el-table-column prop="remark" label="备注" min-width="160" show-overflow-tooltip />
        <el-table-column prop="createdAt" label="创建时间" width="170" />
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
    <div v-if="!list.length" class="empty">暂无货架</div>

    <el-dialog v-model="visible" title="编辑货架" width="420px">
      <el-form :model="editForm" label-width="72px" require-asterisk-position="right">
        <el-form-item label="编码" required>
          <el-input v-model="editForm.code" maxlength="32" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="editForm.remark" maxlength="255" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="saveEdit">保存</el-button>
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
const pageTitle = computed(() => labels.value.parcelShelfTitle || '货架管理')
const pageLead = computed(
  () => labels.value.parcelShelfLead || '维护驿站货架与柜格编号，便于到件入库时对照存放位置。',
)

const list = ref([])
const saving = ref(false)
const visible = ref(false)
const form = reactive({ code: '', remark: '' })
const editForm = reactive({ id: null, code: '', remark: '' })

async function load() {
  const res = await http.get('/api/admin/parcel-shelf')
  list.value = res.data || res || []
}

async function add() {
  if (!form.code.trim()) {
    ElMessage.warning('请填写编码')
    return
  }
  saving.value = true
  try {
    await http.post('/api/admin/parcel-shelf', { code: form.code, remark: form.remark })
    ElMessage.success('已新增')
    form.code = ''
    form.remark = ''
    await load()
  } finally {
    saving.value = false
  }
}

function openEdit(row) {
  Object.assign(editForm, { id: row.id, code: row.code, remark: row.remark || '' })
  visible.value = true
}

async function saveEdit() {
  if (!editForm.code?.trim()) {
    ElMessage.warning('请填写编码')
    return
  }
  await http.put(`/api/admin/parcel-shelf/${editForm.id}`, {
    code: editForm.code,
    remark: editForm.remark,
  })
  ElMessage.success('已保存')
  visible.value = false
  load()
}

async function remove(row) {
  await ElMessageBox.confirm(`确认删除货架「${row.code}」？`, '删除货架')
  await http.delete(`/api/admin/parcel-shelf/${row.id}`)
  ElMessage.success('已删除')
  load()
}

onMounted(load)
</script>

<style scoped>
.title { margin: 0 0 6px; font-size: 18px; }
.lead { margin: 0 0 12px; color: var(--portal-muted, #606266); font-size: 13px; }
.toolbar { margin-bottom: 12px; display: flex; flex-wrap: wrap; gap: 4px; align-items: flex-end; }
.empty { color: var(--portal-muted, #94a3b8); padding: 12px 0; }
</style>
