<template>
  <div
    class="seat-shows"
    :data-cinema-face="cinemaFace"
    :data-trade-surface="tradeSurface || 'cards'"
    :class="{ 'trade-showtime': tradeSurface === 'showtime', 'face-performance': isPerformance }"
  >
    <!-- 演艺皮：大麦式首页货架 -->
    <template v-if="isPerformance && mode === 'list'">
      <!-- 头图：布局 PortalCarousel（管理端广告位）；本页只分类 + 分栏货架 -->
      <nav
        v-if="categories.length"
        class="perf-cats"
        :class="{ scroll: catsNeedScroll }"
        aria-label="演出分类"
      >
        <button
          type="button"
          class="perf-cat"
          :class="{ on: !activeCatId }"
          @click="activeCatId = null"
        >
          全部
        </button>
        <button
          v-for="c in categories"
          :key="c.id"
          type="button"
          class="perf-cat"
          :class="{ on: activeCatId === c.id }"
          :title="c.name"
          @click="activeCatId = c.id"
        >
          {{ c.name }}
        </button>
      </nav>

      <template v-if="activeCatId">
        <section class="perf-shelf">
          <div class="perf-shelf-hd">
            <h2>{{ activeCatName }}</h2>
          </div>
          <div v-if="filteredList.length" class="perf-rail-only">
              <article
              v-for="(s, idx) in filteredList"
              :key="s.id"
              class="perf-hcard"
              @click="goDetail(s.id)"
            >
              <div
                class="thumb"
                :class="['tone-' + (idx % 3), { 'has-cover': !!coverOf(s) }]"
                :style="posterStyle(s, idx)"
              />
              <div>
                <p class="name">{{ s.title }}</p>
                <p class="sub">{{ s.isbn || hallNoun }}</p>
                <p class="sub">{{ formatShowTime(s.startAt) }}</p>
                <p class="price">¥{{ Number(s.author || 0).toFixed(0) }}起</p>
              </div>
            </article>
          </div>
          <p v-else class="empty">该分类暂无开放场次</p>
        </section>
      </template>

      <template v-else>
        <section
          v-for="shelf in shelves"
          :key="shelf.key"
          class="perf-shelf"
        >
          <div class="perf-shelf-hd">
            <h2>{{ shelf.name }}</h2>
            <button
              v-if="shelf.catId"
              type="button"
              class="more"
              @click="activeCatId = shelf.catId"
            >
              查看全部
            </button>
          </div>
          <div class="perf-shelf-grid">
            <div
              class="perf-feat"
              :class="['tone-' + (shelf.tone % 3), { 'has-cover': !!coverOf(shelf.feature) }]"
              :style="posterStyle(shelf.feature, shelf.tone)"
              @click="goDetail(shelf.feature.id)"
            >
              <div class="name">{{ shelf.feature.title }}</div>
              <div class="price">¥{{ Number(shelf.feature.author || 0).toFixed(0) }}起</div>
            </div>
            <div class="perf-rail">
              <article
                v-for="(s, idx) in shelf.rail"
                :key="s.id"
                class="perf-hcard"
                @click="goDetail(s.id)"
              >
                <div
                  class="thumb"
                  :class="['tone-' + ((idx + 1) % 3), { 'has-cover': !!coverOf(s) }]"
                  :style="posterStyle(s, idx + 1)"
                />
                <div>
                  <p class="name">{{ s.title }}</p>
                  <p class="sub">{{ s.isbn || hallNoun }}</p>
                  <p class="sub">{{ formatShowTime(s.startAt) }}</p>
                  <p class="price">¥{{ Number(s.author || 0).toFixed(0) }}起</p>
                </div>
              </article>
            </div>
          </div>
        </section>
        <p v-if="!shelves.length" class="empty">
          暂无开放场次。{{ soldOutHint ? `${soldOutLabel}的场次不再展示。` : '' }}
        </p>
      </template>

      <div v-if="weekOn" class="week-switch">
        <el-radio-group v-model="mode" size="small">
          <el-radio-button value="list">场次</el-radio-button>
          <el-radio-button value="week">{{ showWeekViewLabel }}</el-radio-button>
        </el-radio-group>
      </div>
    </template>

    <!-- 影院皮 / 周视图：原列表 -->
    <template v-else>
      <section v-if="!isPerformance" class="hero">
        <div class="hero-row">
          <div>
            <h1>{{ title }}</h1>
            <p>{{ lead }}</p>
            <p v-if="comboOn && cinemaComboBody" class="combo">
              <strong>{{ cinemaComboLabel }}</strong>：{{ cinemaComboBody }}
            </p>
          </div>
          <div v-if="weekOn" class="tools">
            <el-radio-group v-model="mode" size="small">
              <el-radio-button value="list">列表</el-radio-button>
              <el-radio-button value="week">{{ showWeekViewLabel }}</el-radio-button>
            </el-radio-group>
          </div>
        </div>
      </section>

      <template v-if="mode === 'week' && weekOn">
        <div class="week-tools">
          <el-button @click="shiftWeek(-1)">上一周</el-button>
          <el-button @click="goToday">本周</el-button>
          <el-button @click="shiftWeek(1)">下一周</el-button>
          <span class="range">{{ rangeText }}</span>
          <el-button v-if="isPerformance" text type="primary" @click="mode = 'list'">返回场次</el-button>
        </div>
        <div class="week-grid">
          <div v-for="d in days" :key="d.key" class="day-col">
            <div class="day-head">
              <div class="dow">{{ d.dow }}</div>
              <div class="date">{{ d.label }}</div>
            </div>
            <button
              v-for="s in showsOnDay(d.key)"
              :key="s.id"
              type="button"
              class="chip"
              @click="goFromWeek(s.id)"
            >
              <span>{{ timeOf(s.startAt) }} {{ s.title }}<template v-if="s.shopName"> · {{ s.shopName }}</template></span>
              <el-tag v-if="effectTag(s)" size="small" type="warning" effect="plain">{{ effectTag(s) }}</el-tag>
            </button>
            <p v-if="!showsOnDay(d.key).length" class="day-empty">—</p>
          </div>
        </div>
        <p v-if="!weekShows.length" class="empty">{{ showWeekViewEmpty }}</p>
      </template>

      <template v-else>
        <div class="show-list">
          <article v-for="(s, idx) in list" :key="s.id" class="show-card">
            <div class="show-poster" :class="'tone-' + (idx % 3)">
              <span class="poster-title">{{ s.title }}</span>
              <span class="poster-sub">{{ posterSub(s) }}</span>
            </div>
            <div class="meta">
              <h2>{{ s.title }}</h2>
              <div class="badges">
                <span v-if="effectTag(s) || s.categoryName" class="badge">{{ effectTag(s) || s.categoryName }}</span>
                <span v-if="s.shopName" class="badge org">{{ s.shopName }}</span>
              </div>
              <div class="rows">
                <div>{{ hallNoun }} <b>{{ s.isbn || '—' }}</b></div>
                <div>开场 <b>{{ s.startAt || '—' }}</b></div>
                <div>座位 <b>{{ s.seatRows || 6 }} 排 × {{ s.seatCols || 8 }} 座</b></div>
                <div>余座 <b>{{ s.stock }}</b></div>
              </div>
              <div class="price">¥{{ Number(s.author || 0).toFixed(2) }}<small>/座</small></div>
            </div>
            <button type="button" class="cta" @click="goMap(s.id)">{{ seatSelectCta }}</button>
          </article>
        </div>
        <div v-if="!list.length" class="empty">
          暂无开放场次。{{ soldOutHint ? `${soldOutLabel}的场次不再展示。` : '' }}
        </div>
      </template>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import http from '../api/http'
import { getSchema } from '../utils/domainSchema'
import { APP_DELIVERED } from '../appDelivered.js'

const router = useRouter()
const tradeSurface = computed(() => {
  const s = String(
    APP_DELIVERED?.tradeSurfaceStyle
      || import.meta.env.VITE_TRADE_SURFACE_STYLE
      || '',
  ).trim()
  if (['shelfgrid', 'menuboard', 'showtime'].includes(s)) return s
  return ''
})
const list = ref([])
const categories = ref([])
const activeCatId = ref(null)
const mode = ref('list')
const weekStart = ref(startOfWeek(new Date()))
const schema = computed(() => getSchema() || {})
const labels = computed(() => schema.value.labels || {})
const thicken = computed(() => schema.value.tradeThicken || {})
const cinemaFace = computed(() =>
  String(schema.value.cinemaFace || labels.value.cinemaFace || 'cinema').trim() || 'cinema',
)
const isPerformance = computed(() => cinemaFace.value === 'performance')
const title = computed(() => labels.value.seatShowsTitle || '场次选座')
const soldOutLabel = computed(() => labels.value.showSoldOutLabel || '已售罄')
const soldOutHint = computed(() => labels.value.showSoldOutHint || '')
const lead = computed(
  () => labels.value.seatShowsLead || '选择场次后进入座位图，确认购票后出票。开场后该场次不再售票。',
)
const seatSelectCta = computed(() => labels.value.seatSelectCta || '选座')
const hallNoun = computed(() => labels.value.seatHallNoun || (isPerformance.value ? '场馆' : '影厅'))
const weekOn = computed(() => !!thicken.value.showWeekView)
const showWeekViewLabel = computed(() => labels.value.showWeekViewLabel || '周视图')
const showWeekViewEmpty = computed(() => labels.value.showWeekViewEmpty || '本周暂无场次')
const comboOn = computed(() => !!thicken.value.cinemaCombo)
const cinemaComboLabel = computed(() => labels.value.cinemaComboLabel || '连场套票')
const cinemaComboBody = computed(() => labels.value.cinemaComboBody || '')
const effectHallLabel = computed(() => labels.value.effectHallLabel || '特效厅')
const effectHallImax = computed(() => labels.value.effectHallImax || 'IMAX')

const activeCatName = computed(() => {
  const hit = categories.value.find((c) => c.id === activeCatId.value)
  return hit?.name || '分类'
})
/** 含「全部」超过 8 个：单行横滑，避免均分挤爆 / 折成墙 */
const catsNeedScroll = computed(() => (categories.value || []).length + 1 > 8)

function soldOf(s) {
  return Number(s?.soldCount ?? s?.salesCount ?? 0)
}

/** 栏内按已售座排序（大麦货架密度；不单独「推荐」条） */
function rankShows(rows) {
  return [...(rows || [])].sort((a, b) => {
    const d = soldOf(b) - soldOf(a)
    if (d) return d
    return String(a.startAt || '').localeCompare(String(b.startAt || ''))
  })
}

const filteredList = computed(() => {
  const rows = list.value || []
  if (!activeCatId.value) return rankShows(rows)
  return rankShows(rows.filter((s) => Number(s.categoryId) === Number(activeCatId.value)))
})

/** 按管理端分类分栏；无分类名的场次归「其它场次」 */
const shelves = computed(() => {
  const shows = list.value || []
  if (!shows.length) return []
  const cats = categories.value || []
  const out = []
  let tone = 0
  for (const c of cats) {
    const rows = rankShows(shows.filter((s) => Number(s.categoryId) === Number(c.id)))
    if (!rows.length) continue
    out.push({
      key: `c-${c.id}`,
      catId: c.id,
      name: c.name,
      feature: rows[0],
      rail: rows.slice(1, 4),
      tone: tone++,
    })
  }
  const known = new Set(cats.map((c) => Number(c.id)))
  const orphan = rankShows(shows.filter((s) => !s.categoryId || !known.has(Number(s.categoryId))))
  if (orphan.length && !cats.length) {
    out.push({
      key: 'all',
      catId: null,
      name: labels.value.seatShowsTitle || '演出场次',
      feature: orphan[0],
      rail: orphan.slice(1, 4),
      tone: 0,
    })
  } else if (orphan.length) {
    out.push({
      key: 'other',
      catId: null,
      name: '其它场次',
      feature: orphan[0],
      rail: orphan.slice(1, 4),
      tone: tone,
    })
  }
  return out
})

const DOW = ['一', '二', '三', '四', '五', '六', '日']

function startOfWeek(d) {
  const x = new Date(d)
  const day = (x.getDay() + 6) % 7
  x.setHours(0, 0, 0, 0)
  x.setDate(x.getDate() - day)
  return x
}

function fmtDate(d) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

const days = computed(() => {
  const out = []
  for (let i = 0; i < 7; i++) {
    const d = new Date(weekStart.value)
    d.setDate(d.getDate() + i)
    out.push({
      key: fmtDate(d),
      dow: `周${DOW[i]}`,
      label: `${d.getMonth() + 1}/${d.getDate()}`,
    })
  }
  return out
})

const rangeText = computed(() => {
  const a = days.value[0]
  const b = days.value[6]
  return `${a?.key || ''} ~ ${b?.key || ''}`
})

const weekShows = computed(() => {
  const from = days.value[0]?.key
  const to = days.value[6]?.key
  if (!from || !to) return []
  return (list.value || []).filter((s) => {
    const day = String(s.startAt || '').slice(0, 10)
    return day && day >= from && day <= to
  })
})

function showsOnDay(dayKey) {
  return weekShows.value
    .filter((s) => String(s.startAt || '').slice(0, 10) === dayKey)
    .sort((a, b) => String(a.startAt || '').localeCompare(String(b.startAt || '')))
}

function timeOf(startAt) {
  const m = String(startAt || '').match(/(\d{1,2}:\d{2})/)
  return m ? m[1] : ''
}

function formatShowTime(startAt) {
  const s = String(startAt || '').trim()
  if (!s) return '—'
  return s.replace(/-/g, '.').replace('T', ' ').slice(0, 16)
}

function coverOf(s) {
  return String(s?.coverUrl || s?.cover_url || '').trim()
}

/** 有封面用图；无封面用深色海报块（不拿壳色浅蓝当主视觉） */
function posterStyle(s, tone = 0) {
  const url = coverOf(s)
  if (url) {
    return {
      backgroundImage: `linear-gradient(90deg, rgba(15,23,42,0.55), rgba(15,23,42,0.15) 55%), url('${url}')`,
      backgroundSize: 'cover',
      backgroundPosition: 'center',
    }
  }
  const tones = ['var(--poster-a)', 'var(--poster-b)', 'var(--poster-c)']
  return { background: tones[Math.abs(Number(tone) || 0) % 3] }
}

function effectTag(s) {
  if (!thicken.value.effectHall) return ''
  const name = String(s?.categoryName || '')
  if (!name) return ''
  if (name.includes(effectHallImax.value) || /IMAX|巨幕|杜比/i.test(name)) {
    return name.includes(effectHallImax.value) ? `${effectHallLabel.value}·${effectHallImax.value}` : `${effectHallLabel.value}·${name}`
  }
  return ''
}

function posterSub(s) {
  const cat = effectTag(s) || s.categoryName || ''
  const t = timeOf(s.startAt)
  if (cat && t) return `${cat} · ${t}`
  return cat || t || ''
}

function shiftWeek(n) {
  const d = new Date(weekStart.value)
  d.setDate(d.getDate() + n * 7)
  weekStart.value = d
}

function goToday() {
  weekStart.value = startOfWeek(new Date())
}

function goDetail(id) {
  router.push(`/archive/item/${id}`)
}

function goMap(id) {
  router.push(`/seats/map/${id}`)
}

function goFromWeek(id) {
  if (isPerformance.value) goDetail(id)
  else goMap(id)
}

async function load() {
  const [showRes, catRes] = await Promise.all([
    http.get('/api/seats/shows'),
    http.get('/api/categories').catch(() => ({ data: [] })),
  ])
  list.value = showRes.data?.data || showRes.data || []
  const raw = catRes.data?.data || catRes.data || catRes || []
  categories.value = (Array.isArray(raw) ? raw : [])
    .map((c) => ({
      id: c.id,
      name: String(c.name || c.label || '').trim(),
    }))
    .filter((c) => c.id != null && c.name)
}

onMounted(load)
</script>

<style scoped>
.seat-shows {
  --seat-ink: #1c1917;
  --seat-muted: #78716c;
  --seat-line: #e7e5e4;
  --seat-card: #ffffff;
  --seat-accent: #b45309;
  --seat-cta: #9a3412;
  --seat-warn: #c2410c;
  --seat-radius: 14px;
  --poster-a: linear-gradient(155deg, #7c2d12 0%, #1c1917 70%);
  --poster-b: linear-gradient(155deg, #44403c 0%, #0c0a09 75%);
  --poster-c: linear-gradient(155deg, #57534e 0%, #1c1917 75%);
}
.seat-shows.face-performance {
  --seat-accent: var(--portal-accent, #60a5fa);
  --seat-cta: var(--portal-brand, #6eb0d8);
  --seat-ink: var(--portal-ink, #1c1917);
  --seat-muted: #64748b;
  --seat-line: #e2e8f0;
  /* 海报块用深色剧场调，壳色只染 CTA；有 coverUrl 时再叠真图 */
  --poster-a: linear-gradient(155deg, #1e3a5f 0%, #0f172a 72%);
  --poster-b: linear-gradient(155deg, #334155 0%, #0c1222 75%);
  --poster-c: linear-gradient(155deg, #1e40af 0%, #0c0a09 75%);
}
.perf-feat.has-cover,
.perf-hcard .thumb.has-cover {
  background-color: #0f172a;
}
.seat-shows:not(.face-performance) {
  --seat-accent: #c4a574;
  --seat-cta: #3b5bdb;
  --seat-ink: #1a1820;
  --seat-muted: #6b6570;
  --seat-line: #e6e2ea;
  --poster-a: linear-gradient(160deg, rgba(196, 165, 116, 0.45), #2c2a33 55%);
  --poster-b: linear-gradient(200deg, #2c2a33, #1a1820);
  --poster-c: linear-gradient(160deg, #4c1d95 0%, #1a1820 75%);
}

/* —— 演艺货架：广告轮播在布局；本页分类 + 分栏 —— */
/* 分类少：均分；多：单行横滑（不对折成墙） */
.perf-cats {
  display: flex;
  flex-wrap: nowrap;
  justify-content: space-evenly;
  align-items: stretch;
  gap: 0.15rem;
  margin: 0 0 1.4rem;
  padding: 0;
  width: 100%;
  border-bottom: 1px solid var(--seat-line);
}
.perf-cats.scroll {
  justify-content: flex-start;
  gap: 0.15rem 0.35rem;
  overflow-x: auto;
  overflow-y: hidden;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: thin;
  padding-bottom: 1px;
}
.perf-cat {
  position: relative;
  border: 0;
  background: transparent;
  padding: 0.75rem 0.85rem 0.7rem;
  flex: 1 1 auto;
  min-width: 4rem;
  font: inherit;
  font-size: 0.92rem;
  letter-spacing: 0.02em;
  color: var(--seat-muted);
  cursor: pointer;
  text-align: center;
  white-space: nowrap;
  transition: color 0.15s ease;
}
.perf-cats.scroll .perf-cat {
  flex: 0 0 auto;
  min-width: auto;
  padding-left: 1rem;
  padding-right: 1rem;
}
.perf-cat::after {
  content: '';
  position: absolute;
  left: 18%;
  right: 18%;
  bottom: -1px;
  height: 2px;
  border-radius: 2px 2px 0 0;
  background: transparent;
}
.perf-cat:hover {
  color: var(--seat-ink);
}
.perf-cat.on {
  color: var(--seat-cta);
  font-weight: 650;
}
.perf-cat.on::after {
  background: var(--seat-cta);
}

.perf-shelf { margin-bottom: 1.85rem; }
.perf-shelf-hd {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 0.85rem;
}
.perf-shelf-hd h2 {
  margin: 0;
  font-size: 1.18rem;
  font-weight: 700;
  letter-spacing: 0.01em;
  color: var(--seat-ink);
}
.perf-shelf-hd .more {
  border: 0;
  background: transparent;
  color: var(--seat-muted);
  font: inherit;
  font-size: 0.82rem;
  cursor: pointer;
}
.perf-shelf-hd .more:hover { color: var(--seat-cta); }
.perf-shelf-grid {
  display: grid;
  grid-template-columns: minmax(160px, 220px) minmax(0, 1fr);
  gap: 0.85rem;
}
.perf-feat {
  min-height: 228px;
  border-radius: 14px;
  background: var(--poster-b);
  color: #f8fafc;
  padding: 1.1rem;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  cursor: pointer;
  box-shadow: 0 10px 24px color-mix(in srgb, #0f172a 18%, transparent);
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.perf-feat:hover {
  transform: translateY(-2px);
  box-shadow: 0 14px 28px color-mix(in srgb, #0f172a 22%, transparent);
}
.perf-feat.tone-1 { background: var(--poster-a); }
.perf-feat.tone-2 { background: var(--poster-c); }
.perf-feat .name { font-weight: 700; font-size: 1.02rem; line-height: 1.35; margin-bottom: 0.45rem; }
.perf-feat .price { font-weight: 700; color: color-mix(in srgb, #fff 55%, var(--seat-cta)); }
.perf-rail,
.perf-rail-only {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.75rem;
}
.perf-rail-only { grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); }
.perf-hcard {
  display: grid;
  grid-template-columns: 68px minmax(0, 1fr);
  gap: 0.65rem;
  background: var(--seat-card);
  border: 1px solid var(--seat-line);
  border-radius: 12px;
  padding: 0.65rem;
  cursor: pointer;
  min-height: 5.6rem;
  box-sizing: border-box;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.perf-hcard:hover {
  border-color: color-mix(in srgb, var(--seat-cta) 42%, var(--seat-line));
  box-shadow: 0 6px 16px color-mix(in srgb, var(--seat-cta) 10%, transparent);
}
.perf-hcard .thumb {
  border-radius: 9px;
  background: var(--poster-c);
  min-height: 92px;
}
.perf-hcard .thumb.tone-1 { background: var(--poster-a); }
.perf-hcard .thumb.tone-2 { background: var(--poster-b); }
.perf-hcard .name {
  margin: 0 0 0.28rem;
  font-size: 0.84rem;
  font-weight: 650;
  line-height: 1.35;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  color: var(--seat-ink);
}
.perf-hcard .sub { margin: 0; font-size: 0.72rem; color: var(--seat-muted); }
.perf-hcard .price {
  margin: 0.3rem 0 0;
  font-size: 0.86rem;
  font-weight: 700;
  color: var(--seat-cta);
}
.week-switch { margin-top: 1rem; }

.hero { margin-bottom: 1rem; }
.hero-row { display: flex; gap: 1rem; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; }
.hero h1 { margin: 0 0 0.35rem; font-size: 1.65rem; letter-spacing: 0.02em; color: var(--seat-ink); }
.hero p { margin: 0; color: var(--seat-muted); line-height: 1.55; max-width: 44em; }
.tools { flex-shrink: 0; }
.combo { color: var(--seat-muted); font-size: 0.92rem; margin: 0.4rem 0 0; }
.show-list { display: grid; gap: 0.85rem; }
.show-card {
  display: grid;
  grid-template-columns: 112px minmax(0, 1fr) auto;
  gap: 1.1rem;
  align-items: center;
  background: var(--seat-card);
  border: 1px solid var(--seat-line);
  border-radius: var(--seat-radius);
  padding: 1rem;
  box-shadow: 0 1px 0 rgba(28, 25, 23, 0.04);
  box-sizing: border-box;
}
.show-poster {
  box-sizing: border-box;
  width: 100%;
  max-width: 112px;
  height: 148px;
  border-radius: 10px;
  color: #fafaf9;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  padding: 0.65rem;
  font-size: 0.78rem;
  font-weight: 600;
  line-height: 1.35;
  background: var(--poster-a);
  overflow: hidden;
}
.show-poster.tone-1 { background: var(--poster-b); }
.show-poster.tone-2 { background: var(--poster-c); }
.poster-title { display: block; }
.poster-sub { display: block; opacity: 0.8; font-weight: 400; font-size: 0.7rem; margin-top: 0.25rem; }
.meta { min-width: 0; }
.meta h2 { margin: 0 0 0.45rem; font-size: 1.1rem; color: var(--seat-ink); }
.badges { display: flex; gap: 0.45rem; flex-wrap: wrap; margin-bottom: 0.55rem; }
.badge {
  font-size: 0.75rem;
  padding: 0.1rem 0.5rem;
  border-radius: 999px;
  background: #eef2ff;
  color: #3b5bdb;
  border: 1px solid #dbe4ff;
}
.badge.org {
  background: #f5f5f4;
  color: var(--seat-muted);
  border-color: var(--seat-line);
}
.rows {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.3rem 1.4rem;
  font-size: 0.82rem;
  color: var(--seat-muted);
}
.rows b { color: var(--seat-ink); font-weight: 600; }
.price {
  color: var(--seat-accent);
  font-size: 1.2rem;
  font-weight: 700;
  margin-top: 0.55rem;
}
.price small {
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--seat-muted);
  margin-left: 0.2rem;
}
.cta {
  align-self: center;
  background: var(--seat-cta);
  color: #fff;
  border: 0;
  border-radius: 10px;
  padding: 0.7rem 1.35rem;
  font: inherit;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}
.cta:hover { filter: brightness(1.05); }
.empty { color: var(--seat-muted); }
.week-tools { display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap; margin-bottom: 0.75rem; }
.range { color: var(--seat-muted); margin-left: 0.5rem; }
.week-grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 0.5rem;
}
.day-col {
  border: 1px solid var(--seat-line);
  border-radius: 6px;
  padding: 0.5rem;
  min-height: 8rem;
  background: var(--seat-card);
}
.day-head { margin-bottom: 0.4rem; }
.dow { font-weight: 600; font-size: 0.9rem; color: var(--seat-ink); }
.date { color: var(--seat-muted); font-size: 0.8rem; }
.chip {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.2rem;
  width: 100%;
  text-align: left;
  border: 1px solid var(--seat-line);
  background: #fff;
  border-radius: 4px;
  padding: 0.35rem 0.4rem;
  margin-bottom: 0.35rem;
  cursor: pointer;
  font-size: 0.78rem;
  line-height: 1.3;
  color: var(--seat-ink);
}
.chip:hover { border-color: var(--seat-cta); }
.day-empty { color: var(--seat-muted); font-size: 0.8rem; margin: 0; }
@media (max-width: 900px) {
  .perf-shelf-grid { grid-template-columns: 1fr; }
  .perf-rail { grid-template-columns: 1fr; }
  .week-grid { grid-template-columns: 1fr; }
}
@media (max-width: 720px) {
  .show-card { grid-template-columns: 88px minmax(0, 1fr); }
  .show-card .cta { grid-column: 1 / -1; width: 100%; }
  .rows { grid-template-columns: 1fr; }
  .show-poster { max-width: 88px; height: 118px; }
}
</style>
