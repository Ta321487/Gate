<template>
  <div>
    <section class="hero">
      <h1>{{ title }}</h1>
      <p>{{ lead }}</p>
    </section>
    <EmptyHint v-if="!list.length" :title="empty" />
    <el-row v-else :gutter="12">
      <el-col v-for="row in list" :key="row.id" :xs="24" :sm="12" :md="8">
        <el-card shadow="hover" class="card">
          <h3>{{ row.title }}</h3>
          <p class="muted">{{ costLabel }}：{{ row.costHours }} 小时 · 余 {{ row.stock }}</p>
          <p v-if="row.remark" class="muted">{{ row.remark }}</p>
          <el-button type="primary" size="small" :loading="busyId === row.id" @click="redeem(row)">
            {{ redeemLabel }}
          </el-button>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../api/http'
import EmptyHint from '../components/EmptyHint.vue'
import { getSchema } from '../utils/domainSchema'

const labels = computed(() => getSchema()?.labels || {})
const title = computed(() => labels.value.tbCatalogTitle || '兑换目录')
const lead = computed(() => labels.value.tbCatalogLead || '用时长兑换互助权益，不涉及在线支付。')
const costLabel = computed(() => labels.value.tbCatalogCostLabel || '所需时长')
const redeemLabel = computed(() => labels.value.tbCatalogRedeemLabel || '兑换')
const empty = computed(() => labels.value.tbCatalogEmpty || '暂无可兑换项目')
const done = computed(() => labels.value.tbCatalogRedeemDone || '已兑换')
const list = ref([])
const busyId = ref(null)

async function load() {
  const res = await http.get('/api/timebank/catalog')
  list.value = res.data?.data || res.data || []
}

async function redeem(row) {
  await ElMessageBox.confirm(`确认用 ${row.costHours} 小时兑换「${row.title}」？`, redeemLabel.value)
  busyId.value = row.id
  try {
    await http.post(`/api/timebank/catalog/${row.id}/redeem`)
    ElMessage.success(done.value)
    await load()
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '兑换失败')
  } finally {
    busyId.value = null
  }
}

onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 1rem; }
.card { margin-bottom: 12px; }
.muted { color: var(--el-text-color-secondary); font-size: 13px; }
</style>
