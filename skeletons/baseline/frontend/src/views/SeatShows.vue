<template>
  <div>
    <section class="hero">
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
            @click="go(s.id)"
          >
            <span>{{ timeOf(s.startAt) }} {{ s.title }}</span>
            <el-tag v-if="effectTag(s)" size="small" type="warning" effect="plain">{{ effectTag(s) }}</el-tag>
          </button>
          <p v-if="!showsOnDay(d.key).length" class="day-empty">—</p>
        </div>
      </div>
      <p v-if="!weekShows.length" class="empty">{{ showWeekViewEmpty }}</p>
    </template>

    <template v-else>
      <div class="list">
        <article v-for="s in list" :key="s.id" class="card item">
          <div>
            <strong>{{ s.title }}</strong>
            <el-tag v-if="effectTag(s)" size="small" type="warning" effect="plain" class="hall-tag">
              {{ effectTag(s) }}
            </el-tag>
            <div class="muted">
              {{ s.isbn || '—' }}
              <template v-if="s.categoryName"> · {{ s.categoryName }}</template>
              <template v-if="s.startAt"> · {{ s.startAt }}</template>
              · 票价 ¥{{ s.author || 0 }}
              · 座位 {{ s.seatRows || 6 }}×{{ s.seatCols || 8 }}
              · 余座 {{ s.stock }}
            </div>
          </div>
          <el-button type="primary" @click="go(s.id)">选座</el-button>
        </article>
      </div>
      <div v-if="!list.length" class="empty">
        暂无开放场次。{{ soldOutHint ? `${soldOutLabel}的场次不再展示。` : '' }}
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import http from '../api/http'
import { getSchema } from '../utils/domainSchema'

const router = useRouter()
const list = ref([])
const mode = ref('list')
const weekStart = ref(startOfWeek(new Date()))
const labels = computed(() => getSchema().labels || {})
const thicken = computed(() => getSchema().tradeThicken || {})
const title = computed(() => labels.value.seatShowsTitle || '场次选座')
const soldOutLabel = computed(() => labels.value.showSoldOutLabel || '已售罄')
const soldOutHint = computed(() => labels.value.showSoldOutHint || '')
const lead = computed(
  () => labels.value.seatShowsLead || '选择场次后进入座位图，确认购票后出票。开场后该场次不再售票。',
)
const weekOn = computed(() => !!thicken.value.showWeekView)
const showWeekViewLabel = computed(() => labels.value.showWeekViewLabel || '周视图')
const showWeekViewEmpty = computed(() => labels.value.showWeekViewEmpty || '本周暂无场次')
const comboOn = computed(() => !!thicken.value.cinemaCombo)
const cinemaComboLabel = computed(() => labels.value.cinemaComboLabel || '连场套票')
const cinemaComboBody = computed(() => labels.value.cinemaComboBody || '')
const effectHallLabel = computed(() => labels.value.effectHallLabel || '特效厅')
const effectHallImax = computed(() => labels.value.effectHallImax || 'IMAX')

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

function effectTag(s) {
  if (!thicken.value.effectHall) return ''
  const name = String(s?.categoryName || '')
  if (!name) return ''
  if (name.includes(effectHallImax.value) || /IMAX|巨幕|杜比/i.test(name)) {
    return name.includes(effectHallImax.value) ? `${effectHallLabel.value}·${effectHallImax.value}` : `${effectHallLabel.value}·${name}`
  }
  return ''
}

function shiftWeek(n) {
  const d = new Date(weekStart.value)
  d.setDate(d.getDate() + n * 7)
  weekStart.value = d
}

function goToday() {
  weekStart.value = startOfWeek(new Date())
}

async function load() {
  const res = await http.get('/api/seats/shows')
  list.value = res.data?.data || res.data || []
}

function go(id) {
  router.push(`/seats/map/${id}`)
}

onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 1rem; }
.hero-row { display: flex; gap: 1rem; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; }
.tools { flex-shrink: 0; }
.combo { color: var(--el-text-color-regular); font-size: 0.92rem; margin: 0.4rem 0 0; }
.list { display: grid; gap: 0.75rem; }
.item { padding: 1rem; display: flex; gap: 1rem; align-items: center; justify-content: space-between; flex-wrap: wrap; }
.muted { color: var(--el-text-color-secondary); font-size: 0.9rem; margin-top: 0.25rem; }
.hall-tag { margin-left: 0.5rem; vertical-align: middle; }
.empty { color: var(--el-text-color-secondary); }
.week-tools { display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap; margin-bottom: 0.75rem; }
.range { color: var(--el-text-color-secondary); margin-left: 0.5rem; }
.week-grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 0.5rem;
}
.day-col {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  padding: 0.5rem;
  min-height: 8rem;
}
.day-head { margin-bottom: 0.4rem; }
.dow { font-weight: 600; font-size: 0.9rem; }
.date { color: var(--el-text-color-secondary); font-size: 0.8rem; }
.chip {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.2rem;
  width: 100%;
  text-align: left;
  border: 1px solid var(--el-border-color);
  background: #fff;
  border-radius: 4px;
  padding: 0.35rem 0.4rem;
  margin-bottom: 0.35rem;
  cursor: pointer;
  font-size: 0.78rem;
  line-height: 1.3;
}
.chip:hover { border-color: var(--el-color-primary); }
.day-empty { color: var(--el-text-color-placeholder); font-size: 0.8rem; margin: 0; }
@media (max-width: 900px) {
  .week-grid { grid-template-columns: 1fr; }
}
</style>
