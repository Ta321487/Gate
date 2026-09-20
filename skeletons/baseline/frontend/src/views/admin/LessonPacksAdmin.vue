<template>
  <div>
    <p class="hint">设置课时包的名称、节数、价格和有效天数。</p>
    <div class="toolbar">
      <el-button type="primary" @click="openCreate">添加课时包</el-button>
      <el-button @click="load">刷新</el-button>
    </div>
    <el-table :data="list" stripe>
      <el-table-column prop="name" label="名称" min-width="120" />
      <el-table-column prop="sessions" label="节数" width="80" />
      <el-table-column prop="priceYuan" label="价格" width="90" />
      <el-table-column prop="validDays" label="有效天数" width="100" />
      <el-table-column label="启用" width="80">
        <template #default="{ row }">{{ row.enabled ? '是' : '否' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="90">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
        </template>
      </el-table-column>
    </el-table>
    <p v-if="!list.length" class="empty">还没有课时包。</p>
    <el-dialog v-model="visible" :title="form.id ? '编辑课时包' : '添加课时包'" width="420px">
      <el-form label-width="88px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" maxlength="32" />
        </el-form-item>
        <el-form-item label="节数" required>
          <el-input-number v-model="form.sessions" :min="1" :step="1" />
        </el-form-item>
        <el-form-item label="价格" required>
          <el-input-number v-model="form.priceYuan" :min="0" :precision="2" :step="1" />
        </el-form-item>
        <el-form-item label="有效天数" required>
          <el-input-number v-model="form.validDays" :min="1" :step="1" />
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
const form = reactive({ id: null, name: '', sessions: 1, priceYuan: 0, validDays: 30, enabled: true })

async function load() {
  const res = await http.get('/api/lessons/packs/all')
  list.value = res.data || []
}

function openCreate() {
  Object.assign(form, { id: null, name: '', sessions: 1, priceYuan: 0, validDays: 30, enabled: true })
  visible.value = true
}

function openEdit(row) {
  Object.assign(form, {
    id: row.id,
    name: row.name || '',
    sessions: row.sessions || 1,
    priceYuan: Number(row.priceYuan || 0),
    validDays: row.validDays || 1,
    enabled: row.enabled !== false,
  })
  visible.value = true
}

async function save() {
  if (!String(form.name || '').trim()) {
    ElMessage.warning('请填写包名')
    return
  }
  await http.post('/api/lessons/packs', { ...form })
  ElMessage.success('已保存')
  visible.value = false
  await load()
}

onMounted(load)
</script>

<style scoped>
.hint, .empty { color: var(--el-text-color-secondary); margin: 0 0 12px; }
.toolbar { margin-bottom: 12px; }
</style>
