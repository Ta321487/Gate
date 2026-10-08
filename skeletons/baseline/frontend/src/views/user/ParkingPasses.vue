<template>
  <div>
    <section class="hero">
      <div>
        <h1>{{ pageTitle }}</h1>
        <p>{{ pageLead }}</p>
      </div>
      <el-button @click="load">刷新</el-button>
    </section>
    <p v-if="remainHint" class="hint">{{ remainHint }}：{{ totalRemain }}</p>
    <el-table :data="list" stripe empty-text="暂无停车次卡">
      <el-table-column :label="packLabel" prop="packName" min-width="140" />
      <el-table-column :label="remainLabel" prop="remainCount" width="120" />
    </el-table>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import http from '../../api/http'
import { getSchema, menuLabel } from '../../utils/domainSchema.js'

const labels = computed(() => getSchema()?.labels || {})
const pageTitle = computed(
  () => labels.value.parkingPassTitle || menuLabel('user', 'parking_pass', '我的停车次卡'),
)
const pageLead = computed(
  () => labels.value.parkingPassLead || '包月次卡剩余次数；预约成功将自动扣减一次（有余次时）。',
)
const packLabel = computed(() => labels.value.parkingPassPackLabel || '套餐名称')
const remainLabel = computed(() => labels.value.parkingPassRemainLabel || '剩余次数')
const remainHint = computed(() => labels.value.parkingPassRemainHint || '次卡余次')
const list = ref([])
const totalRemain = computed(() =>
  list.value.reduce((n, r) => n + (Number(r.remainCount) || 0), 0),
)

async function load() {
  const res = await http.get('/api/parking-passes')
  list.value = Array.isArray(res.data) ? res.data : []
}

onMounted(load)
</script>

<style scoped>
.hero {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
}
.hero h1 { margin: 0 0 6px; font-size: 22px; }
.hero p { margin: 0; color: var(--portal-muted, #64748b); font-size: 13px; }
.hint { margin: 0 0 12px; font-size: 13px; color: var(--portal-muted, #64748b); }
</style>
