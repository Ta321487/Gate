<template>
  <div>
    <section class="hero">
      <div class="hero-row">
        <div>
          <h1>{{ title }}</h1>
          <p>只读周视图；点击格子查看{{ ticketNoun }}详情。不支持拖拽改期。</p>
        </div>
        <div class="tools">
          <el-button @click="shiftWeek(-1)">上一周</el-button>
          <el-button @click="goToday">本周</el-button>
          <el-button @click="shiftWeek(1)">下一周</el-button>
          <el-button @click="load">刷新</el-button>
        </div>
      </div>
      <p class="range">{{ rangeText }}</p>
    </section>

    <div class="grid" v-loading="loading">
      <div class="head">
        <div class="cell time">时段</div>
        <div v-for="d in days" :key="d.key" class="cell day">
          <div class="dow">{{ d.dow }}</div>
          <div class="date">{{ d.label }}</div>
        </div>
      </div>
      <div v-for="slot in slots" :key="slot" class="row">
        <div class="cell time">{{ slot }}</div>
        <div v-for="d in days" :key="d.key + slot" class="cell body">
          <button
            v-for="ev in eventsAt(d.key, slot)"
            :key="ev.id"
            type="button"
            class="ev"
            @click="open(ev)"
          >{{ ev.title }}</button>
        </div>
      </div>
    </div>

    <p v-if="!loading && !events.length" class="empty">本周暂无带时段的{{ ticketNoun }}。</p>

    <el-dialog v-model="detailVisible" :title="detail?.title || '详情'" width="420px" destroy-on-close>
      <template v-if="detail">
        <p class="sub">状态：{{ statusText(detail.status) }}</p>
        <p class="sub">时段：{{ detail.startAt || '—' }} ~ {{ detail.endAt || '—' }}</p>
        <p class="sub" v-if="detail.typeName">类型：{{ detail.typeName }}</p>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import http from '../../api/http'
import { ticketCopy } from '../../utils/domainSchema.js'

const ticket = ticketCopy()
const title = computed(() => ticket.weekCalendarLabel || '我的日程')
const ticketNoun = computed(() => ticket.label || ticket.labelPlural || '记录')
const states = computed(() => ticket.states || {})

const loading = ref(false)
const events = ref([])
const weekStart = ref(startOfWeek(new Date()))
const detailVisible = ref(false)
const detail = ref(null)

const slots = ['08:00', '10:00', '12:00', '14:00', '16:00', '18:00', '20:00']
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
  const list = []
  for (let i = 0; i < 7; i++) {
    const d = new Date(weekStart.value)
    d.setDate(d.getDate() + i)
    list.push({
      key: fmtDate(d),
      dow: `周${DOW[i]}`,
      label: `${d.getMonth() + 1}/${d.getDate()}`,
    })
  }
  return list
})

const rangeText = computed(() => {
  const a = days.value[0]
  const b = days.value[6]
  return `${a?.key || ''} ~ ${b?.key || ''}`
})

function statusText(s) {
  return states.value[s] || s
}

function shiftWeek(n) {
  const d = new Date(weekStart.value)
  d.setDate(d.getDate() + n * 7)
  weekStart.value = d
}

function goToday() {
  weekStart.value = startOfWeek(new Date())
}

function parseHour(s) {
  if (!s) return null
  const m = String(s).match(/(\d{1,2}):(\d{2})/)
  if (!m) return null
  return Number(m[1])
}

function eventsAt(dayKey, slotLabel) {
  const hour = Number(slotLabel.slice(0, 2))
  return events.value.filter((ev) => {
    if (!ev.startAt || !String(ev.startAt).startsWith(dayKey)) return false
    const h = parseHour(ev.startAt)
    if (h == null) return false
    return h >= hour && h < hour + 2
  })
}

function open(ev) {
  detail.value = ev
  detailVisible.value = true
}

async function load() {
  loading.value = true
  try {
    const res = await http.get('/api/tickets', { params: { page: 1, size: 200 } })
    const list = res.data?.list || []
    events.value = list.filter((x) => x.startAt && x.endAt)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 16px; }
.hero-row { display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.hero h1 { margin: 0 0 6px; font-size: 22px; }
.hero p { margin: 0; color: #64748b; font-size: 13px; }
.range { margin: 10px 0 0; font-size: 13px; color: #0f766e; }
.tools { display: flex; gap: 8px; flex-wrap: wrap; }
.grid {
  background: var(--portal-surface, #fff);
  border: var(--portal-border-width, 1px) solid var(--portal-line, #e2e8f0);
  border-radius: var(--portal-radius, 12px);
  box-shadow: var(--portal-shadow, none);
  overflow: auto;
}
.head, .row { display: grid; grid-template-columns: 64px repeat(7, minmax(100px, 1fr)); min-width: 820px; }
.cell {
  border-bottom: 1px solid #f1f5f9;
  border-right: 1px solid #f1f5f9;
  padding: 8px;
  min-height: 56px;
}
.cell.time { color: #64748b; font-size: 12px; background: #f8fafc; }
.head .cell { background: #f8fafc; font-size: 12px; text-align: center; }
.dow { font-weight: 600; color: #0f172a; }
.date { color: #64748b; margin-top: 2px; }
.ev {
  display: block;
  width: 100%;
  text-align: left;
  border: 0;
  border-radius: var(--portal-radius-sm, 6px);
  background: #e0f2fe;
  color: #0369a1;
  font-size: 12px;
  padding: 4px 6px;
  margin-bottom: 4px;
  cursor: pointer;
  line-height: 1.3;
}
.ev:hover { background: #bae6fd; }
.empty { text-align: center; color: #94a3b8; padding: 28px 0; }
.sub { margin: 0 0 8px; color: #475569; font-size: 14px; }
</style>
