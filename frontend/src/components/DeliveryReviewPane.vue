<template>
  <div class="delivery-review stack">
    <div class="row-between" style="align-items:flex-start">
      <div>
        <div class="small">
          <span class="pill" :class="statusPill">{{ statusLabel }}</span>
          <span v-if="review.round" class="muted" style="margin-left:8px">第 {{ review.round }} 轮</span>
        </div>
        <p class="small muted" style="margin:8px 0 0">
          对照开题材料收窄偏差：已通过项纳入安全区；验圈通过后方可合卷更新交付包。
        </p>
        <p v-if="metrics.first_pack_direct === true" class="small muted" style="margin:4px 0 0">
          首包直发 · 尚未进入复审
        </p>
        <p v-else-if="metrics.first_pack_direct === false" class="small muted" style="margin:4px 0 0">
          已合卷 {{ metrics.repack_count || 0 }} 次
        </p>
      </div>
      <div class="row" style="margin:0;flex-wrap:wrap;justify-content:flex-end">
        <n-button size="small" :disabled="disabled || busy" @click="onStart" v-if="review.status !== 'active'">
          进入复审
        </n-button>
        <n-button size="small" :disabled="disabled || busy" :loading="busy === 'verify'" @click="onVerify">
          验圈
        </n-button>
        <n-button
          size="small"
          type="primary"
          :disabled="disabled || !canRepack"
          :loading="busy === 'repack'"
          @click="onRepack"
        >
          合卷
        </n-button>
        <n-button size="small" :disabled="disabled || busy" :loading="busy === 'qa'" @click="onQa">
          质量摘要
        </n-button>
        <n-button
          v-if="review.status === 'active'"
          size="small"
          :disabled="disabled || busy"
          :loading="busy === 'close'"
          @click="onClose"
        >
          结束复审
        </n-button>
        <n-button size="small" :disabled="disabled" tag="a" :href="handoffUrl" target="_blank">
          导出交接包
        </n-button>
      </div>
    </div>

    <n-alert v-if="zipStale" type="warning" :bordered="false" title="交付包未同步">
      工程已变更，当前 ZIP 与 workspace 不一致。请完成验圈后执行合卷。
    </n-alert>
    <n-alert v-if="openNotes.length && !regressions.length" type="warning" :bordered="false" title="仍有未结案偏差登记">
      请先处理或结案后再合卷（{{ openNotes.length }} 条）
    </n-alert>
    <n-alert v-if="regressions.length" type="error" :bordered="false" title="检测到安全区回退">
      <ul class="reg-list">
        <li v-for="(r, i) in regressions" :key="i">{{ r.message }}</li>
      </ul>
    </n-alert>

    <div class="review-grid">
      <div class="review-panel">
        <div class="parse-sec-hd">安全区 · 已通过</div>
        <n-empty v-if="!safeZone.length" description="尚无冻结项" size="small" />
        <ul v-else class="zone-list">
          <li v-for="item in safeZone" :key="item.name">{{ item.name }}</li>
        </ul>
      </div>
      <div class="review-panel">
        <div class="parse-sec-hd">待收敛 · 毒区</div>
        <n-empty v-if="!poisonZone.length" description="暂无待处理项" size="small" />
        <ul v-else class="zone-list">
          <li v-for="item in poisonZone" :key="item.name">{{ item.name }}</li>
        </ul>
      </div>
    </div>

    <div v-if="fixNotes.length" class="fix-notes-panel">
      <div class="parse-sec-hd row-between" style="align-items:center">
        <span>偏差登记 · {{ openNotes.length }} 条待结案</span>
        <n-button
          v-if="doneNotes.length"
          text
          size="tiny"
          @click="showDoneNotes = !showDoneNotes"
        >
          {{ showDoneNotes ? '隐藏' : '显示' }}已结案（{{ doneNotes.length }}）
        </n-button>
      </div>
      <ul class="fix-note-list">
        <li v-for="n in visibleFixNotes" :key="n.id" class="fix-note-item">
          <div class="fix-note-body">
            <span class="fix-note-status" :class="n.status === 'done' ? 'done' : 'open'">
              {{ n.status === 'done' ? '已结案' : '待处理' }}
            </span>
            <span class="fix-note-text">{{ n.text }}</span>
          </div>
          <div class="fix-note-actions">
            <n-button
              v-if="n.status !== 'done'"
              size="tiny"
              type="primary"
              :disabled="disabled || !!busy"
              :loading="busy === `note-${n.id}`"
              @click="onResolveNote(n.id, true)"
            >
              结案
            </n-button>
            <n-button
              v-else
              size="tiny"
              quaternary
              :disabled="disabled || !!busy"
              :loading="busy === `note-${n.id}`"
              @click="onResolveNote(n.id, false)"
            >
              重开
            </n-button>
          </div>
        </li>
      </ul>
    </div>

    <div class="review-note-row">
      <n-input
        v-model:value="noteText"
        type="textarea"
        :autosize="{ minRows: 2, maxRows: 4 }"
        placeholder="登记与开题或材料不一致之处（仅运营可见，不进学生交付包）"
        :disabled="disabled || busy"
      />
      <n-button size="small" type="primary" :disabled="disabled || !noteText.trim() || busy" @click="onAddNote">
        登记偏差
      </n-button>
    </div>

    <div v-if="rounds.length">
      <div class="parse-sec-hd mt-12">轮次记录</div>
      <n-data-table size="small" :bordered="false" :columns="roundCols" :data="rounds" :max-height="220" />
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { NAlert, NButton, NDataTable, NEmpty, NInput } from 'naive-ui'
import { api, message } from '../api'

const props = defineProps({
  projectId: { type: String, required: true },
  deliveryReview: { type: Object, default: () => ({}) },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['refresh'])

const busy = ref('')
const noteText = ref('')
const localRegressions = ref([])
const showDoneNotes = ref(false)

const review = computed(() => props.deliveryReview?.review || {})
const zones = computed(() => props.deliveryReview?.zones || {})
const safeZone = computed(() => zones.value.safe_zone || [])
const poisonZone = computed(() => zones.value.poison_zone || [])
const fixNotes = computed(() => {
  const raw = review.value.fix_notes
  return Array.isArray(raw) ? [...raw].reverse() : []
})
const openNotes = computed(() => fixNotes.value.filter((n) => n.status !== 'done'))
const doneNotes = computed(() => fixNotes.value.filter((n) => n.status === 'done'))
const visibleFixNotes = computed(() => {
  if (showDoneNotes.value) return fixNotes.value
  return openNotes.value.length ? openNotes.value : fixNotes.value
})
const zipStale = computed(() => !!props.deliveryReview?.zip_stale)
const rounds = computed(() => [...(review.value.rounds || [])].reverse())

const regressions = computed(() => {
  const last = review.value.last_verify?.regressions
  if (localRegressions.value.length) return localRegressions.value
  return Array.isArray(last) ? last : []
})

const statusLabel = computed(() => {
  const s = review.value.status || 'idle'
  if (s === 'active') return '复审进行中'
  if (s === 'closed') return '复审已结束'
  return '未进入复审'
})

const statusPill = computed(() => {
  const s = review.value.status || 'idle'
  if (s === 'active') return 'pill-amber'
  if (s === 'closed') return 'pill-neutral'
  return 'pill-neutral'
})

const canRepack = computed(() => {
  if (props.disabled || busy.value) return false
  if (regressions.value.length) return false
  if (openNotes.value.length) return false
  const rounds = review.value.rounds || []
  const lastRound = rounds.length ? rounds[rounds.length - 1] : null
  if (!lastRound?.round_pass) return false
  if (lastRound.monotonic_ok === false) return false
  return true
})

const metrics = computed(() => props.deliveryReview?.metrics || {})

const handoffUrl = computed(() => api.deliveryHandoffUrl(props.projectId))

const roundCols = [
  { title: '轮次', key: 'round', width: 56 },
  {
    title: '单调性',
    key: 'monotonic_ok',
    width: 80,
    render: (r) => (r.monotonic_ok ? '通过' : '回退'),
  },
  { title: '门禁', key: 'gates_ok', width: 72, render: (r) => (r.gates_ok ? '通过' : '未过') },
  { title: '待收敛', key: 'pending_count', width: 72 },
  { title: '时间', key: 'at', ellipsis: { tooltip: true } },
]

async function onStart() {
  busy.value = 'start'
  try {
    await api.startDeliveryReview(props.projectId)
    message.success('已进入交付复审')
    emit('refresh')
  } catch (e) {
    message.error(e?.response?.data?.detail || e?.message || '进入复审失败')
  } finally {
    busy.value = ''
  }
}

async function onVerify() {
  busy.value = 'verify'
  localRegressions.value = []
  try {
    const res = await api.verifyDeliveryReview(props.projectId)
    localRegressions.value = res.regressions || []
    if (res.monotonic_ok && res.round_pass) {
      message.success('验圈通过 · 可执行合卷')
    } else if (!res.monotonic_ok) {
      message.warning('验圈未通过 · 存在安全区回退')
    } else {
      message.info('验圈完成 · 仍有待收敛项')
    }
    emit('refresh')
  } catch (e) {
    message.error(e?.response?.data?.detail || e?.message || '验圈失败')
  } finally {
    busy.value = ''
  }
}

async function onRepack() {
  busy.value = 'repack'
  try {
    await api.repackDeliveryReview(props.projectId)
    message.success('合卷完成 · 交付包已更新')
    emit('refresh')
  } catch (e) {
    message.error(e?.response?.data?.detail || e?.message || '合卷失败')
  } finally {
    busy.value = ''
  }
}

async function onQa() {
  busy.value = 'qa'
  try {
    const res = await api.runDeliveryQa(props.projectId)
    if (res.qa?.ok) message.success('质量摘要已通过')
    else message.warning('质量摘要存在 error 级问题')
    emit('refresh')
  } catch (e) {
    message.error(e?.response?.data?.detail || e?.message || '质量摘要失败')
  } finally {
    busy.value = ''
  }
}

async function onClose() {
  busy.value = 'close'
  try {
    await api.closeDeliveryReview(props.projectId)
    message.success('已结束交付复审')
    emit('refresh')
  } catch (e) {
    message.error(e?.response?.data?.detail || e?.message || '结束复审失败')
  } finally {
    busy.value = ''
  }
}

async function onAddNote() {
  const text = noteText.value.trim()
  if (!text) return
  busy.value = 'note'
  try {
    await api.addDeliveryFixNote(props.projectId, text)
    noteText.value = ''
    showDoneNotes.value = false
    message.success('已登记偏差')
    emit('refresh')
  } finally {
    busy.value = ''
  }
}

async function onResolveNote(noteId, done) {
  if (!noteId || busy.value) return
  busy.value = `note-${noteId}`
  try {
    await api.resolveDeliveryFixNote(props.projectId, noteId, done)
    message.success(done ? '已结案' : '已重开')
    emit('refresh')
  } catch (e) {
    message.error(e?.response?.data?.detail || e?.message || '操作失败')
  } finally {
    busy.value = ''
  }
}
</script>

<style scoped>
.delivery-review .review-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
@media (max-width: 720px) {
  .delivery-review .review-grid {
    grid-template-columns: 1fr;
  }
}
.review-panel {
  border: 1px solid var(--border, #e8e8e8);
  border-radius: 8px;
  padding: 10px 12px;
  min-height: 120px;
}
.zone-list {
  margin: 8px 0 0;
  padding-left: 18px;
  font-size: 13px;
}
.note-li {
  color: var(--text-muted, #666);
}
.fix-notes-panel {
  border: 1px solid var(--border, #e8e8e8);
  border-radius: 8px;
  padding: 10px 12px;
  margin-top: 4px;
}
.fix-note-list {
  list-style: none;
  margin: 8px 0 0;
  padding: 0;
}
.fix-note-item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid var(--border, #f0f0f0);
  font-size: 13px;
}
.fix-note-item:last-child {
  border-bottom: none;
}
.fix-note-body {
  flex: 1;
  min-width: 0;
}
.fix-note-status {
  display: inline-block;
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 4px;
  margin-right: 6px;
  vertical-align: middle;
}
.fix-note-status.open {
  background: #fff7e6;
  color: #ad6800;
}
.fix-note-status.done {
  background: #f6ffed;
  color: #389e0d;
}
.fix-note-text {
  word-break: break-word;
}
.fix-note-actions {
  flex-shrink: 0;
}
.review-note-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 4px;
}
.reg-list {
  margin: 4px 0 0;
  padding-left: 18px;
}
.pill-amber {
  background: #fff7e6;
  color: #ad6800;
}
</style>
