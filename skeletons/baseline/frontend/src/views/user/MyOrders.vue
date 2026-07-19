<template>
  <div>
    <section class="hero">
      <h1>{{ label }}</h1>
      <p>查看{{ orderNoun }}状态与明细。</p>
      <el-select v-model="status" clearable placeholder="全部状态" style="width:140px" @change="load">
        <el-option v-for="(lab, key) in states" :key="key" :label="lab" :value="key" />
      </el-select>
    </section>

    <article v-for="row in list" :key="row.id" class="card">
      <div class="hd">
        <strong>{{ orderNoun }} #{{ row.id }}</strong>
        <el-tag size="small" effect="plain">{{ states[row.status] || row.status }}</el-tag>
      </div>
      <p class="sub">{{ row.createdAt }} · 合计 ¥{{ row.totalYuan }}</p>
      <ul class="lines">
        <li v-for="ln in row.lines || []" :key="ln.id">{{ ln.title }} × {{ ln.qty }}（¥{{ ln.lineYuan }}）</li>
      </ul>
      <div class="acts">
        <el-button
          v-if="row.status === 'pending' || row.status === 'confirmed'"
          size="small"
          @click="cancel(row)"
        >取消</el-button>
      </div>
    </article>
    <div v-if="!list.length" class="empty">暂无{{ orderNoun }}</div>
    <div class="pager">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="size"
        background
        layout="total, prev, pager, next"
        :total="total"
        @current-change="load"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'
import { getSchema, menuLabel } from '../../utils/domainSchema.js'

const label = menuLabel('user', 'my_orders', '我的订单')
const orderNoun = computed(() => getSchema()?.entities?.order?.label || '订单')
const states = computed(() => getSchema()?.entities?.order?.states || {})
const list = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const status = ref(null)

async function load() {
  const res = await http.get('/api/orders', {
    params: { page: page.value, size: size.value, status: status.value || undefined },
  })
  list.value = res.data?.list || []
  total.value = res.data?.total || 0
}

async function cancel(row) {
  await ElMessageBox.confirm(`取消${orderNoun.value} #${row.id}？`, '取消')
  await http.post(`/api/orders/${row.id}/cancel`)
  ElMessage.success('已取消')
  load()
}

onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 16px; }
.hero h1 { margin: 0 0 6px; font-size: 22px; }
.hero p { margin: 0 0 10px; color: #64748b; font-size: 13px; }
.card {
  background: #fff; border: 1px solid #e2e8f0; border-radius: 12px;
  padding: 14px 16px; margin-bottom: 12px;
}
.hd { display: flex; justify-content: space-between; gap: 8px; align-items: center; }
.sub { margin: 6px 0; color: #64748b; font-size: 12px; }
.lines { margin: 0; padding-left: 18px; color: #334155; font-size: 13px; }
.acts { margin-top: 10px; }
.empty { text-align: center; color: #94a3b8; padding: 40px 0; }
.pager { margin-top: 16px; display: flex; justify-content: flex-end; }
</style>
