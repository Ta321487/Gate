<template>
  <div>
    <section class="hero">
      <h1>选择时段</h1>
      <p v-if="itemTitle">为「{{ itemTitle }}」预约可用时段（约满不可再约）。</p>
      <div class="tools">
        <el-date-picker v-model="day" type="date" value-format="YYYY-MM-DD" @change="load" />
        <el-button type="primary" @click="load">查询</el-button>
        <el-button link @click="$router.push('/archive')">返回浏览</el-button>
      </div>
    </section>

    <div class="grid">
      <button
        v-for="s in list"
        :key="s.id"
        class="slot"
        :disabled="s.remain <= 0"
        @click="reserve(s)"
      >
        <div class="t">{{ s.startAt }}</div>
        <div class="e">至 {{ s.endAt }}</div>
        <div class="r">剩余 {{ s.remain }} / {{ s.capacity }}</div>
      </button>
    </div>
    <div v-if="!list.length" class="empty">该日暂无时段，换一天试试或联系管理员生成。</div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'

const route = useRoute()
const router = useRouter()
const itemId = computed(() => Number(route.query.itemId || 0))
const itemTitle = computed(() => String(route.query.title || ''))
const day = ref('2026-09-20')
const list = ref([])

async function load() {
  if (!itemId.value) return
  const res = await http.get('/api/slots', {
    params: { itemId: itemId.value, day: day.value || undefined },
  })
  list.value = res.data || []
}

async function reserve(s) {
  await ElMessageBox.confirm(`确认预约 ${s.startAt} ~ ${s.endAt}？`, '预约')
  await http.post('/api/slots/reserve', { slotId: s.id })
  ElMessage.success('预约成功')
  router.push('/reservations')
}

onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 16px; }
.hero h1 { margin: 0 0 6px; font-size: 22px; }
.hero p { margin: 0 0 10px; color: #64748b; font-size: 13px; }
.tools { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px;
}
.slot {
  text-align: left; padding: 14px; border-radius: 12px; border: 1px solid #e2e8f0;
  background: #fff; cursor: pointer;
}
.slot:hover:not(:disabled) { border-color: #0f766e; }
.slot:disabled { opacity: 0.45; cursor: not-allowed; }
.t { font-weight: 700; font-size: 14px; }
.e, .r { margin-top: 4px; font-size: 12px; color: #64748b; }
.empty { text-align: center; color: #94a3b8; padding: 40px 0; }
</style>
