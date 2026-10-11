<template>
  <div>
    <h2>{{ title }}</h2>
    <el-button type="primary" class="mb" @click="openEdit()">新增</el-button>
    <el-table :data="list" stripe>
      <el-table-column prop="title" label="名称" />
      <el-table-column prop="costHours" label="所需时长" width="100" />
      <el-table-column prop="stock" label="库存" width="80" />
      <el-table-column prop="enabled" label="启用" width="80">
        <template #default="{ row }">{{ Number(row.enabled) === 1 ? '是' : '否' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="100">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-dialog v-model="visible" :title="form.id ? '编辑' : '新增'" width="480px" destroy-on-close>
      <el-form label-position="top">
        <el-form-item label="名称" required>
          <el-input v-model="form.title" maxlength="120" />
        </el-form-item>
        <el-form-item label="所需时长" required>
          <el-input-number v-model="form.costHours" :min="0.5" :max="999" :step="0.5" />
        </el-form-item>
        <el-form-item label="库存">
          <el-input-number v-model="form.stock" :min="0" :max="9999" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.enabled" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" :loading="busy" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/http'
import { getSchema } from '../../utils/domainSchema'

const title = computed(() => getSchema()?.labels?.tbCatalogAdminTitle || '兑换目录维护')
const list = ref([])
const visible = ref(false)
const busy = ref(false)
const form = reactive({
  id: null,
  title: '',
  costHours: 1,
  stock: 1,
  enabled: true,
  remark: '',
})

async function load() {
  const res = await http.get('/api/timebank/admin/catalog')
  list.value = res.data?.data || res.data || []
}

function openEdit(row) {
  if (row) {
    form.id = row.id
    form.title = row.title || ''
    form.costHours = Number(row.costHours) || 1
    form.stock = Number(row.stock) || 0
    form.enabled = Number(row.enabled) === 1
    form.remark = row.remark || ''
  } else {
    form.id = null
    form.title = ''
    form.costHours = 1
    form.stock = 1
    form.enabled = true
    form.remark = ''
  }
  visible.value = true
}

async function save() {
  if (!form.title.trim()) {
    ElMessage.warning('请填写名称')
    return
  }
  busy.value = true
  try {
    await http.post('/api/timebank/admin/catalog', { ...form })
    ElMessage.success('已保存')
    visible.value = false
    await load()
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '保存失败')
  } finally {
    busy.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.mb { margin: 0.75rem 0; }
</style>
