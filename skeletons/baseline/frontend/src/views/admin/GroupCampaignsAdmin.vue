<template>
  <div>
    <div class="toolbar">
      <el-button type="primary" @click="openCreate">新建拼团</el-button>
      <el-button @click="load">刷新</el-button>
    </div>
    <el-table :data="list" stripe>
      <el-table-column prop="title" label="商品" min-width="140" />
      <el-table-column label="进度" width="100">
        <template #default="{ row }">{{ row.joined }}/{{ row.targetSize }}</template>
      </el-table-column>
      <el-table-column prop="deadline" label="截止" min-width="170" />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">{{ statusLabel(row.status) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="90">
        <template #default="{ row }">
          <el-button v-if="row.status === 'open'" link type="primary" @click="openEdit(row)">编辑</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-dialog v-model="visible" :title="form.id ? '编辑拼团' : '新建拼团'" width="460px">
      <el-form label-width="96px">
        <el-form-item label="商品" required>
          <el-select v-model="form.itemId" filterable placeholder="选择商品" style="width: 100%">
            <el-option v-for="p in products" :key="p.id" :label="p.title" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="成团人数" required>
          <el-input-number v-model="form.targetSize" :min="2" />
        </el-form-item>
        <el-form-item label="截止时间" required>
          <el-date-picker
            v-model="form.deadline"
            type="datetime"
            value-format="YYYY-MM-DD HH:mm:ss"
            placeholder="选择截止时间"
            style="width: 100%"
          />
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
const products = ref([])
const visible = ref(false)
const form = reactive({ id: null, itemId: null, targetSize: 2, deadline: '' })

function statusLabel(s) {
  if (s === 'formed') return '已成团'
  if (s === 'failed') return '未成团'
  return '开放'
}

async function load() {
  const [a, b] = await Promise.all([
    http.get('/api/group-buys'),
    http.get('/api/group-buys/products'),
  ])
  list.value = a.data || []
  products.value = b.data || []
}

function openCreate() {
  Object.assign(form, { id: null, itemId: null, targetSize: 2, deadline: '' })
  visible.value = true
}

function openEdit(row) {
  Object.assign(form, {
    id: row.id,
    itemId: row.itemId,
    targetSize: Number(row.targetSize || 2),
    deadline: row.deadline || '',
  })
  visible.value = true
}

async function save() {
  await http.post('/api/group-buys', { ...form })
  ElMessage.success('已保存')
  visible.value = false
  load()
}

onMounted(load)
</script>
