<template>
  <div>
    <p class="tip">{{ hint }}</p>
    <el-form label-width="88px" class="form">
      <el-form-item label="范围" required>
        <el-radio-group v-model="scope">
          <el-radio value="item">按商品</el-radio>
          <el-radio value="category">按分类</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item v-if="scope === 'item'" label="商品" required>
        <el-select v-model="form.itemId" placeholder="选择需审核的商品" style="width: 100%">
          <el-option v-for="it in targets" :key="it.id" :label="it.title" :value="it.id" />
        </el-select>
      </el-form-item>
      <el-form-item v-else label="分类" required>
        <el-select v-model="form.categoryId" placeholder="选择分类" style="width: 100%">
          <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="资料图片" required>
        <el-upload :show-file-list="false" accept="image/*" :http-request="onImage">
          <el-button>上传图片</el-button>
        </el-upload>
        <a v-if="form.imageUrl" :href="form.imageUrl" target="_blank" rel="noopener noreferrer">已上传</a>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="submit">提交审核</el-button>
      </el-form-item>
    </el-form>
    <el-table :data="list" stripe>
      <el-table-column label="对象" min-width="140">
        <template #default="{ row }">{{ row.itemId ? `商品 #${row.itemId}` : `分类 #${row.categoryId}` }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">{{ statusLabel(row.status) }}</template>
      </el-table-column>
      <el-table-column prop="rejectReason" label="驳回原因" min-width="160" />
      <el-table-column label="图片" width="80">
        <template #default="{ row }">
          <a v-if="row.imageUrl" :href="row.imageUrl" target="_blank" rel="noopener noreferrer">查看</a>
          <span v-else>—</span>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import http from '../../api/http'
import { getSchema } from '../../utils/domainSchema.js'

const route = useRoute()
const hint = computed(() => getSchema()?.labels?.purchaseGateHint || '需审核的商品要先通过，才能购买。')
const scope = ref('item')
const targets = ref([])
const categories = ref([])
const list = ref([])
const form = reactive({ itemId: null, categoryId: null, imageUrl: '' })

function statusLabel(s) {
  if (s === 'approved') return '已通过'
  if (s === 'rejected') return '已驳回'
  return '待审'
}

async function load() {
  const [t, c, m] = await Promise.all([
    http.get('/api/purchase-permits/targets'),
    http.get('/api/categories'),
    http.get('/api/purchase-permits/mine'),
  ])
  targets.value = t.data || []
  categories.value = c.data || []
  list.value = m.data || []
  const q = Number(route.query.itemId || 0)
  if (q && targets.value.some((x) => x.id === q)) form.itemId = q
}

async function onImage(opt) {
  const fd = new FormData()
  fd.append('file', opt.file)
  const res = await http.post('/api/upload', fd)
  form.imageUrl = res.data?.url || ''
  ElMessage.success('图片已上传')
}

async function submit() {
  if (!form.imageUrl) {
    ElMessage.warning('请上传审核图片')
    return
  }
  if (scope.value === 'item' && !form.itemId) {
    ElMessage.warning('请选择商品')
    return
  }
  if (scope.value === 'category' && !form.categoryId) {
    ElMessage.warning('请选择分类')
    return
  }
  await http.post('/api/purchase-permits', {
    itemId: scope.value === 'item' ? form.itemId : null,
    categoryId: scope.value === 'category' ? form.categoryId : null,
    imageUrl: form.imageUrl,
  })
  ElMessage.success('已提交，等待审核')
  form.imageUrl = ''
  load()
}

onMounted(load)
</script>
