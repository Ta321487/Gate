<template>
  <div
    class="long-op-wait"
    role="status"
    aria-live="polite"
    :aria-busy="true"
    :aria-label="title"
  >
    <div class="row-between" style="margin-bottom:8px;align-items:baseline;gap:8px">
      <div style="font-weight:600">{{ title }}</div>
      <div class="small muted">已等待 {{ elapsedLabel }}</div>
    </div>
    <div class="sub-progress" aria-hidden="true"><i /></div>
    <ol v-if="phases.length" class="long-op-phases">
      <li
        v-for="(ph, i) in phases"
        :key="ph.key || i"
        :class="phaseClass(i)"
      >
        <span class="long-op-mark" aria-hidden="true">{{ phaseMark(i) }}</span>
        <span>{{ ph.label }}</span>
      </li>
    </ol>
    <p class="small muted" style="margin:10px 0 0">{{ liveHint }}</p>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'

const props = defineProps({
  /** 主标题，如「正在验收…」 */
  title: { type: String, default: '仍在运行…' },
  /** { key, label }[] 阶段；无则只显示不确定进度条 */
  phases: { type: Array, default: () => [] },
  /** 覆盖底部提示；空则按阶段自动生成 */
  hint: { type: String, default: '' },
  /** 各阶段大致秒数（用于推进高亮，非真实服务端进度） */
  phaseSeconds: { type: Array, default: () => [] },
  /** 外部已等待毫秒（刷新恢复时用） */
  startedAt: { type: Number, default: 0 },
})

const now = ref(Date.now())
const mountAt = ref(Date.now())
let tick = null

onMounted(() => {
  mountAt.value = Date.now()
  tick = window.setInterval(() => {
    now.value = Date.now()
  }, 1000)
})

onUnmounted(() => {
  if (tick) window.clearInterval(tick)
})

watch(
  () => props.startedAt,
  (v) => {
    now.value = Date.now()
    if (!Number(v)) mountAt.value = Date.now()
  },
)

const baseAt = computed(() => {
  const t = Number(props.startedAt) || 0
  return t > 0 ? t : mountAt.value
})

const elapsedSec = computed(() => Math.max(0, Math.floor((now.value - baseAt.value) / 1000)))

const elapsedLabel = computed(() => {
  const s = elapsedSec.value
  if (s < 60) return `${s} 秒`
  const m = Math.floor(s / 60)
  const r = s % 60
  return `${m} 分 ${r} 秒`
})

const activeIndex = computed(() => {
  const n = props.phases.length
  if (!n) return -1
  const secs = props.phaseSeconds
  let acc = 0
  for (let i = 0; i < n; i += 1) {
    const step = Number(secs[i]) > 0 ? Number(secs[i]) : 25
    acc += step
    if (elapsedSec.value < acc) return i
  }
  return n - 1
})

function phaseClass(i) {
  const cur = activeIndex.value
  if (i < cur) return 'done'
  if (i === cur) return 'run'
  return 'wait'
}

function phaseMark(i) {
  const c = phaseClass(i)
  if (c === 'done') return '✓'
  if (c === 'run') return '…'
  return '·'
}

const liveHint = computed(() => {
  if (props.hint) return props.hint
  const cur = props.phases[activeIndex.value]
  const name = cur?.label || '当前步骤'
  return `${name}进行中`
})
</script>

<style scoped>
.long-op-wait {
  padding: 12px 0 4px;
}
.long-op-phases {
  list-style: none;
  margin: 12px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.long-op-phases li {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--muted, #6b7280);
}
.long-op-phases li.run {
  color: var(--text, #111827);
  font-weight: 600;
}
.long-op-phases li.done {
  color: var(--teal, #0f766e);
}
.long-op-mark {
  width: 1.1em;
  text-align: center;
  font-variant-numeric: tabular-nums;
}
</style>
