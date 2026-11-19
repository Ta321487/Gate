<template>
  <div
    class="seat-map-page"
    :data-cinema-face="cinemaFace"
    :class="{ 'face-performance': isPerformance }"
  >
    <el-button text class="back" @click="$router.push('/seats/shows')">← 返回场次</el-button>

    <div v-if="show" class="seat-head">
      <div class="thumb" aria-hidden="true" />
      <div>
        <h1>{{ show.title || title }}</h1>
        <p class="muted">
          {{ show.isbn || '—' }}
          <template v-if="show.categoryName"> · {{ show.categoryName }}</template>
          <el-tag v-if="effectTag" size="small" type="warning" effect="plain" class="hall-tag">{{ effectTag }}</el-tag>
          <template v-if="show.startAt"> · {{ show.startAt }}</template>
          · ¥{{ show.author }}/座
          <template v-if="show.shopName"> · {{ orgNoun }} {{ show.shopName }}</template>
          · {{ rows }}排×{{ cols }}座 · 空闲 {{ freeCount }}
        </p>
      </div>
    </div>
    <h1 v-else>{{ title }}</h1>

    <p v-if="comboOn && cinemaComboBody" class="combo">
      <strong>{{ cinemaComboLabel }}</strong>：{{ cinemaComboBody }}
    </p>
    <p v-if="cinemaMemberOn && cinemaMemberHint" class="combo">
      <strong>{{ cinemaMemberLabel }}</strong>：{{ cinemaMemberHint }}
    </p>
    <p v-if="cinemaPointsOn && cinemaPointsHint" class="combo">
      <strong>{{ cinemaPointsLabel }}</strong>：{{ cinemaPointsHint }}
    </p>
    <p v-if="adjacentText" class="hint-line">{{ adjacentText }}</p>
    <p v-if="holdHint" class="hint-line warn">{{ holdHint }}</p>

    <div class="map-panel">
      <div class="stage" :class="{ screen: !isPerformance }">{{ stageLabel }}</div>
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
    </div>

    <div class="notice card" v-if="noticeOn">
      <p class="notice-title">{{ cinemaNoticeLabel }}</p>
      <p class="muted">{{ cinemaNoticeBody }}</p>
      <el-checkbox v-model="noticeAgreed">{{ cinemaNoticeRequiredHint }}</el-checkbox>
    </div>
    <div class="snack card" v-if="snackOn">
      <p class="notice-title">{{ cinemaSnackLabel }}</p>
      <p v-if="cinemaSnackHint" class="muted snack-lead">{{ cinemaSnackHint }}</p>
      <p v-if="!snackList.length" class="muted">{{ cinemaSnackEmpty }}</p>
      <div v-else class="snack-list">
        <div
          v-for="s in snackList"
          :key="s.id"
          class="snack-item"
          :class="{ on: !!snackChecked[s.id], out: Number(s.stock || 0) <= 0 }"
        >
          <span class="snack-mark" aria-hidden="true">{{ snackMark(s.title) }}</span>
          <div class="snack-body">
            <p class="snack-name">{{ s.title }}</p>
            <p class="snack-meta">
              <template v-if="Number(s.stock || 0) > 0">余 {{ s.stock }}</template>
              <template v-else>{{ cinemaSnackSoldOutLabel }}</template>
            </p>
          </div>
          <div class="snack-side">
            <span class="snack-price">¥{{ Number(s.priceYuan || 0).toFixed(2) }}</span>
            <el-checkbox
              v-model="snackChecked[s.id]"
              :disabled="Number(s.stock || 0) <= 0"
            >加购</el-checkbox>
            <el-input-number
              v-if="snackChecked[s.id]"
              v-model="snackQty[s.id]"
              :min="1"
              :max="Math.min(6, Number(s.stock || 1))"
              size="small"
            />
          </div>
        </div>
      </div>
      <p v-if="cinemaSnackStockHint" class="muted tip">{{ cinemaSnackStockHint }}</p>
    </div>

    <div class="dock">
      <div class="dock-left">
        <div class="chips">
          <span v-if="!picked.length" class="chip">未选座</span>
          <span v-for="code in picked" :key="code" class="chip">{{ code }}</span>
        </div>
        <div class="sum">合计 <b>¥{{ total }}</b></div>
      </div>
      <el-button
        type="primary"
        class="dock-go"
        :disabled="!picked.length || (noticeOn && !noticeAgreed)"
        :loading="busy"
        @click="buy"
      >
        确认购票
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
const schema = computed(() => getSchema() || {})
const labels = computed(() => schema.value.labels || {})
const thicken = computed(() => schema.value.tradeThicken || {})
const cinemaFace = computed(() =>
  String(schema.value.cinemaFace || labels.value.cinemaFace || 'cinema').trim() || 'cinema',
)
const isPerformance = computed(() => cinemaFace.value === 'performance')
const stageLabel = computed(
  () => labels.value.seatStageLabel || (isPerformance.value ? '舞台' : '银幕'),
)
const orgNoun = computed(
  () => labels.value.seatOrgNoun || (isPerformance.value ? '主办方' : '影城'),
)
const title = computed(() => labels.value.seatMapTitle || '选座购票')
const noticeOn = computed(() => !!thicken.value.cinemaNotice)
const cinemaNoticeLabel = computed(
  () => labels.value.cinemaNoticeLabel || (isPerformance.value ? '观演须知' : '观影须知'),
)
const cinemaNoticeBody = computed(() => labels.value.cinemaNoticeBody || '')
const cinemaNoticeRequiredHint = computed(
  () =>
    labels.value.cinemaNoticeRequiredHint
    || (isPerformance.value ? '请先确认已阅读观演须知' : '请先确认已阅读观影须知'),
)
const seatHoldTimeoutHint = computed(() => labels.value.seatHoldTimeoutHint || '')
const adjacentSeatHintTitle = computed(() => labels.value.adjacentSeatHintTitle || '连座提示')
const adjacentSeatHintEmpty = computed(() => labels.value.adjacentSeatHintEmpty || '')
const showSoldOutLabel = computed(() => labels.value.showSoldOutLabel || '已售罄')
const attrsOn = computed(() => !!thicken.value.seatAttrs)
const seatAttrCoupleLabel = computed(
  () => labels.value.seatAttrCoupleLabel || (isPerformance.value ? '双人座' : '情侣座'),
)
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
/** 忽略过期的占座回包，避免取消后又被旧响应写回已选 */
let holdSeq = 0
let holdExpireHandled = false

function snackMark(title) {
  const t = String(title || '').trim()
  return t ? t.slice(0, 1) : '品'
}

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

function holdUntilMs(raw) {
  if (!raw) return NaN
  return Date.parse(String(raw).replace(' ', 'T'))
}

function applyMap(data, opts = {}) {
  applyingMap = true
  try {
    show.value = data.show
    seats.value = data.seats || []
    rows.value = data.rows || 6
    cols.value = data.cols || 8
    freeCount.value = data.freeCount || 0
    adjacentHint.value = data.adjacentHint || ''
    const hu = data.holdUntil || ''
    const untilMs = holdUntilMs(hu)
    const holdAlive = Number.isFinite(untilMs) && untilMs > Date.now()
    // 超时/强制释放：禁止用服务端旧 mine 把已取消座位写回
    if (opts.forceClear) {
      picked.value = []
      holdUntil.value = ''
      holdExpireHandled = true
      return
    }
    holdUntil.value = holdAlive ? hu : ''
    // 与服务端「我的占座」对齐；已过期的 hold 不当选中
    const mine = (data.seats || [])
      .filter((s) => s.mine && holdAlive)
      .map((s) => s.seatCode)
    picked.value = mine
    holdExpireHandled = !holdAlive
  } finally {
    applyingMap = false
  }
}

async function load() {
  const id = route.params.id
  const res = await http.get(`/api/seats/shows/${id}/map`)
  const data = res.data?.data || res.data || {}
  applyMap(data)
  // 进页时占座已过期：立刻走释放，勿等 watch（sec 一直为 0 可能不触发）
  if (holdUntil.value && holdRemainSec.value <= 0) {
    expireHoldLocal()
  } else if (!holdUntil.value) {
    const stillMine = (data.seats || []).some((s) => s.mine)
    if (stillMine) expireHoldLocal()
  }
}

async function holdNow() {
  // 勿在 applyMap 期间直接丢掉本次同步，否则取消选座的空 hold 发不出去，稍后又被 mine 写回
  if (applyingMap) {
    if (holdTimer) window.clearTimeout(holdTimer)
    holdTimer = window.setTimeout(holdNow, 50)
    return
  }
  const seq = ++holdSeq
  const seatsSnap = [...picked.value]
  try {
    const res = await http.post('/api/seats/hold', {
      showId: Number(route.params.id),
      seats: seatsSnap,
    })
    if (seq !== holdSeq) return
    applyMap(res.data?.data || res.data || {})
  } catch (e) {
    if (seq !== holdSeq) return
    ElMessage.error(e?.response?.data?.message || e.message || '占座失败')
    try {
      if (seatsSnap.length === 0) {
        // 取消占座失败时也先清本地，再尽力通知服务端，避免「取消后又勾上」
        picked.value = []
        holdUntil.value = ''
        await http.post('/api/seats/hold', {
          showId: Number(route.params.id),
          seats: [],
        }).catch(() => {})
      }
      await load()
      if (seatsSnap.length === 0) {
        picked.value = []
        holdUntil.value = ''
      }
    } catch { /* ignore */ }
  }
}

function scheduleHold() {
  if (holdTimer) window.clearTimeout(holdTimer)
  // 提前作废进行中的占座回包
  holdSeq += 1
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

/** 倒计时到点：本地清空 + 请求空占座强制释放，再拉图 */
async function expireHoldLocal() {
  if (holdExpireHandled) return
  holdExpireHandled = true
  if (holdTimer) {
    window.clearTimeout(holdTimer)
    holdTimer = 0
  }
  holdSeq += 1
  const had = picked.value.length > 0 || !!holdUntil.value
    || (seats.value || []).some((s) => s.mine)
  picked.value = []
  holdUntil.value = ''
  if (!had) return
  ElMessage.warning(seatHoldTimeoutHint.value || '占座已释放')
  try {
    const res = await http.post('/api/seats/hold', {
      showId: Number(route.params.id),
      seats: [],
    })
    applyMap(res.data?.data || res.data || {}, { forceClear: true })
    // 再拉一次，确认服务端已释放
    await load()
  } catch {
    try {
      await http.post('/api/seats/hold', {
        showId: Number(route.params.id),
        seats: [],
      })
    } catch { /* ignore */ }
    try {
      await load()
    } catch { /* ignore */ }
    picked.value = []
    holdUntil.value = ''
    holdExpireHandled = true
  }
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
    const needPay = !!(getSchema()?.demoPay || getSchema()?.shopMarketplace)
    ElMessage.success(
      needPay
        ? '已下单，请到「我的订单」完成付款后查看取票码'
        : '已出票，请到「我的订单」查看取票码',
    )
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

watch(
  holdRemainSec,
  (sec) => {
    if (sec <= 0 && (holdUntil.value || (seats.value || []).some((s) => s.mine))) {
      expireHoldLocal()
    }
  },
  { immediate: true },
)

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
.seat-map-page {
  --seat-ink: #1c1917;
  --seat-muted: #78716c;
  --seat-line: #e7e5e4;
  --seat-card: #ffffff;
  --seat-accent: #b45309;
  --seat-cta: #9a3412;
  --seat-ok: #9a3412;
  --seat-warn: #c2410c;
  --seat-stage: #e7e5e4;
  --seat-radius: 14px;
  --poster-b: linear-gradient(155deg, #44403c 0%, #0c0a09 75%);
  padding-bottom: 6.25rem;
}
/* 演艺皮：选中/CTA/价签跟壳主色，包擦浅蓝会一起搭 */
.seat-map-page.face-performance {
  --seat-accent: var(--portal-accent, var(--portal-brand, #6eb0d8));
  --seat-cta: var(--portal-brand, #6eb0d8);
  --seat-ok: var(--portal-brand, #6eb0d8);
  --seat-warn: color-mix(in srgb, var(--portal-brand, #6eb0d8) 55%, #b45309);
  --seat-ink: var(--portal-ink, #1e3a5f);
  --seat-muted: var(--portal-muted, #5a7088);
  --seat-line: var(--portal-line, #d0dce8);
  --seat-stage: color-mix(in srgb, var(--portal-brand, #6eb0d8) 12%, #e8eef5);
  --poster-b: var(--portal-cover, linear-gradient(160deg, #93c5fd, #6eb0d8));
}
.seat-map-page:not(.face-performance) {
  --seat-accent: #c4a574;
  --seat-cta: #3b5bdb;
  --seat-ok: #2563eb;
  --seat-ink: #1a1820;
  --seat-muted: #6b6570;
  --seat-line: #e6e2ea;
  --seat-stage: linear-gradient(180deg, #e8e4ec, #d4d0d8);
  --poster-b: linear-gradient(200deg, #2c2a33, #1a1820);
}
.back {
  margin: 0 0 0.85rem -0.35rem;
  color: var(--seat-muted);
}
.back:hover { color: var(--seat-cta); }
.seat-head {
  display: grid;
  grid-template-columns: 72px 1fr;
  gap: 0.95rem;
  align-items: center;
  background: var(--seat-card);
  border: 1px solid var(--seat-line);
  border-radius: var(--seat-radius);
  padding: 1rem 1.1rem;
  margin-bottom: 0.85rem;
  box-shadow: 0 1px 0 color-mix(in srgb, var(--seat-ink) 4%, transparent);
}
.thumb {
  box-sizing: border-box;
  width: 72px;
  height: 96px;
  border-radius: 10px;
  background: var(--poster-b);
  flex-shrink: 0;
}
.seat-head h1 {
  margin: 0 0 0.4rem;
  font-size: 1.2rem;
  font-weight: 700;
  letter-spacing: 0.01em;
  color: var(--seat-ink);
}
.muted { color: var(--seat-muted); margin: 0; font-size: 0.85rem; line-height: 1.55; }
.hall-tag { margin-left: 0.35rem; vertical-align: middle; }
.combo { color: var(--seat-ink); font-size: 0.9rem; margin: 0.4rem 0 0; }
.hint-line { color: var(--seat-muted); font-size: 0.9rem; margin: 0.4rem 0 0; }
.hint-line.warn {
  color: var(--seat-warn);
  padding: 0.55rem 0.75rem;
  border-radius: 10px;
  background: color-mix(in srgb, var(--seat-warn) 10%, #fff);
}
.map-panel {
  background: var(--seat-card);
  border: 1px solid var(--seat-line);
  border-radius: var(--seat-radius);
  padding: 1.35rem 1.1rem 1.1rem;
  margin: 1rem 0;
  box-shadow: 0 8px 24px color-mix(in srgb, var(--seat-cta) 6%, transparent);
}
.stage {
  max-width: 420px;
  margin: 0 auto 1.35rem;
  height: 40px;
  border-radius: 10px;
  background: var(--seat-stage);
  color: var(--seat-muted);
  font-size: 0.78rem;
  display: grid;
  place-items: center;
  letter-spacing: 0.32em;
  font-weight: 650;
  box-shadow: inset 0 -1px 0 color-mix(in srgb, var(--seat-ink) 6%, transparent);
}
.stage.screen {
  border-radius: 0 0 42% 42% / 0 0 100% 100%;
  letter-spacing: 0.3em;
  font-weight: 500;
  height: 30px;
}
.seat-map-scroll {
  overflow-x: auto;
  padding: 0.15rem 0 0.35rem;
  -webkit-overflow-scrolling: touch;
}
.grid {
  display: grid;
  gap: 0.42rem;
  justify-content: center;
  margin: 0 auto 0.65rem;
  width: max-content;
}
.seat {
  width: 2.2rem;
  height: 2.2rem;
  border: 1px solid color-mix(in srgb, var(--seat-line) 80%, #c4c4c4);
  border-radius: 9px;
  font-size: 0.62rem;
  cursor: pointer;
  background: #fff;
  padding: 0;
  color: var(--seat-muted);
  transition: border-color 0.15s ease, background 0.15s ease, transform 0.15s ease, box-shadow 0.15s ease;
}
.seat.free:hover {
  border-color: var(--seat-cta);
  color: var(--seat-cta);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--seat-cta) 18%, transparent);
}
.seat.pick {
  background: var(--seat-ok);
  color: #fff;
  border-color: var(--seat-ok);
  animation: seat-pick-pop 0.28s ease;
  transform: scale(1.05);
  font-weight: 700;
  box-shadow: 0 4px 10px color-mix(in srgb, var(--seat-ok) 28%, transparent);
}
@keyframes seat-pick-pop {
  0% { transform: scale(0.88); }
  70% { transform: scale(1.1); }
  100% { transform: scale(1.05); }
}
.seat.sold {
  background: color-mix(in srgb, var(--seat-line) 70%, #e7e5e4);
  color: #a8a29e;
  cursor: not-allowed;
  border-color: transparent;
}
.seat.held {
  background: #fff;
  color: #ef4444;
  border: 2px solid #ef4444;
  cursor: not-allowed;
}
.seat.couple:not(.pick):not(.sold) { box-shadow: inset 0 0 0 2px #ca8a04; }
.seat.accessible:not(.pick):not(.sold) { box-shadow: inset 0 0 0 2px #0f766e; }
.legend {
  display: flex;
  gap: 0.95rem;
  justify-content: center;
  margin-top: 1.05rem;
  padding-top: 0.85rem;
  border-top: 1px dashed var(--seat-line);
  align-items: center;
  flex-wrap: wrap;
  font-size: 0.78rem;
}
.sep { margin-left: 0.25rem; }
.dot {
  display: inline-block;
  width: 0.8rem;
  height: 0.8rem;
  border-radius: 4px;
  margin-right: 0.28rem;
  vertical-align: middle;
}
.dot.free { background: #fff; border: 1px solid #d6d3d1; }
.dot.pick { background: var(--seat-ok); border-color: var(--seat-ok); }
.dot.sold { background: #d6d3d1; }
.dot.held { background: #fff; border: 2px solid #ef4444; }
.dot.couple { background: #fff; box-shadow: inset 0 0 0 2px #ca8a04; }
.dot.accessible { background: #fff; box-shadow: inset 0 0 0 2px #0f766e; }
.notice, .snack {
  padding: 0.95rem 1.05rem;
  margin-bottom: 1rem;
  background: var(--seat-card);
  border: 1px solid var(--seat-line);
  border-radius: var(--seat-radius);
}
.notice-title { font-weight: 650; margin: 0 0 0.4rem; color: var(--seat-ink); }
.snack-lead { margin: 0 0 0.75rem; }
.snack-list {
  display: grid;
  gap: 0.55rem;
  margin: 0.35rem 0 0.55rem;
}
.snack-item {
  display: grid;
  grid-template-columns: 44px minmax(0, 1fr) auto;
  gap: 0.75rem;
  align-items: center;
  padding: 0.7rem 0.8rem;
  border: 1px solid var(--seat-line);
  border-radius: 12px;
  background: color-mix(in srgb, var(--seat-card) 88%, var(--seat-stage));
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.snack-item.on {
  border-color: color-mix(in srgb, var(--seat-cta) 45%, var(--seat-line));
  box-shadow: 0 4px 14px color-mix(in srgb, var(--seat-cta) 12%, transparent);
}
.snack-item.out { opacity: 0.55; }
.snack-mark {
  width: 44px;
  height: 44px;
  border-radius: 11px;
  display: grid;
  place-items: center;
  font-weight: 750;
  font-size: 1rem;
  color: var(--seat-cta);
  background: color-mix(in srgb, var(--seat-cta) 14%, #fff);
}
.snack-name {
  margin: 0 0 0.2rem;
  font-size: 0.92rem;
  font-weight: 650;
  color: var(--seat-ink);
}
.snack-meta {
  margin: 0;
  font-size: 0.75rem;
  color: var(--seat-muted);
}
.snack-side {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 0.55rem;
}
.snack-price {
  font-size: 1rem;
  font-weight: 750;
  color: var(--seat-cta);
  font-variant-numeric: tabular-nums;
}
.tip { font-size: 0.85rem; margin: 0.35rem 0 0; }
.dock {
  position: sticky;
  bottom: 0;
  margin: 1.15rem -0.35rem 0;
  background: color-mix(in srgb, var(--seat-card) 92%, transparent);
  border: 1px solid var(--seat-line);
  border-radius: 14px 14px 0 0;
  backdrop-filter: blur(12px);
  padding: 0.95rem 1.1rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  justify-content: space-between;
  z-index: 2;
  box-shadow: 0 -8px 28px color-mix(in srgb, var(--seat-ink) 8%, transparent);
}
.dock-left { min-width: 0; }
.chips { display: flex; gap: 0.45rem; flex-wrap: wrap; margin-bottom: 0.3rem; }
.chip {
  background: color-mix(in srgb, var(--seat-cta) 14%, #fff);
  color: var(--seat-cta);
  border-radius: 999px;
  padding: 0.22rem 0.65rem;
  font-size: 0.75rem;
  font-weight: 600;
}
.face-performance .chip {
  background: color-mix(in srgb, var(--portal-brand, #6eb0d8) 16%, #fff);
}
.seat-map-page:not(.face-performance) .chip { background: #eef2ff; }
.sum { font-size: 0.9rem; color: var(--seat-muted); }
.sum b { color: var(--seat-accent); font-size: 1.28rem; font-weight: 750; }
.dock-go {
  --el-button-bg-color: var(--seat-cta);
  --el-button-border-color: var(--seat-cta);
  --el-button-hover-bg-color: var(--seat-cta);
  --el-button-hover-border-color: var(--seat-cta);
  font-weight: 700;
  padding: 0.75rem 1.55rem;
  border-radius: 10px;
  box-shadow: 0 6px 16px color-mix(in srgb, var(--seat-cta) 28%, transparent);
}
</style>
