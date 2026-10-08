<template>
  <div>
    <section class="hero">
      <el-button text @click="$router.push('/seats/shows')">← 返回场次</el-button>
      <h1>{{ title }}</h1>
      <p v-if="show" class="muted">
        {{ show.title }}
        · {{ show.isbn || '—' }}
        <template v-if="show.categoryName"> · {{ show.categoryName }}</template>
        <el-tag v-if="effectTag" size="small" type="warning" effect="plain" class="hall-tag">{{ effectTag }}</el-tag>
        <template v-if="show.startAt"> · {{ show.startAt }}</template>
        · ¥{{ show.author }}/座
        · {{ rows }}排×{{ cols }}座 · 空闲 {{ freeCount }}
      </p>
      <p v-if="comboOn && cinemaComboBody" class="combo">
        <strong>{{ cinemaComboLabel }}</strong>：{{ cinemaComboBody }}
      </p>
      <p v-if="cinemaMemberOn && cinemaMemberHint" class="combo">
        <strong>{{ cinemaMemberLabel }}</strong>：{{ cinemaMemberHint }}
      </p>
      <p v-if="cinemaPointsOn && cinemaPointsHint" class="combo">
        <strong>{{ cinemaPointsLabel }}</strong>：{{ cinemaPointsHint }}
      </p>
      <p v-if="holdHint" class="hold-tip">{{ holdHint }}</p>
      <p v-if="adjacentText" class="hold-tip">{{ adjacentText }}</p>
    </section>
    <div class="screen">银幕</div>
    <div class="seat-map-scroll">
    <div class="grid" :style="{ gridTemplateColumns: `repeat(${cols}, 2.2rem)` }">
      <button
        v-for="seat in seats"
        :key="seat.seatCode"
        type="button"
        class="seat"
        :class="seatClass(seat)"
        :disabled="!canPick(seat)"
        @click="toggle(seat)"
      >
        {{ seat.seatCode }}
      </button>
    </div>
    </div>
    <div class="legend muted">
      <span class="dot free" />空闲
      <span class="dot pick" />已选
      <span class="dot held" />他人已选
      <span class="dot sold" />已售
      <template v-if="attrsOn">
        <span class="sep">{{ seatAttrLegendLabel }}：</span>
        <span class="dot couple" />{{ seatAttrCoupleLabel }}
        <span class="dot accessible" />{{ seatAttrAccessibleLabel }}
      </template>
    </div>
    <div class="notice card" v-if="noticeOn">
      <p class="notice-title">{{ cinemaNoticeLabel }}</p>
      <p class="muted">{{ cinemaNoticeBody }}</p>
      <el-checkbox v-model="noticeAgreed">{{ cinemaNoticeRequiredHint }}</el-checkbox>
    </div>
    <div class="snack card" v-if="snackOn">
      <p class="notice-title">{{ cinemaSnackLabel }}</p>
      <p v-if="cinemaSnackHint" class="muted">{{ cinemaSnackHint }}</p>
      <p v-if="!snackList.length" class="muted">{{ cinemaSnackEmpty }}</p>
      <div v-for="s in snackList" :key="s.id" class="snack-row">
        <el-checkbox v-model="snackChecked[s.id]" :disabled="Number(s.stock || 0) <= 0">
          {{ s.title }} · ¥{{ Number(s.priceYuan || 0).toFixed(2) }}
          <span class="muted">（余 {{ s.stock }}）</span>
        </el-checkbox>
        <el-input-number
          v-if="snackChecked[s.id]"
          v-model="snackQty[s.id]"
          :min="1"
          :max="Math.min(6, Number(s.stock || 1))"
          size="small"
        />
      </div>
      <p v-if="cinemaSnackStockHint" class="muted tip">{{ cinemaSnackStockHint }}</p>
    </div>
    <div class="bar">
      <span>已选 {{ picked.length }}：{{ picked.join('、') || '—' }}</span>
      <el-button
        type="primary"
        :disabled="!picked.length || (noticeOn && !noticeAgreed)"
        :loading="busy"
        @click="buy"
      >
        确认购票 ¥{{ total }}
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import http from '../api/http'
import { getSchema } from '../utils/domainSchema'

const route = useRoute()
const router = useRouter()
const labels = computed(() => getSchema().labels || {})
const thicken = computed(() => getSchema().tradeThicken || {})
const title = computed(() => labels.value.seatMapTitle || '选座购票')
const noticeOn = computed(() => !!thicken.value.cinemaNotice)
const cinemaNoticeLabel = computed(() => labels.value.cinemaNoticeLabel || '观影须知')
const cinemaNoticeBody = computed(() => labels.value.cinemaNoticeBody || '')
const cinemaNoticeRequiredHint = computed(
  () => labels.value.cinemaNoticeRequiredHint || '请先确认已阅读观影须知',
)
const seatHoldTimeoutHint = computed(() => labels.value.seatHoldTimeoutHint || '')
const adjacentSeatHintTitle = computed(() => labels.value.adjacentSeatHintTitle || '连座提示')
const adjacentSeatHintEmpty = computed(() => labels.value.adjacentSeatHintEmpty || '')
const showSoldOutLabel = computed(() => labels.value.showSoldOutLabel || '已售罄')
const attrsOn = computed(() => !!thicken.value.seatAttrs)
const seatAttrCoupleLabel = computed(() => labels.value.seatAttrCoupleLabel || '情侣座')
const seatAttrAccessibleLabel = computed(() => labels.value.seatAttrAccessibleLabel || '无障碍座')
const seatAttrLegendLabel = computed(() => labels.value.seatAttrLegendLabel || '座位说明')
const comboOn = computed(() => !!thicken.value.cinemaCombo)
const cinemaComboLabel = computed(() => labels.value.cinemaComboLabel || '连场套票')
const cinemaComboBody = computed(() => labels.value.cinemaComboBody || '')
const cinemaMemberOn = computed(() => !!thicken.value.cinemaMemberPrice)
const cinemaMemberLabel = computed(() => labels.value.cinemaMemberPriceLabel || '会员价')
const cinemaMemberHint = computed(() => labels.value.cinemaMemberPriceHint || '')
const cinemaPointsOn = computed(() => !!thicken.value.cinemaPointsTicket)
const cinemaPointsLabel = computed(() => labels.value.cinemaPointsTicketLabel || '积分兑票')
const cinemaPointsHint = computed(() => labels.value.cinemaPointsTicketHint || '')
const effectHallLabel = computed(() => labels.value.effectHallLabel || '特效厅')
const effectHallImax = computed(() => labels.value.effectHallImax || 'IMAX')
const snackOn = computed(() => !!thicken.value.cinemaSnack)
const cinemaSnackLabel = computed(() => labels.value.cinemaSnackLabel || '卖品加购')
const cinemaSnackHint = computed(() => labels.value.cinemaSnackHint || '')
const cinemaSnackEmpty = computed(() => labels.value.cinemaSnackEmpty || '暂无可加购卖品')
const cinemaSnackStockHint = computed(() => labels.value.cinemaSnackStockHint || '')
const cinemaSnackSoldOutLabel = computed(() => labels.value.cinemaSnackSoldOutLabel || '卖品暂时无货')

const show = ref(null)
const seats = ref([])
const rows = ref(6)
const cols = ref(8)
const freeCount = ref(0)
const picked = ref([])
const busy = ref(false)
const noticeAgreed = ref(false)
const adjacentHint = ref('')
const holdUntil = ref('')
const nowMs = ref(Date.now())
const snackList = ref([])
const snackChecked = ref({})
const snackQty = ref({})
let holdTimer = 0
let tickTimer = 0
let applyingMap = false

const snackExtra = computed(() => {
  if (!snackOn.value) return 0
  let sum = 0
  for (const s of snackList.value) {
    if (!snackChecked.value[s.id]) continue
    const qty = Number(snackQty.value[s.id] || 1)
    sum += Number(s.priceYuan || 0) * Math.max(1, qty)
  }
  return sum
})

const total = computed(() => {
  const unit = Number(show.value?.author) || 0
  return (unit * picked.value.length + snackExtra.value).toFixed(2)
})

function selectedSnacks() {
  if (!snackOn.value) return []
  const out = []
  for (const s of snackList.value) {
    if (!snackChecked.value[s.id]) continue
    const qty = Number(snackQty.value[s.id] || 1)
    if (qty < 1) continue
    out.push({ id: s.id, qty })
  }
  return out
}

async function loadSnacks() {
  if (!snackOn.value) {
    snackList.value = []
    return
  }
  try {
    const res = await http.get('/api/seats/snacks')
    const list = res.data?.data || res.data || []
    snackList.value = Array.isArray(list) ? list : []
    const checked = { ...snackChecked.value }
    const qty = { ...snackQty.value }
    for (const s of snackList.value) {
      if (checked[s.id] == null) checked[s.id] = false
      if (qty[s.id] == null) qty[s.id] = 1
    }
    snackChecked.value = checked
    snackQty.value = qty
  } catch {
    snackList.value = []
  }
}

const holdRemainSec = computed(() => {
  if (!holdUntil.value) return 0
  const t = Date.parse(String(holdUntil.value).replace(' ', 'T'))
  if (!Number.isFinite(t)) return 0
  return Math.max(0, Math.floor((t - nowMs.value) / 1000))
})

const holdHint = computed(() => {
  if (!thicken.value.seatHoldTimeout) return ''
  if (holdRemainSec.value > 0) {
    const m = Math.floor(holdRemainSec.value / 60)
    const s = String(holdRemainSec.value % 60).padStart(2, '0')
    return `${seatHoldTimeoutHint.value} 剩余 ${m}:${s}`
  }
  return seatHoldTimeoutHint.value
})

const adjacentText = computed(() => {
  if (!thicken.value.adjacentSeatHint) return ''
  if (adjacentHint.value) return `${adjacentSeatHintTitle.value}：${adjacentHint.value.replace(/^建议连坐：/, '')}`
  return `${adjacentSeatHintTitle.value}：${adjacentSeatHintEmpty.value}`
})

const effectTag = computed(() => {
  if (!thicken.value.effectHall) return ''
  const name = String(show.value?.categoryName || '')
  if (!name) return ''
  if (name.includes(effectHallImax.value) || /IMAX|巨幕|杜比/i.test(name)) {
    return name.includes(effectHallImax.value)
      ? `${effectHallLabel.value}·${effectHallImax.value}`
      : `${effectHallLabel.value}·${name}`
  }
  return ''
})

function canPick(seat) {
  return seat.status === 'free' || !!seat.mine
}

function seatClass(seat) {
  const attr = String(seat.seatAttr || '')
  const parts = ['seat-cell']
  if (picked.value.includes(seat.seatCode)) parts.push('pick', 'picked')
  else if (seat.status === 'sold') parts.push('sold')
  else if (seat.status === 'held' && !seat.mine) parts.push('held')
  else parts.push('free')
  if (attrsOn.value && attr === 'couple') parts.push('couple')
  if (attrsOn.value && attr === 'accessible') parts.push('accessible')
  return parts.join(' ')
}

function applyMap(data) {
  applyingMap = true
  show.value = data.show
  seats.value = data.seats || []
  rows.value = data.rows || 6
  cols.value = data.cols || 8
  freeCount.value = data.freeCount || 0
  adjacentHint.value = data.adjacentHint || ''
  holdUntil.value = data.holdUntil || ''
  const mine = (data.seats || [])
    .filter((s) => s.mine)
    .map((s) => s.seatCode)
  if (mine.length) picked.value = mine
  applyingMap = false
}

async function load() {
  const id = route.params.id
  const res = await http.get(`/api/seats/shows/${id}/map`)
  const data = res.data?.data || res.data || {}
  applyMap(data)
  if (!picked.value.length) picked.value = []
}

async function holdNow() {
  if (applyingMap) return
  try {
    const res = await http.post('/api/seats/hold', {
      showId: Number(route.params.id),
      seats: picked.value,
    })
    applyMap(res.data?.data || res.data || {})
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '占座失败')
    await load()
  }
}

function scheduleHold() {
  if (holdTimer) window.clearTimeout(holdTimer)
  holdTimer = window.setTimeout(holdNow, 280)
}

function toggle(seat) {
  if (!canPick(seat)) return
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
  scheduleHold()
}

async function buy() {
  if (noticeOn.value && !noticeAgreed.value) {
    ElMessage.warning(cinemaNoticeRequiredHint.value)
    return
  }
  busy.value = true
  try {
    const snacks = selectedSnacks()
    await http.post('/api/seats/purchase', {
      showId: Number(route.params.id),
      seats: picked.value,
      noticeAgreed: noticeOn.value ? noticeAgreed.value : true,
      snacks: snacks.length ? snacks : undefined,
    })
    ElMessage.success('已出票，请到「我的订单」查看取票码')
    router.push('/orders')
  } catch (e) {
    const msg = e?.response?.data?.message || e.message || '购票失败'
    if (msg.includes('卖品')) ElMessage.error(cinemaSnackSoldOutLabel.value)
    else ElMessage.error(msg.includes('售罄') ? showSoldOutLabel.value : msg)
    await load()
    await loadSnacks()
  } finally {
    busy.value = false
  }
}

watch(holdRemainSec, (sec) => {
  if (sec === 0 && picked.value.length && holdUntil.value) {
    ElMessage.warning(seatHoldTimeoutHint.value || '占座已释放')
    load()
  }
})

onMounted(() => {
  load().catch((e) => {
    ElMessage.error(e?.response?.data?.message || e.message || '无法打开座位图')
  })
  loadSnacks()
  tickTimer = window.setInterval(() => {
    nowMs.value = Date.now()
  }, 1000)
})

onUnmounted(() => {
  if (holdTimer) window.clearTimeout(holdTimer)
  if (tickTimer) window.clearInterval(tickTimer)
})
</script>

<style scoped>
.hero { margin-bottom: 1rem; }
.muted { color: var(--el-text-color-secondary); }
.hall-tag { margin-left: 0.35rem; vertical-align: middle; }
.combo { color: var(--el-text-color-regular); font-size: 0.9rem; margin: 0.35rem 0 0; }
.hold-tip { color: var(--el-color-warning); font-size: 0.9rem; margin: 0.35rem 0 0; }
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
.seat.pick {
  background: var(--el-color-primary);
  color: #fff;
  border-color: var(--el-color-primary);
  animation: seat-pick-pop 0.28s ease;
  transform: scale(1.06);
}
@keyframes seat-pick-pop {
  0% { transform: scale(0.86); }
  70% { transform: scale(1.12); }
  100% { transform: scale(1.06); }
}
.seat.sold { background: var(--el-fill-color-dark); color: var(--el-text-color-placeholder); cursor: not-allowed; }
.seat.held { background: #fde2e2; color: var(--el-color-danger); cursor: not-allowed; }
.seat.couple:not(.pick):not(.sold) { box-shadow: inset 0 0 0 2px #e6a23c; }
.seat.accessible:not(.pick):not(.sold) { box-shadow: inset 0 0 0 2px #67c23a; }
.legend { display: flex; gap: 1rem; justify-content: center; margin-bottom: 1rem; align-items: center; flex-wrap: wrap; }
.sep { margin-left: 0.25rem; }
.dot { display: inline-block; width: 0.75rem; height: 0.75rem; border-radius: 2px; margin-right: 0.25rem; vertical-align: middle; }
.dot.free { background: #fff; border: 1px solid var(--el-border-color); }
.dot.pick { background: var(--el-color-primary); }
.dot.sold { background: var(--el-fill-color-dark); }
.dot.held { background: #fde2e2; border: 1px solid var(--el-color-danger); }
.dot.couple { background: #fff; box-shadow: inset 0 0 0 2px #e6a23c; }
.dot.accessible { background: #fff; box-shadow: inset 0 0 0 2px #67c23a; }
.notice, .snack { padding: 0.85rem 1rem; margin-bottom: 1rem; }
.notice-title { font-weight: 600; margin: 0 0 0.35rem; }
.snack-row { display: flex; flex-wrap: wrap; gap: 0.75rem; align-items: center; margin: 0.4rem 0; }
.tip { font-size: 0.85rem; margin: 0.35rem 0 0; }
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
