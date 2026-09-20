<template>
  <div>
    <p class="hint">买家预约时从这些套餐里选择，金额以套餐为准。</p>
    <div class="toolbar">
      <el-button type="primary" @click="openCreate">添加套餐</el-button>
      <el-button @click="load">刷新</el-button>
    </div>
    <el-table :data="list" stripe>
      <el-table-column prop="name" label="名称" min-width="120" />
      <el-table-column prop="priceYuan" label="价格" width="100" />
      <el-table-column prop="detail" label="包含" min-width="180" />
      <el-table-column label="启用" width="80">
        <template #default="{ row }">{{ row.enabled ? '是' : '否' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="90">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-dialog v-model="visible" :title="form.id ? '编辑套餐' : '添加套餐'" width="460px">
      <el-form label-width="72px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" maxlength="64" placeholder="例如：证件照" />
        </el-form-item>
        <el-form-item label="价格" required>
          <el-input-number v-model="form.priceYuan" :min="0" :precision="2" :step="1" />
        </el-form-item>
        <el-form-item label="包含">
          <el-input v-model="form.detail" maxlength="200" placeholder="例如：含精修 2 张" />
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
const form = reactive({ id: null, name: '', priceYuan: 0, detail: '', enabled: true })

async function load() {
  const res = await http.get('/api/shoot/bundles/all')
  list.value = res.data || []
}

function openCreate() {
  Object.assign(form, { id: null, name: '', priceYuan: 0, detail: '', enabled: true })
  visible.value = true
}

function openEdit(row) {
  Object.assign(form, {
    id: row.id,
    name: row.name,
    priceYuan: Number(row.priceYuan) || 0,
    detail: row.detail || '',
    enabled: row.enabled !== false,
  })
  visible.value = true
}

async function save() {
  if (!String(form.name || '').trim()) {
    ElMessage.warning('请填写套餐名称')
    return
  }
  await http.post('/api/shoot/bundles', { ...form })
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
