<template>
  <div>
    <p class="hint">设置每个盲盒的奖品、出现机会和保底次数。</p>
    <div class="toolbar">
      <el-button type="primary" @click="openCreate">添加奖品</el-button>
      <el-button @click="load">刷新</el-button>
    </div>
    <el-table :data="list" stripe>
      <el-table-column prop="boxTitle" label="盒子" min-width="140" />
      <el-table-column prop="prizeTitle" label="奖品" min-width="140" />
      <el-table-column prop="weight" label="权重" width="80" />
      <el-table-column label="隐藏款" width="90">
        <template #default="{ row }">{{ row.hidden ? '是' : '否' }}</template>
      </el-table-column>
      <el-table-column prop="prizeStock" label="奖品库存" width="100" />
      <el-table-column prop="pityN" label="保底次数" width="100" />
      <el-table-column label="启用" width="80">
        <template #default="{ row }">{{ row.enabled ? '是' : '否' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="90">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-dialog v-model="visible" :title="form.id ? '编辑奖品' : '添加奖品'" width="480px">
      <el-form label-width="96px">
        <el-form-item label="盒子" required>
          <el-select v-model="form.boxId" filterable placeholder="选择盒子商品" style="width: 100%" @change="onBox">
            <el-option v-for="p in products" :key="p.id" :label="p.title" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="奖品" required>
          <el-select v-model="form.prizeId" filterable placeholder="选择奖品商品" style="width: 100%">
            <el-option v-for="p in prizeOptions" :key="p.id" :label="p.title" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="权重" required>
          <el-input-number v-model="form.weight" :min="1" />
        </el-form-item>
        <el-form-item label="保底次数">
          <el-input-number v-model="form.pityN" :min="0" />
        </el-form-item>
        <el-form-item label="隐藏款">
          <el-switch v-model="form.hidden" />
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
import { ElMessage } from 'element-plus'
import http from '../../api/http'

const list = ref([])
const products = ref([])
const visible = ref(false)
const form = reactive({
  id: null,
  boxId: null,
  prizeId: null,
  weight: 1,
  pityN: 0,
  hidden: false,
  enabled: true,
})

const prizeOptions = computed(() => products.value.filter((p) => p.id !== form.boxId))

async function load() {
  const [a, b] = await Promise.all([
    http.get('/api/blind-boxes'),
    http.get('/api/blind-boxes/products'),
  ])
  list.value = a.data || []
  products.value = b.data || []
}

function onBox(id) {
  const hit = products.value.find((p) => p.id === id)
  if (hit && hit.pityN != null) form.pityN = Number(hit.pityN) || 0
}

function openCreate() {
  Object.assign(form, {
    id: null,
    boxId: null,
    prizeId: null,
    weight: 1,
    pityN: 0,
    hidden: false,
    enabled: true,
  })
  visible.value = true
}

function openEdit(row) {
  Object.assign(form, {
    id: row.id,
    boxId: row.boxId,
    prizeId: row.prizeId,
    weight: Number(row.weight) || 1,
    pityN: Number(row.pityN) || 0,
    hidden: !!row.hidden,
    enabled: row.enabled !== false,
  })
  visible.value = true
}

async function save() {
  if (!form.boxId || !form.prizeId) {
    ElMessage.warning('请选择盒子和奖品')
    return
  }
  await http.post('/api/blind-boxes', { ...form })
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
