<template>
  <div>
    <section class="hero">
      <el-button text @click="$router.push('/seats/shows')">← 返回场次</el-button>
      <h1>{{ title }}</h1>
      <p v-if="show" class="muted">
        {{ show.title }}
        · {{ show.isbn || '—' }}
        <template v-if="show.startAt"> · {{ show.startAt }}</template>
        · ¥{{ show.author }}/座
        · {{ rows }}排×{{ cols }}座 · 空闲 {{ freeCount }}
      </p>
    </section>
    <div class="screen">银幕</div>
    <div class="grid" :style="{ gridTemplateColumns: `repeat(${cols}, 2.2rem)` }">
      <button
        v-for="seat in seats"
        :key="seat.seatCode"
        type="button"
        class="seat"
        :class="seatClass(seat)"
        :disabled="seat.status !== 'free'"
        @click="toggle(seat)"
      >
        {{ seat.seatCode }}
      </button>
    </div>
    <div class="legend muted">
      <span class="dot free" />空闲
      <span class="dot pick" />已选
      <span class="dot sold" />已售
    </div>
    <div class="bar">
      <span>已选 {{ picked.length }}：{{ picked.join('、') || '—' }}</span>
      <el-button type="primary" :disabled="!picked.length" :loading="busy" @click="buy">
        确认购票 ¥{{ total }}
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import http from '../api/http'
import { getSchema } from '../utils/domainSchema'

const route = useRoute()
const router = useRouter()
const labels = computed(() => getSchema().labels || {})
const title = computed(() => labels.value.seatMapTitle || '选座购票')
const show = ref(null)
const seats = ref([])
const rows = ref(6)
const cols = ref(8)
const freeCount = ref(0)
const picked = ref([])
const busy = ref(false)

const total = computed(() => {
  const unit = Number(show.value?.author) || 0
  return (unit * picked.value.length).toFixed(2)
})

function seatClass(seat) {
  if (picked.value.includes(seat.seatCode)) return 'pick'
  if (seat.status === 'sold') return 'sold'
  return 'free'
}

function toggle(seat) {
  if (seat.status !== 'free') return
  const code = seat.seatCode
  if (picked.value.includes(code)) {
    picked.value = picked.value.filter((c) => c !== code)
  } else {
    if (picked.value.length >= 6) {
      ElMessage.warning('单次最多选 6 座')
      return
    }
    picked.value = [...picked.value, code]
  }
}

async function load() {
  const id = route.params.id
  const res = await http.get(`/api/seats/shows/${id}/map`)
  const data = res.data?.data || res.data || {}
  show.value = data.show
  seats.value = data.seats || []
  rows.value = data.rows || 6
  cols.value = data.cols || 8
  freeCount.value = data.freeCount || 0
  picked.value = []
}

async function buy() {
  busy.value = true
  try {
    await http.post('/api/seats/purchase', {
      showId: Number(route.params.id),
      seats: picked.value,
    })
    ElMessage.success('已占座并生成订单')
    router.push('/orders')
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '购票失败')
    await load()
  } finally {
    busy.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 1rem; }
.muted { color: var(--el-text-color-secondary); }
.screen {
  text-align: center;
  padding: 0.5rem;
  margin: 0 auto 1rem;
  max-width: 20rem;
  background: var(--el-fill-color);
  border-radius: 4px;
  color: var(--el-text-color-secondary);
  font-size: 0.85rem;
}
.grid {
  display: grid;
  gap: 0.35rem;
  justify-content: center;
  margin-bottom: 1rem;
}
.seat {
  width: 2.2rem;
  height: 2.2rem;
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  font-size: 0.65rem;
  cursor: pointer;
  background: #fff;
  padding: 0;
}
.seat.free:hover { border-color: var(--el-color-primary); }
.seat.pick { background: var(--el-color-primary); color: #fff; border-color: var(--el-color-primary); }
.seat.sold { background: var(--el-fill-color-dark); color: var(--el-text-color-placeholder); cursor: not-allowed; }
.legend { display: flex; gap: 1rem; justify-content: center; margin-bottom: 1rem; align-items: center; }
.dot { display: inline-block; width: 0.75rem; height: 0.75rem; border-radius: 2px; margin-right: 0.25rem; vertical-align: middle; }
.dot.free { background: #fff; border: 1px solid var(--el-border-color); }
.dot.pick { background: var(--el-color-primary); }
.dot.sold { background: var(--el-fill-color-dark); }
.bar {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  align-items: center;
  justify-content: space-between;
  padding: 1rem;
  border-top: 1px solid var(--el-border-color-lighter);
}
</style>
