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
        <span v-if="review.status !== 'active'" :title="tipStart" class="btn-tip-wrap">
          <n-button
            size="small"
            :disabled="disabled || !!busy"
            :loading="busy === 'start'"
            @click="onStart"
          >
            进入复审
          </n-button>
        </span>
        <span :title="tipVerify" class="btn-tip-wrap">
          <n-button
            size="small"
            :disabled="disabled || !!busy"
            :loading="busy === 'verify'"
            @click="onVerify"
          >
            验圈
          </n-button>
        </span>
        <span
          v-if="showScrubCopy"
          title="调用工厂 scrub（与出包同源），不必手改学生包"
          class="btn-tip-wrap"
        >
          <n-button
            size="small"
            type="primary"
            :disabled="disabled || !!busy || scrubBusy"
            :loading="scrubBusy"
            @click="onScrubCopy"
          >
            工厂清洗文案
          </n-button>
        </span>
        <span :title="repackTip" class="btn-tip-wrap">
          <n-button
            size="small"
            type="primary"
            :disabled="disabled || !canRepack"
            :loading="busy === 'repack'"
            @click="onRepack"
          >
            合卷
          </n-button>
        </span>
        <span :title="tipQa" class="btn-tip-wrap">
          <n-button
            size="small"
            :disabled="disabled || !!busy"
            :loading="busy === 'qa'"
            @click="onQa"
          >
            质量摘要
          </n-button>
        </span>
        <span v-if="review.status === 'active'" :title="tipClose" class="btn-tip-wrap">
          <n-button
            size="small"
            :disabled="disabled || !!busy"
            :loading="busy === 'close'"
            @click="onClose"
          >
            结束复审
          </n-button>
        </span>
        <span :title="tipHandoff" class="btn-tip-wrap">
          <n-button
            size="small"
            :disabled="disabled"
            tag="a"
            :href="handoffUrl"
            target="_blank"
          >
            导出交接包
          </n-button>
        </span>
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
    <n-alert
      v-if="(blockingGates || []).length && !(regressions || []).length"
      type="warning"
      :bordered="false"
      title="清单已收敛，但质量门禁未过"
    >
      毒区只列实装清单；页头「质检未过」通常卡在下面这些门禁（含交付质量摘要）。修复后再点验圈。
      <ul class="reg-list">
        <li v-for="g in blockingGates" :key="g.key || g.label">
          {{ g.label }}<span v-if="g.desc" class="muted"> · {{ g.desc }}</span>
        </li>
      </ul>
      <p v-if="showScrubCopy" class="small muted" style="margin:8px 0 0">
        工厂腔或「演示」口吻未过时，用上方「工厂清洗文案」即可（会按现网骨架覆写脏 Vue），不必手改学生包。
      </p>
    </n-alert>

    <div class="diag-grid">
      <div class="review-panel boss-card-panel">
        <div class="parse-sec-hd row-between" style="align-items:center">
          <span>老板小卡 · 感觉不对时对着勾</span>
          <n-button text size="tiny" :disabled="disabled" @click="resetBossChecks">清空勾选</n-button>
        </div>
        <p class="small muted" style="margin:6px 0 8px">
          勾选仅保存在本机浏览器，对照右侧毒区 / 验圈 / 质量摘要。机器全绿仍可能理解错——对着开题核。
          <router-link to="/help#help-card-四痛点">帮助 · 四痛点</router-link>
        </p>
        <div class="boss-check-list">
          <n-checkbox
            v-for="item in bossItems"
            :key="item.key"
            :checked="!!bossChecks[item.key]"
            :disabled="disabled"
            style="display:flex;align-items:flex-start;margin:0 0 8px"
            @update:checked="(v) => setBossCheck(item.key, v)"
          >
            <span class="boss-check-label">{{ item.label }}</span>
          </n-checkbox>
        </div>
        <n-alert
          v-if="understandGapHint"
          type="warning"
          :bordered="false"
          style="margin-top:8px"
          title="机器绿 ≠ 写对了"
        >
          已勾「理解偏差」且毒区/挡包门禁为空：对照开题核域、主路径、皮与种子，修工厂；登记偏差写「工厂理解偏差」，禁止甩锅「材料薄」。
        </n-alert>
      </div>
      <div class="review-panel diag-side-panel">
        <div class="parse-sec-hd">机器毒区 · 验圈 / QA</div>
        <div class="diag-side-block">
          <div class="small" style="font-weight:600;margin-bottom:4px">待收敛 · 毒区（{{ poisonZone.length }}）</div>
          <n-empty v-if="!poisonZone.length" description="暂无待处理清单项" size="small" />
          <ul v-else class="zone-list">
            <li v-for="item in poisonZone" :key="'p-' + item.name">{{ item.name }}</li>
          </ul>
        </div>
        <div class="diag-side-block">
          <div class="small" style="font-weight:600;margin-bottom:4px">挡包门禁（{{ blockingGates.length }}）</div>
          <n-empty v-if="!blockingGates.length" description="无未过门禁" size="small" />
          <ul v-else class="zone-list">
            <li v-for="g in blockingGates" :key="'g-' + (g.key || g.label)">
              {{ g.label }}<span v-if="g.desc" class="muted"> · {{ g.desc }}</span>
            </li>
          </ul>
        </div>
        <div class="diag-side-block">
          <div class="small" style="font-weight:600;margin-bottom:4px">最近验圈</div>
          <p v-if="lastVerifySummary" class="small" style="margin:0">{{ lastVerifySummary }}</p>
          <p v-else class="small muted" style="margin:0">尚未验圈</p>
        </div>
        <div class="diag-side-block">
          <div class="small row-between" style="font-weight:600;margin-bottom:4px;align-items:center">
            <span>质量摘要（QA）</span>
            <n-button text size="tiny" :disabled="disabled || !!busy" :loading="busy === 'qa'" @click="onQa">
              重跑
            </n-button>
          </div>
          <p v-if="lastQa?.summary" class="small" style="margin:0 0 6px">{{ lastQa.summary }}</p>
          <p v-else class="small muted" style="margin:0">尚无摘要 · 可点验圈或「质量摘要」</p>
          <ul v-if="lastQaFindings.length" class="zone-list">
            <li v-for="(f, i) in lastQaFindings" :key="'qa-' + i">
              <span class="pill" :class="qaLevelPill(f.level)">{{ f.level || 'info' }}</span>
              {{ f.msg }}<span v-if="f.where" class="muted"> · {{ f.where }}</span>
            </li>
          </ul>
        </div>
      </div>
    </div>

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
        placeholder="登记工厂与开题不一致之处（写「工厂理解偏差」；禁止甩锅材料薄。仅运营可见）"
        :disabled="disabled || !!busy"
      />
      <n-button size="small" type="primary" :disabled="disabled || !noteText.trim() || !!busy" @click="onAddNote">
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
import { computed, ref, watch } from 'vue'
import { NAlert, NButton, NCheckbox, NDataTable, NEmpty, NInput } from 'naive-ui'
import { api, message } from '../api'

const props = defineProps({
  projectId: { type: String, required: true },
  deliveryReview: { type: Object, default: () => ({}) },
  disabled: { type: Boolean, default: false },
  /** 可选：返回 Promise 的刷新函数；有则 await，避免 busy 过早清空导致连点 */
  reload: { type: Function, default: null },
  /** 与质量检查同源：父级 scrubStudentCopy / copyGateNeedsScrub */
  showScrubCopy: { type: Boolean, default: false },
  scrubBusy: { type: Boolean, default: false },
  scrubCopy: { type: Function, default: null },
})

const emit = defineEmits(['refresh'])

const busy = ref('')
const noteText = ref('')
const localRegressions = ref([])
const showDoneNotes = ref(false)

const BOSS_ITEMS = [
  { key: 'shell', label: '1. 有没有空壳（宣称有、缺表/API/状态机）？' },
  { key: 'regress', label: '2. 旧题（图书/宿舍/实习等）回归红了吗？' },
  { key: 'fsm', label: '3. 状态机对且准吗（集合/转移/角色/文案）？' },
  { key: 'fields', label: '4. 字段可见含义像本题吗（有无壳字段穿帮）？' },
  { key: 'flow', label: '5. 客户会不会看错主流程（「我的」/种子/按钮诱导）？' },
  { key: 'steal', label: '6. 新域有没有抢走旧题匹配？' },
  { key: 'demo', label: '7. 学生可见面有没有「演示」字样？' },
  { key: 'rewrite', label: '8. 开题有没有被改来迁就工厂？' },
  { key: 'reject', label: '9. 该 reject 的硬边界还拒不拒？' },
  { key: 'thesis', label: '10. 论文图（ER/模块/用例）跟实包一致吗？' },
  { key: 'skin', label: '11. 皮肤/布局选项进包生效了吗？' },
  { key: 'scene', label: '12. 登录氛围与门户轮播分套、身份跟场景吗？' },
  { key: 'understand_gap', label: '理解偏差：老师已确认的主路径/域，工厂写对了吗？（禁止甩锅开题套话）' },
]

const bossItems = BOSS_ITEMS
const bossChecks = ref({})

function bossStorageKey(id) {
  return `gf-boss-card:${id || ''}`
}

function loadBossChecks(id) {
  try {
    const raw = localStorage.getItem(bossStorageKey(id))
    const parsed = raw ? JSON.parse(raw) : {}
    bossChecks.value = parsed && typeof parsed === 'object' ? parsed : {}
  } catch {
    bossChecks.value = {}
  }
}

function persistBossChecks() {
  try {
    localStorage.setItem(bossStorageKey(props.projectId), JSON.stringify(bossChecks.value || {}))
  } catch {
    /* ignore quota */
  }
}

function setBossCheck(key, checked) {
  bossChecks.value = { ...bossChecks.value, [key]: !!checked }
  persistBossChecks()
}

function resetBossChecks() {
  bossChecks.value = {}
  persistBossChecks()
}

watch(
  () => props.projectId,
  (id) => loadBossChecks(id),
  { immediate: true },
)

async function refreshAfter() {
  if (typeof props.reload === 'function') {
    await props.reload()
    return
  }
  emit('refresh')
}

function formatAt(raw) {
  if (!raw) return '—'
  const d = new Date(raw)
  if (Number.isNaN(d.getTime())) return String(raw)
  return d.toLocaleString()
}

const review = computed(() => props.deliveryReview?.review || {})
const zones = computed(() => props.deliveryReview?.zones || {})
const safeZone = computed(() => zones.value.safe_zone || [])
const poisonZone = computed(() => zones.value.poison_zone || [])
const blockingGates = computed(() => {
  const raw = props.deliveryReview?.blocking_gates
  return Array.isArray(raw) ? raw.filter((x) => x && typeof x === 'object') : []
})
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

const lastQa = computed(() => {
  const qa = review.value.last_qa
  return qa && typeof qa === 'object' ? qa : null
})

const lastQaFindings = computed(() => {
  const raw = lastQa.value?.findings
  if (!Array.isArray(raw)) return []
  return raw.slice(0, 8)
})

const lastVerifySummary = computed(() => {
  const last = review.value.last_verify
  if (!last || typeof last !== 'object') {
    const rounds = review.value.rounds || []
    const r = rounds.length ? rounds[rounds.length - 1] : null
    if (!r) return ''
    const parts = [
      `第 ${r.round || '—'} 轮`,
      r.round_pass ? '通过' : '未过',
      r.monotonic_ok === false ? '单调性回退' : null,
      r.gates_ok ? '门禁过' : '门禁未过',
      typeof r.pending_count === 'number' ? `待收敛 ${r.pending_count}` : null,
      r.at ? formatAt(r.at) : null,
    ].filter(Boolean)
    return parts.join(' · ')
  }
  const parts = [
    last.round_pass ? '通过' : '未过',
    last.monotonic_ok === false ? '单调性回退' : null,
    Array.isArray(last.regressions) && last.regressions.length
      ? `回退 ${last.regressions.length} 条`
      : null,
  ].filter(Boolean)
  return parts.join(' · ') || '已有验圈记录'
})

const understandGapHint = computed(() => {
  if (!bossChecks.value.understand_gap) return false
  return !poisonZone.value.length && !blockingGates.value.length
})

function qaLevelPill(level) {
  const l = String(level || '').toLowerCase()
  if (l === 'error') return 'pill-rose'
  if (l === 'warn' || l === 'warning') return 'pill-amber'
  return 'pill-neutral'
}

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

const tipStart = '开始对照开题收窄偏差；可验圈、登记偏差'
const tipVerify = '本轮验收：重跑门禁与质量摘要；通过项进安全区，清单未过留毒区，门禁未过会单独提示'
const tipQa = '再跑一遍交付质检摘要（不替代门禁）'
const tipClose = '结束本轮复审流程（不删已有登记）'
const tipHandoff = '导出运营交接材料，不进学生 ZIP'

const repackTip = computed(() => {
  if (canRepack.value) return '验圈通过后更新交付 ZIP，使与工程一致'
  if (props.disabled) return '工程重新生成中或尚无工作区，暂不可合卷'
  if (busy.value) return '请等待当前操作完成'
  if (regressions.value.length) return '存在安全区回退，请先处理后再合卷'
  if (openNotes.value.length) return `仍有 ${openNotes.value.length} 条未结案偏差，请先结案后再合卷`
  if (blockingGates.value.length) {
    const labels = blockingGates.value
      .map((g) => (g && g.label) || '')
      .filter(Boolean)
      .slice(0, 3)
      .join('、')
    return `质量门禁未过（${labels || '见上方提示'}）· 修复后再验圈合卷`
  }
  const rounds = review.value.rounds || []
  const lastRound = rounds.length ? rounds[rounds.length - 1] : null
  if (!lastRound?.round_pass) return '请先完成验圈通过后再合卷'
  if (lastRound.monotonic_ok === false) return '验圈单调性未通过，暂不可合卷'
  return '暂不可合卷'
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
  {
    title: '时间',
    key: 'at',
    width: 168,
    ellipsis: { tooltip: true },
    render: (r) => formatAt(r.at),
  },
]

async function onStart() {
  if (busy.value || props.disabled) return
  busy.value = 'start'
  try {
    await api.startDeliveryReview(props.projectId)
    message.success('已进入交付复审')
    await refreshAfter()
  } catch (e) {
    message.error(e?.response?.data?.detail || e?.message || '进入复审失败')
  } finally {
    busy.value = ''
  }
}

async function onScrubCopy() {
  if (typeof props.scrubCopy === 'function') {
    await props.scrubCopy()
  }
}

async function onVerify() {
  if (busy.value || props.disabled) return
  busy.value = 'verify'
  localRegressions.value = []
  try {
    const raw = await api.verifyDeliveryReview(props.projectId)
    // 兼容直接模型 / { data } 包裹
    const res = raw && typeof raw === 'object' && raw.data && raw.monotonic_ok == null ? raw.data : raw
    const payload = res && typeof res === 'object' ? res : {}
    localRegressions.value = Array.isArray(payload.regressions) ? payload.regressions : []
    const blocked = Array.isArray(payload.blocking_gates) ? payload.blocking_gates : []
    const failReasons = Array.isArray(payload.fail_reasons) ? payload.fail_reasons.filter(Boolean) : []
    if (payload.monotonic_ok && payload.round_pass) {
      message.success('验圈通过 · 可执行合卷')
    } else if (!payload.monotonic_ok) {
      message.warning('验圈未通过 · 存在安全区回退')
    } else if (failReasons.length) {
      message.warning(`验圈未通过 · ${failReasons.join('；')}`)
    } else if (blocked.length) {
      const labels = blocked
        .map((g) => (g && g.label) || '')
        .filter(Boolean)
        .slice(0, 3)
        .join('、')
      message.warning(`验圈未通过 · 质量门禁未过${labels ? `（${labels}）` : ''}`)
    } else {
      const pending = Array.isArray(payload.pending_names) ? payload.pending_names.filter(Boolean) : []
      if (pending.length) {
        message.warning(`验圈未通过 · 待收敛清单：${pending.slice(0, 4).join('、')}`)
      } else {
        message.warning('验圈未通过 · 请查看毒区与「质量检查」页')
      }
    }
    await refreshAfter()
  } catch (e) {
    message.error(e?.response?.data?.detail || e?.message || '验圈失败')
  } finally {
    busy.value = ''
  }
}

async function onRepack() {
  if (busy.value || props.disabled || !canRepack.value) return
  busy.value = 'repack'
  try {
    await api.repackDeliveryReview(props.projectId)
    message.success('合卷完成 · 交付包已更新')
    await refreshAfter()
  } catch (e) {
    message.error(e?.response?.data?.detail || e?.message || '合卷失败')
  } finally {
    busy.value = ''
  }
}

async function onQa() {
  if (busy.value || props.disabled) return
  busy.value = 'qa'
  try {
    const res = await api.runDeliveryQa(props.projectId)
    if (res.qa?.ok) message.success('质量摘要已通过')
    else message.warning('质量摘要存在 error 级问题')
    await refreshAfter()
  } catch (e) {
    message.error(e?.response?.data?.detail || e?.message || '质量摘要失败')
  } finally {
    busy.value = ''
  }
}

async function onClose() {
  if (busy.value || props.disabled) return
  busy.value = 'close'
  try {
    await api.closeDeliveryReview(props.projectId)
    message.success('已结束交付复审')
    await refreshAfter()
  } catch (e) {
    message.error(e?.response?.data?.detail || e?.message || '结束复审失败')
  } finally {
    busy.value = ''
  }
}

async function onAddNote() {
  const text = noteText.value.trim()
  if (!text || busy.value || props.disabled) return
  busy.value = 'note'
  try {
    await api.addDeliveryFixNote(props.projectId, text)
    noteText.value = ''
    showDoneNotes.value = false
    message.success('已登记偏差')
    await refreshAfter()
  } finally {
    busy.value = ''
  }
}

async function onResolveNote(noteId, done) {
  if (!noteId || busy.value || props.disabled) return
  busy.value = `note-${noteId}`
  try {
    await api.resolveDeliveryFixNote(props.projectId, noteId, done)
    message.success(done ? '已结案' : '已重开')
    await refreshAfter()
  } catch (e) {
    message.error(e?.response?.data?.detail || e?.message || '操作失败')
  } finally {
    busy.value = ''
  }
}
</script>

<style scoped>
.delivery-review .review-grid,
.delivery-review .diag-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
@media (max-width: 720px) {
  .delivery-review .review-grid,
  .delivery-review .diag-grid {
    grid-template-columns: 1fr;
  }
}
.review-panel {
  border: 1px solid var(--border, #e8e8e8);
  border-radius: 8px;
  padding: 10px 12px;
  min-height: 120px;
}
.boss-check-list {
  max-height: 320px;
  overflow: auto;
  padding-right: 4px;
}
.boss-check-label {
  font-size: 12px;
  line-height: 1.45;
  white-space: normal;
}
.diag-side-block {
  padding: 8px 0;
  border-bottom: 1px solid var(--border, #f0f0f0);
}
.diag-side-block:last-child {
  border-bottom: none;
  padding-bottom: 0;
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
  gap: 8px;
  align-items: flex-start;
  margin-top: 8px;
}
.review-note-row .n-input {
  flex: 1;
}
.reg-list {
  margin: 6px 0 0;
  padding-left: 18px;
}
.btn-tip-wrap {
  display: inline-flex;
}
</style>
