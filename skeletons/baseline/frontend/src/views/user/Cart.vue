<template>
  <div>
    <section class="hero">
      <h1>{{ cartLabel }}</h1>
      <p>确认数量后提交订单（演示无真支付）。</p>
      <div class="tools">
        <el-button @click="load">刷新</el-button>
        <el-button type="primary" :disabled="!list.length" :loading="placing" @click="place">提交订单</el-button>
      </div>
    </section>

    <el-table :data="list" stripe empty-text="购物车为空，去浏览加购吧">
      <el-table-column prop="title" label="名称" min-width="160" />
      <el-table-column prop="priceYuan" label="单价" width="100" />
      <el-table-column label="数量" width="140">
        <template #default="{ row }">
          <el-input-number v-model="row.qty" :min="1" :max="99" size="small" @change="(v) => saveQty(row, v)" />
        </template>
      </el-table-column>
      <el-table-column prop="lineYuan" label="小计" width="100" />
      <el-table-column label="操作" width="90">
        <template #default="{ row }">
          <el-button link type="danger" @click="remove(row)">移除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <div v-if="list.length" class="total">合计 ¥{{ totalYuan }}</div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'
import { menuLabel } from '../../utils/domainSchema.js'

const router = useRouter()
const cartLabel = menuLabel('user', 'cart', '购物车')
const list = ref([])
const placing = ref(false)

const totalYuan = computed(() =>
  list.value.reduce((s, x) => s + Number(x.lineYuan || 0), 0).toFixed(2),
)

async function load() {
  const res = await http.get('/api/cart')
  list.value = res.data || []
}

async function saveQty(row, qty) {
  await http.post('/api/cart', { itemId: row.itemId, qty })
  await load()
}

async function remove(row) {
  await http.delete(`/api/cart/${row.itemId}`)
  ElMessage.success('已移除')
  load()
}

async function place() {
  const { value } = await ElMessageBox.prompt('可填写收货备注 / 口味说明（可留空）', '提交订单', {
    confirmButtonText: '提交',
    cancelButtonText: '取消',
    inputPlaceholder: '选填',
    inputValue: '',
  }).catch(() => ({ value: null }))
  if (value === null) return
  placing.value = true
  try {
    await http.post('/api/orders', { remark: String(value || '').trim() })
    ElMessage.success('下单成功')
    router.push('/orders')
  } finally {
    placing.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 16px; display: flex; flex-wrap: wrap; justify-content: space-between; gap: 12px; }
.hero h1 { margin: 0 0 6px; font-size: 22px; }
.hero p { margin: 0; color: #64748b; font-size: 13px; width: 100%; }
.tools { display: flex; gap: 8px; }
.total { margin-top: 14px; text-align: right; font-weight: 700; font-size: 16px; }
</style>
