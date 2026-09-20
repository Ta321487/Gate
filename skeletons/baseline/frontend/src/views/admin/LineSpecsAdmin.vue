<template>
  <div>
    <p class="hint">买家下单时从这些选项里选择。</p>
    <div class="toolbar">
      <el-button type="primary" @click="openCreate">添加选项</el-button>
      <el-button @click="load">刷新</el-button>
    </div>
    <el-table :data="list" stripe>
      <el-table-column prop="label" label="名称" min-width="160" />
      <el-table-column prop="sortNo" label="排序" width="80" />
      <el-table-column label="启用" width="80">
        <template #default="{ row }">{{ row.enabled ? '是' : '否' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="90">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-dialog v-model="visible" :title="form.id ? '编辑选项' : '添加选项'" width="420px">
      <el-form label-width="72px">
        <el-form-item label="名称" required>
          <el-input v-model="form.label" maxlength="64" placeholder="例如：宋体" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sortNo" :min="0" />
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
const form = reactive({ id: null, label: '', sortNo: 0, enabled: true })

async function load() {
  const res = await http.get('/api/line-specs')
  list.value = res.data || []
}

function openCreate() {
  Object.assign(form, { id: null, label: '', sortNo: 0, enabled: true })
  visible.value = true
}

function openEdit(row) {
  Object.assign(form, {
    id: row.id,
    label: row.label,
    sortNo: Number(row.sortNo) || 0,
    enabled: row.enabled !== false,
  })
  visible.value = true
}

async function save() {
  if (!String(form.label || '').trim()) {
    ElMessage.warning('请填写名称')
    return
  }
  await http.post('/api/line-specs', { ...form })
  ElMessage.success('已保存')
  visible.value = false
  await load()
}

onMounted(load)
</script>

<style scoped>
.hint { color: var(--el-text-color-secondary); margin: 0 0 12px; }
.toolbar { margin-bottom: 12px; }
</style>
