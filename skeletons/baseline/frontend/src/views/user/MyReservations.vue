<template>
  <div>
    <section class="hero">
      <h1>{{ label }}</h1>
      <p>已占坑的预约记录，可取消释放时段。</p>
      <el-select v-model="status" clearable placeholder="全部状态" style="width:140px" @change="load">
        <el-option v-for="(lab, key) in states" :key="key" :label="lab" :value="key" />
      </el-select>
    </section>

    <article v-for="row in list" :key="row.id" class="card">
      <div class="hd">
        <strong>{{ row.itemTitle || row.title || ('预约 #' + row.id) }}</strong>
        <el-tag size="small" effect="plain">{{ states[row.status] || row.status }}</el-tag>
      </div>
      <p class="sub">{{ row.startAt }} ~ {{ row.endAt }}</p>
      <p v-if="row.remark" class="sub">备注：{{ row.remark }}</p>
      <p class="sub">申请于 {{ row.createdAt }}</p>
      <div class="acts">
        <el-button
          v-if="row.status === 'pending' || row.status === 'confirmed'"
          size="small"
          @click="cancel(row)"
        >取消预约</el-button>
      </div>
    </article>
    <div v-if="!list.length" class="empty">暂无预约</div>
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

const label = menuLabel('user', 'my_reservations', '我的预约')
const states = computed(() => getSchema()?.entities?.reservation?.states || {})
const list = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const status = ref(null)

async function load() {
  const res = await http.get('/api/slots/reservations', {
    params: { page: page.value, size: size.value, status: status.value || undefined },
  })
  list.value = res.data?.list || []
  total.value = res.data?.total || 0
}

async function cancel(row) {
  await ElMessageBox.confirm(`取消「${row.itemTitle}」的预约？`, '取消')
  await http.post(`/api/slots/reservations/${row.id}/cancel`)
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
.sub { margin: 4px 0 0; color: #64748b; font-size: 12px; }
.acts { margin-top: 10px; }
.empty { text-align: center; color: #94a3b8; padding: 40px 0; }
.pager { margin-top: 16px; display: flex; justify-content: flex-end; }
</style>
