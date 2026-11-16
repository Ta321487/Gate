<template>
  <div class="delivery-review stack">
    <div class="row-between" style="align-items:flex-start;gap:10px">
      <div>
        <div class="small">
          <span class="pill" :class="statusPill">{{ statusLabel }}</span>
          <span v-if="review.round" class="muted" style="margin-left:8px">第 {{ review.round }} 轮</span>
          <span v-if="metrics.first_pack_direct === true" class="muted" style="margin-left:8px">首包直发</span>
          <span v-else-if="metrics.first_pack_direct === false" class="muted" style="margin-left:8px">
            已重打包 {{ metrics.repack_count || 0 }} 次
          </span>
        </div>
        <p class="small muted" style="margin:6px 0 0">
          验收通过后可重打包；下载仍用上方就绪条。
        </p>
      </div>
      <div class="row" style="margin:0;flex-wrap:wrap;justify-content:flex-end;gap:6px">
        <span v-if="review.status !== 'active'" :title="tipStart" class="btn-tip-wrap">
          <n-button size="small" :disabled="disabled || !!busy" :loading="busy === 'start'" @click="onStart">
            进入复审
          </n-button>
        </span>
        <span :title="tipVerify" class="btn-tip-wrap">
          <n-button size="small" :disabled="disabled || !!busy" :loading="busy === 'verify'" @click="onVerify">
            验收
          </n-button>
        </span>
        <span
          v-if="showScrubCopy"
          title="调用工厂 scrub（与出包同源），不必手改学生包"
          class="btn-tip-wrap"
        >
          <n-button
            size="small"
            secondary
            :disabled="disabled || !!busy || scrubBusy"
            :loading="scrubBusy"
            @click="onScrubCopy"
          >
            清洗文案
          </n-button>
        </span>
        <span :title="repackTip" class="btn-tip-wrap">
          <n-button
            size="small"
            secondary
            :disabled="disabled || !canRepack"
            :loading="busy === 'repack'"
            @click="onRepack"
          >
            重打包
          </n-button>
        </span>
        <span :title="tipQa" class="btn-tip-wrap">
          <n-button size="small" quaternary :disabled="disabled || !!busy" :loading="busy === 'qa'" @click="onQa">
            质量摘要
          </n-button>
        </span>
        <span v-if="review.status === 'active'" :title="tipClose" class="btn-tip-wrap">
          <n-button
            size="small"
            quaternary
            :disabled="disabled || !!busy"
            :loading="busy === 'close' || busy === 'close-rebake'"
            @click="onClose"
          >
            结束复审
          </n-button>
        </span>
        <span :title="tipHandoff" class="btn-tip-wrap">
          <n-button size="small" quaternary :disabled="disabled" tag="a" :href="handoffUrl" target="_blank">
            交接包
          </n-button>
        </span>
      </div>
    </div>

    <div v-if="longOpVisible" class="panel panel-quiet mb-12">
      <div class="panel-bd">
        <LongOpWait
          :title="longOpTitle"
          :phases="longOpPhases"
          :phase-seconds="longOpPhaseSeconds"
          :started-at="longOpStartedAt"
          :hint="longOpHint"
        />
        <div v-if="recoverAlign" class="row mt-8" style="margin:0">
          <n-button size="small" secondary :loading="recoverBusy" @click="alignAfterRecover">
            立即对齐状态
          </n-button>
        </div>
      </div>
    </div>

    <div class="wb-pulse row" style="gap:8px;flex-wrap:wrap;margin:0">
      <span class="pill" :class="poisonZone.length ? 'pill-amber' : 'pill-green'">
        待收敛 {{ poisonZone.length }}
      </span>
      <span
        class="pill"
        :class="[
          blockingGates.length ? 'pill-amber' : 'pill-green',
          blockingGates.length ? 'pill-click' : '',
        ]"
        :role="blockingGates.length ? 'button' : undefined"
        :tabindex="blockingGates.length ? 0 : undefined"
        :title="blockingGates.length ? '查看挡包门禁全文' : undefined"
        @click="blockingGates.length && (showGateDetails = true)"
        @keydown.enter.prevent="blockingGates.length && (showGateDetails = true)"
      >
        挡包门禁 {{ blockingGates.length }}
      </span>
      <span class="pill" :class="openNotes.length ? 'pill-amber' : 'pill-neutral'">
        偏差 {{ openNotes.length }}
      </span>
      <span class="pill pill-neutral">已通过 {{ safeZone.length }}</span>
    </div>

    <!-- 失败场景：一条阻断卡合并同义告警；门禁全文进弹层，不把页面撑成墙 -->
    <div v-if="hasBlockSurface" class="block-panel" :class="'tone-' + blockTone">
      <div class="block-hd row-between" style="align-items:flex-start;gap:8px">
        <div>
          <div class="block-title">{{ blockTitle }}</div>
          <p class="small muted" style="margin:4px 0 0">{{ blockHint }}</p>
        </div>
        <n-button
          v-if="rebakeEscapeNeeded"
          size="small"
          secondary
          :disabled="disabled || !!busy"
          :loading="busy === 'close-rebake'"
          @click="onCloseAndRebake"
        >
          结束复审并去重新生成
        </n-button>
      </div>
      <ul class="block-points">
        <li v-if="rebakeEscapeNeeded">复审锁生成 · 须改工程先结束复审</li>
        <li v-if="zipStale">ZIP 与工程未同步</li>
        <li v-if="openNotes.length && !regressions.length">未结案偏差 {{ openNotes.length }} 条</li>
        <li v-if="regressions.length">已通过清单回退 {{ regressions.length }} 条</li>
        <li v-if="blockingGates.length && !regressions.length">
          挡包门禁 {{ blockingGates.length }} 项
          <template v-if="showScrubCopy"> · 可先清洗文案</template>
        </li>
      </ul>
      <div v-if="regressions.length" class="block-preview">
        <div
          v-for="(r, i) in regressions.slice(0, 3)"
          :key="'reg-' + i"
          class="block-preview-line"
        >{{ r.message }}</div>
        <button
          v-if="regressions.length > 3"
          type="button"
          class="block-toggle"
          @click="showGateDetails = true"
        >其余 {{ regressions.length - 3 }} 条见全文</button>
      </div>
      <div v-if="blockingGates.length" class="block-gates">
        <div class="block-preview">
          <div
            v-for="g in blockingGates.slice(0, 3)"
            :key="'prev-' + (g.key || g.label)"
            class="block-preview-line"
          >
            <strong>{{ g.label }}</strong>
          </div>
        </div>
        <button type="button" class="block-toggle" @click="showGateDetails = true">
          查看门禁全文（{{ blockingGates.length }}）· 含说明
        </button>
      </div>
    </div>

    <n-modal
      v-model:show="showGateDetails"
      preset="card"
      :title="gateModalTitle"
      class="gate-detail-modal"
      style="width:min(720px,94vw)"
      :bordered="false"
      :segmented="{ content: true }"
    >
      <div class="gate-modal-body">
        <div v-if="regressions.length" class="gate-modal-block">
          <div class="parse-sec-hd">清单回退</div>
          <ul class="reg-list gate-full-list">
            <li v-for="(r, i) in regressions" :key="'mreg-' + i">{{ r.message }}</li>
          </ul>
        </div>
        <div v-if="blockingGates.length" class="gate-modal-block">
          <div class="parse-sec-hd">挡包门禁 · {{ blockingGates.length }}</div>
          <ul class="reg-list gate-full-list">
            <li v-for="g in blockingGates" :key="'mg-' + (g.key || g.label)">
              <strong class="gate-full-label">{{ g.label }}</strong>
              <div v-if="g.desc" class="gate-full-desc">{{ g.desc }}</div>
            </li>
          </ul>
        </div>
      </div>
      <template #footer>
        <n-button size="small" @click="showGateDetails = false">关闭</n-button>
      </template>
    </n-modal>

    <n-collapse class="review-more" :default-expanded-names="reviewDefaultOpen">
      <n-collapse-item :title="`复审明细 · 待收敛 ${poisonZone.length} · 门禁 ${blockingGates.length}`" name="diag">
        <div class="diag-grid">
          <div class="review-panel diag-side-panel">
            <div class="diag-side-block">
              <div class="small" style="font-weight:600;margin-bottom:4px">待收敛 · 未通过清单（{{ poisonZone.length }}）</div>
              <n-empty v-if="!poisonZone.length" description="暂无待处理清单项" size="small" />
              <ul v-else class="zone-list">
                <li v-for="item in poisonZone" :key="'p-' + item.name">{{ item.name }}</li>
              </ul>
            </div>
            <div class="diag-side-block">
              <div class="small row-between" style="font-weight:600;margin-bottom:4px;align-items:center">
                <span>挡包门禁（{{ blockingGates.length }}）</span>
                <n-button
                  v-if="blockingGates.length"
                  text
                  size="tiny"
                  @click="showGateDetails = true"
                >查看全文</n-button>
              </div>
              <n-empty v-if="!blockingGates.length" description="无未过门禁" size="small" />
              <ul v-else class="zone-list">
                <li v-for="g in blockingGates" :key="'g-' + (g.key || g.label)">
                  {{ g.label }}
                </li>
              </ul>
            </div>
            <div class="diag-side-block">
              <div class="small" style="font-weight:600;margin-bottom:4px">已通过清单（{{ safeZone.length }}）</div>
              <n-empty v-if="!safeZone.length" description="尚无冻结项" size="small" />
              <ul v-else class="zone-list">
                <li v-for="item in safeZone" :key="'s-' + item.name">{{ item.name }}</li>
              </ul>
            </div>
            <div class="diag-side-block">
              <div class="small" style="font-weight:600;margin-bottom:4px">最近验收</div>
              <p v-if="lastVerifySummary" class="small" style="margin:0">{{ lastVerifySummary }}</p>
              <p v-else class="small muted" style="margin:0">尚未验收</p>
            </div>
            <div class="diag-side-block">
              <div class="small row-between" style="font-weight:600;margin-bottom:4px;align-items:center">
                <span>质量摘要（QA）</span>
                <n-button text size="tiny" :disabled="disabled || !!busy" :loading="busy === 'qa'" @click="onQa">
                  重跑
                </n-button>
              </div>
              <p v-if="lastQa?.summary" class="small" style="margin:0 0 6px">{{ lastQa.summary }}</p>
              <p v-else class="small muted" style="margin:0">尚无摘要 · 可点验收或「质量摘要」</p>
              <ul v-if="lastQaFindings.length" class="zone-list">
                <li v-for="(f, i) in lastQaFindings" :key="'qa-' + i">
                  <span class="pill" :class="qaLevelPill(f.level)">{{ f.level || 'info' }}</span>
                  {{ f.msg }}<span v-if="f.where" class="muted"> · {{ f.where }}</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </n-collapse-item>

      <n-collapse-item title="审计检查表 · 12 主项 + 理解偏差" name="boss">
        <div class="row-between" style="align-items:center;margin-bottom:6px">
          <p class="small muted" style="margin:0">
            勾选仅保存在本机。机器全绿仍可能理解错——对着开题核。
            <router-link to="/help#help-card-四痛点">帮助 · 四痛点</router-link>
          </p>
          <n-button text size="tiny" :disabled="disabled" @click="resetBossChecks">清空勾选</n-button>
        </div>
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
          已勾「理解偏差」且未通过清单/挡包门禁为空：对照开题核域、主路径、皮与种子，修工厂；登记偏差写「工厂理解偏差」，禁止甩锅「材料薄」。
        </n-alert>
      </n-collapse-item>

      <n-collapse-item :title="`偏差登记与轮次${openNotes.length ? ` · ${openNotes.length} 条待结案` : ''}`" name="notes">
        <div v-if="fixNotes.length" class="fix-notes-panel" style="margin:0 0 10px;border:none;padding:0">
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
                  secondary
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

        <div class="review-note-row" style="margin-top:0">
          <n-input
            v-model:value="noteText"
            type="textarea"
            :autosize="{ minRows: 2, maxRows: 4 }"
            placeholder="登记工厂与开题不一致之处（写「工厂理解偏差」；禁止甩锅材料薄。仅运营可见）"
            :disabled="disabled || !!busy"
          />
          <n-button size="small" secondary :disabled="disabled || !noteText.trim() || !!busy" @click="onAddNote">
            登记偏差
          </n-button>
        </div>

        <div v-if="rounds.length" class="mt-12">
          <div class="parse-sec-hd">轮次记录</div>
          <n-data-table size="small" :bordered="false" :columns="roundCols" :data="rounds" :max-height="180" />
        </div>
      </n-collapse-item>
    </n-collapse>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { NAlert, NButton, NCheckbox, NCollapse, NCollapseItem, NDataTable, NEmpty, NInput, NModal } from 'naive-ui'
import { api, message, confirm } from '../api'
import LongOpWait from './LongOpWait.vue'
import { clearLongOp, markLongOp, peekLongOp } from '../utils/longOpSession'

const props = defineProps({
  projectId: { type: String, required: true },
  deliveryReview: { type: Object, default: () => ({}) },
  disabled: { type: Boolean, default: false },
  /** 可选：返回 Promise 的刷新函数；有则 await，避免 busy 过早清空导致连点 */
  reload: { type: Function, default: null },
  /** 合卷成功后先乐观写入投影（消黄条），再等 reload 权威对齐 */
  applyReview: { type: Function, default: null },
  /** 与质量检查同源：父级 scrubStudentCopy / copyGateNeedsScrub */
  showScrubCopy: { type: Boolean, default: false },
  scrubBusy: { type: Boolean, default: false },
  scrubCopy: { type: Function, default: null },
  /** 结束复审后跳到一键生成（可选） */
  goGenerate: { type: Function, default: null },
})

const emit = defineEmits(['refresh', 'go-generate'])

const busy = ref('')
const noteText = ref('')
const localRegressions = ref([])
const showDoneNotes = ref(false)
/** 门禁全文默认收起；点 pill /「展开」再看，避免失败页无限变长 */
const showGateDetails = ref(false)

/** I2：验收/摘要/重打包/清洗 中间态 + 刷新可恢复 */
const recoverAlign = ref(false)
const recoverBusy = ref(false)
const recoverKind = ref('')
const longOpStartedAt = ref(0)

const LONG_OP_META = {
  verify: {
    title: '正在验收…',
    phases: [
      { key: 'qa', label: '质量摘要' },
      { key: 'gates', label: '门禁与单调性' },
      { key: 'ready', label: '对齐交付就绪' },
    ],
    phaseSeconds: [35, 50, 40],
  },
  qa: {
    title: '正在拉质量摘要…',
    phases: [
      { key: 'qa', label: '质量摘要' },
      { key: 'gates', label: '刷新门禁投影' },
    ],
    phaseSeconds: [45, 30],
  },
  repack: {
    title: '正在重打包…',
    phases: [
      { key: 'check', label: '校验验收条件' },
      { key: 'zip', label: '打包交付 ZIP' },
      { key: 'sync', label: '同步就绪状态' },
    ],
    phaseSeconds: [15, 40, 20],
  },
  scrub: {
    title: '正在清洗文案…',
    phases: [
      { key: 'scan', label: '扫描学生可见文案' },
      { key: 'write', label: '写回工程' },
    ],
    phaseSeconds: [25, 35],
  },
}

const activeLongKind = computed(() => {
  if (busy.value === 'verify') return 'verify'
  if (busy.value === 'qa') return 'qa'
  if (busy.value === 'repack') return 'repack'
  if (props.scrubBusy) return 'scrub'
  if (recoverAlign.value && recoverKind.value) return recoverKind.value
  return ''
})

const longOpVisible = computed(() => !!activeLongKind.value)
const longOpMeta = computed(() => LONG_OP_META[activeLongKind.value] || null)
const longOpTitle = computed(() => {
  if (recoverAlign.value && !busy.value && !props.scrubBusy) {
    const label = LONG_OP_META[recoverKind.value]?.title?.replace(/…$/, '') || '上次长操作'
    return `${label}可能仍在跑或已完成 · 正在对齐`
  }
  return longOpMeta.value?.title || '仍在运行…'
})
const longOpPhases = computed(() => longOpMeta.value?.phases || [])
const longOpPhaseSeconds = computed(() => longOpMeta.value?.phaseSeconds || [])
const longOpHint = computed(() => {
  if (recoverAlign.value && !busy.value && !props.scrubBusy) {
    return '刷新后仍保留等待语义：点「立即对齐」或稍候自动对齐；勿重复连点验收。'
  }
  return ''
})

watch(
  () => [busy.value, props.scrubBusy, props.projectId],
  ([b, scrub, id]) => {
    const kind =
      b === 'verify' || b === 'qa' || b === 'repack' ? b : scrub ? 'scrub' : ''
    if (kind && id) {
      markLongOp(id, kind)
      if (!longOpStartedAt.value) longOpStartedAt.value = Date.now()
      recoverAlign.value = false
    } else if (!kind && !recoverAlign.value) {
      longOpStartedAt.value = 0
    }
  },
)

watch(
  () => props.scrubBusy,
  (v, prev) => {
    if (prev && !v) clearLongOp(props.projectId)
  },
)

async function alignAfterRecover({ silent = false } = {}) {
  if (recoverBusy.value) return
  recoverBusy.value = true
  try {
    await refreshAfter()
    clearLongOp(props.projectId)
    recoverAlign.value = false
    recoverKind.value = ''
    if (!silent) message.info('状态已对齐')
  } catch {
    if (!silent) message.warning('对齐未完成 · 请稍后再试或硬刷新')
  } finally {
    recoverBusy.value = false
  }
}

onMounted(() => {
  const peeked = peekLongOp(props.projectId)
  if (!peeked?.kind || !LONG_OP_META[peeked.kind]) return
  recoverKind.value = peeked.kind
  recoverAlign.value = true
  longOpStartedAt.value = peeked.at || Date.now()
  void alignAfterRecover({ silent: true })
})

/** 有待收敛清单时展开复审明细；门禁全文已在上方阻断卡，不重复撑开 */
const reviewDefaultOpen = computed(() => {
  const dr = props.deliveryReview || {}
  const zones = dr.zones || {}
  const poison = Array.isArray(zones.poison_zone) ? zones.poison_zone : []
  const notes = Array.isArray(dr.review?.fix_notes)
    ? dr.review.fix_notes.filter((n) => n && n.status !== 'done')
    : []
  if (poison.length) return ['diag']
  if (notes.length) return ['notes']
  return []
})

const BOSS_ITEMS = [
  { key: 'shell', label: '1. 有没有空壳（缺表/API/状态机/写库）？已齐是否「管理能管+用户可产生数据」？' },
  { key: 'regress', label: '2. 旧题回归红了吗？每业务组代表（含图书/宿舍/实习）+ 本轮邻域/触点' },
  { key: 'fsm', label: '3. 状态机对且准吗（集合/转移/角色/文案）？' },
  { key: 'fields', label: '4. 字段可见含义像本题吗（有无壳字段穿帮）？' },
  { key: 'flow', label: '5. 会不会看错主流程（「我的」/种子/按钮诱导，或交易/内容串味）？' },
  { key: 'steal', label: '6. 新域有没有抢走旧题匹配？' },
  { key: 'demo', label: '7. 学生可见面有没有「演示」、工厂腔，或硬件否定句进页面？' },
  { key: 'rewrite', label: '8. 开题有没有被改来迁就工厂？' },
  { key: 'reject', label: '9. 该 reject 的硬边界还拒不拒？' },
  { key: 'thesis', label: '10. 论文/材料图跟实包一致吗（本轮动到的八张都要对）？' },
  { key: 'skin', label: '11. 视觉轴进包生效了吗（theme/chrome/layout/typeface/门户构图）？' },
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
  // 写操作已成功时，投影刷新失败不得冒泡成「操作失败」或拖死 busy
  try {
    if (typeof props.reload === 'function') {
      await props.reload()
      return
    }
    emit('refresh')
  } catch {
    /* ignore */
  }
}

/** 验圈/合卷/QA 响应里已有结论时立刻 patch，再轻量刷新 */
function applyFromWrite(patch) {
  if (!patch || typeof patch !== 'object') return
  if (typeof props.applyReview === 'function') {
    props.applyReview({
      ...(props.deliveryReview || {}),
      ...patch,
    })
  }
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
  const roundsList = review.value.rounds || []
  const lastRound = roundsList.length ? roundsList[roundsList.length - 1] : null
  const last = review.value.last_verify
  // last_verify 旧数据可能缺 round_pass；以最近一轮记录为准
  const src =
    last && typeof last === 'object'
      ? {
          ...lastRound,
          ...last,
          round_pass:
            typeof last.round_pass === 'boolean'
              ? last.round_pass
              : lastRound?.round_pass,
          gates_ok:
            typeof last.gates_ok === 'boolean' ? last.gates_ok : lastRound?.gates_ok,
          pending_count:
            typeof last.pending_count === 'number'
              ? last.pending_count
              : lastRound?.pending_count,
          open_notes_count:
            typeof last.open_notes_count === 'number'
              ? last.open_notes_count
              : lastRound?.open_notes_count,
          round: lastRound?.round ?? last.round,
          at: last.at || lastRound?.at,
        }
      : lastRound
  if (!src) return ''
  const parts = [
    src.round != null ? `第 ${src.round} 轮` : null,
    src.round_pass ? '通过' : '未过',
    src.monotonic_ok === false ? '单调性回退' : null,
    Array.isArray(src.regressions) && src.regressions.length
      ? `回退 ${src.regressions.length} 条`
      : null,
    src.gates_ok === false
      ? '门禁未过'
      : src.gates_ok
        ? '门禁过'
        : null,
    typeof src.pending_count === 'number' ? `待收敛 ${src.pending_count}` : null,
    typeof src.open_notes_count === 'number' && src.open_notes_count > 0
      ? `未结案 ${src.open_notes_count}`
      : null,
    Array.isArray(src.fail_reasons) && src.fail_reasons.length && !src.round_pass
      ? src.fail_reasons[0]
      : null,
    src.at ? formatAt(src.at) : null,
  ].filter(Boolean)
  return parts.join(' · ') || '已有验收记录'
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

/** 复审锁生成 + 门禁/回退挡合卷 → 须重出包时的死锁出口 */
const rebakeEscapeNeeded = computed(() => {
  if (review.value.status !== 'active') return false
  return blockingGates.value.length > 0 || regressions.value.length > 0
})

const hasBlockSurface = computed(
  () =>
    rebakeEscapeNeeded.value ||
    zipStale.value ||
    (openNotes.value.length > 0 && !regressions.value.length) ||
    regressions.value.length > 0 ||
    (blockingGates.value.length > 0 && !regressions.value.length),
)

const blockTone = computed(() => {
  if (regressions.value.length) return 'error'
  if (blockingGates.value.length || zipStale.value || openNotes.value.length) return 'warn'
  return 'info'
})

const blockTitle = computed(() => {
  if (regressions.value.length) return '已通过清单回退 · 暂不可重打包'
  if (blockingGates.value.length) return '质量门禁未过 · 暂不可下载'
  if (openNotes.value.length) return '仍有未结案偏差'
  if (zipStale.value) return '交付包未同步'
  if (rebakeEscapeNeeded.value) return '须重跑生成时：先结束复审'
  return '当前阻断'
})

const blockHint = computed(() => {
  if (regressions.value.length) {
    return '回退后勿只反复重打包；结束复审 → 改工厂 → 重新生成。'
  }
  if (blockingGates.value.length) {
    return '当场能修就先做再验收；须改生成/基线则结束复审后重跑。标题保留，说明点「查看门禁全文」。'
  }
  if (zipStale.value && !blockingGates.value.length) {
    return '验收通过后执行重打包，使 ZIP 与工程一致。'
  }
  if (rebakeEscapeNeeded.value) {
    return '仅同步 ZIP 请验收后重打包；须改工程请用右侧按钮。'
  }
  return ''
})

const gateModalTitle = computed(() => {
  if (regressions.value.length && blockingGates.value.length) {
    return `阻断全文 · 回退 ${regressions.value.length} · 门禁 ${blockingGates.value.length}`
  }
  if (regressions.value.length) return `清单回退 · ${regressions.value.length}`
  return `挡包门禁 · ${blockingGates.value.length}`
})

watch(
  () => props.projectId,
  () => {
    showGateDetails.value = false
  },
)

const tipStart = '开始对照开题收窄偏差；可验收、登记偏差'
const tipVerify = '本轮验收：重跑门禁与质量摘要；通过项进已通过清单，未过留未通过清单，门禁未过会单独提示'
const tipQa = '再跑一遍交付质检摘要（不替代门禁）'
const tipClose = computed(() =>
  rebakeEscapeNeeded.value
    ? '结束复审后可重新生成；门禁未过时重打包不可用'
    : '结束本轮复审流程（不删已有登记）',
)
const tipHandoff = '导出运营交接材料，不进学生 ZIP'

const repackTip = computed(() => {
  if (canRepack.value) return '验收通过后更新交付 ZIP，使与工程一致'
  if (props.disabled) return '工程重新生成中或尚无工作区，暂不可重打包'
  if (busy.value) return '请等待当前操作完成'
  if (regressions.value.length) {
    return '存在已通过清单回退，无法重打包；须重出包时请先结束复审再重新生成'
  }
  if (openNotes.value.length) return `仍有 ${openNotes.value.length} 条未结案偏差，请先结案后再重打包`
  if (blockingGates.value.length) {
    const labels = blockingGates.value
      .map((g) => (g && g.label) || '')
      .filter(Boolean)
      .slice(0, 3)
      .join('、')
    return `质量门禁未过（${labels || '见上方提示'}）· 当场可修则处理后验收；须重跑生成请先结束复审`
  }
  const rounds = review.value.rounds || []
  const lastRound = rounds.length ? rounds[rounds.length - 1] : null
  if (!lastRound?.round_pass) return '请先完成验收通过后再重打包'
  if (lastRound.monotonic_ok === false) return '验收单调性未通过，暂不可重打包'
  return '暂不可重打包'
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
  {
    title: '本轮',
    key: 'round_pass',
    width: 72,
    render: (r) => (r.round_pass ? '通过' : '未过'),
  },
  { title: '待收敛', key: 'pending_count', width: 72 },
  {
    title: '时间',
    key: 'at',
    width: 168,
    ellipsis: { tooltip: true },
    render: (r) => formatAt(r.at),
  },
]

function isTimeoutErr(e) {
  const code = e?.code || ''
  return code === 'ECONNABORTED' || /timeout/i.test(String(e?.message || ''))
}

function timeoutAlignMsg(op) {
  return `${op}请求超时 · 服务端可能已成功，请刷新对齐状态`
}

async function onStart() {
  if (busy.value || props.disabled) return
  busy.value = 'start'
  let wroteOk = false
  try {
    const res = await api.startDeliveryReview(props.projectId)
    const st = res?.data?.review
    if (st && typeof st === 'object') {
      applyFromWrite({
        review: st,
        zip_stale: true,
        zip_ready: false,
        delivery_mark: 'none',
      })
    }
    message.success('已进入交付复审')
    wroteOk = true
  } catch (e) {
    message.error(
      isTimeoutErr(e) ? timeoutAlignMsg('进入复审') : e?.response?.data?.detail || e?.message || '进入复审失败',
    )
  } finally {
    busy.value = ''
  }
  // A2：权威投影放 busy 之后，勿拖住按钮
  if (wroteOk) void refreshAfter()
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
  let wroteOk = false
  let keepSession = false
  try {
    const raw = await api.verifyDeliveryReview(props.projectId)
    // 兼容直接模型 / { data } 包裹
    const res = raw && typeof raw === 'object' && raw.data && raw.monotonic_ok == null ? raw.data : raw
    const payload = res && typeof res === 'object' ? res : {}
    localRegressions.value = Array.isArray(payload.regressions) ? payload.regressions : []
    const blocked = Array.isArray(payload.blocking_gates) ? payload.blocking_gates : []
    const failReasons = Array.isArray(payload.fail_reasons) ? payload.fail_reasons.filter(Boolean) : []
    if (payload.monotonic_ok && payload.round_pass) {
      message.success('验收通过 · 可执行重打包')
    } else if (!payload.monotonic_ok) {
      message.warning('验收未通过 · 存在已通过清单回退')
    } else if (failReasons.length) {
      message.warning(`验收未通过 · ${failReasons.join('；')}`)
    } else if (blocked.length) {
      const labels = blocked
        .map((g) => (g && g.label) || '')
        .filter(Boolean)
        .slice(0, 3)
        .join('、')
      message.warning(`验收未通过 · 质量门禁未过${labels ? `（${labels}）` : ''}`)
    } else {
      const pending = Array.isArray(payload.pending_names) ? payload.pending_names.filter(Boolean) : []
      if (pending.length) {
        message.warning(`验收未通过 · 待收敛清单：${pending.slice(0, 4).join('、')}`)
      } else {
        message.warning('验收未通过 · 请查看未通过清单与门禁区')
      }
    }
    // 响应已含 gates/checklist/zip_*：先 patch 顶层；权威拉在 busy 之后
    applyFromWrite({
      review: payload.review,
      zones: payload.zones,
      blocking_gates: payload.blocking_gates,
      zip_stale: payload.zip_stale,
      gates: payload.gates,
      checklist: payload.checklist,
      zip_ready: payload.zip_ready,
      download_blocked_reason: payload.download_blocked_reason,
    })
    wroteOk = true
  } catch (e) {
    if (isTimeoutErr(e)) {
      keepSession = true
      recoverKind.value = 'verify'
      recoverAlign.value = true
      message.error('验收超时 · 服务端可能已成功或仍在跑，请刷新对齐状态')
    } else {
      message.error(e?.response?.data?.detail || e?.message || '验收失败')
    }
  } finally {
    busy.value = ''
    if (!keepSession) clearLongOp(props.projectId)
  }
  if (wroteOk) void refreshAfter()
}

async function onRepack() {
  if (busy.value || props.disabled || !canRepack.value) return
  busy.value = 'repack'
  let wroteOk = false
  let keepSession = false
  try {
    const raw = await api.repackDeliveryReview(props.projectId)
    const meta = raw?.data && typeof raw.data === 'object' ? raw.data : {}
    // 接口已成功：立刻消「未同步」并放开下载条件，勿等整页 load / getDeliveryReview
    applyFromWrite({
      zip_stale: false,
      workspace_hash:
        meta.workspace_hash || props.deliveryReview?.workspace_hash || '',
      zip_ready: true,
      download_blocked_reason: null,
      status: 'generated',
    })
    message.success('重打包完成 · 交付包已更新')
    wroteOk = true
  } catch (e) {
    if (isTimeoutErr(e)) {
      keepSession = true
      recoverKind.value = 'repack'
      recoverAlign.value = true
      message.error(timeoutAlignMsg('重打包'))
    } else {
      message.error(e?.response?.data?.detail || e?.message || '重打包失败')
    }
  } finally {
    busy.value = ''
    if (!keepSession) clearLongOp(props.projectId)
  }
  if (wroteOk) void refreshAfter()
}

async function onQa() {
  if (busy.value || props.disabled) return
  busy.value = 'qa'
  let wroteOk = false
  let keepSession = false
  try {
    const res = await api.runDeliveryQa(props.projectId)
    if (res.qa?.ok) message.success('质量摘要已通过')
    else message.warning('质量摘要存在 error 级问题')
    applyFromWrite({
      gates: res.gates,
      download_blocked_reason: res.download_blocked_reason,
      review: {
        ...(props.deliveryReview?.review || {}),
        last_qa: res.qa,
      },
    })
    wroteOk = true
  } catch (e) {
    if (isTimeoutErr(e)) {
      keepSession = true
      recoverKind.value = 'qa'
      recoverAlign.value = true
      message.error(timeoutAlignMsg('质量摘要'))
    } else {
      message.error(e?.response?.data?.detail || e?.message || '质量摘要失败')
    }
  } finally {
    busy.value = ''
    if (!keepSession) clearLongOp(props.projectId)
  }
  if (wroteOk) void refreshAfter()
}

async function onClose() {
  if (busy.value || props.disabled) return
  busy.value = 'close'
  let wroteOk = false
  try {
    const res = await api.closeDeliveryReview(props.projectId)
    const st = res?.data?.review
    if (st && typeof st === 'object') {
      applyFromWrite({ review: st })
    }
    message.success('已结束交付复审')
    wroteOk = true
  } catch (e) {
    message.error(
      isTimeoutErr(e) ? timeoutAlignMsg('结束复审') : e?.response?.data?.detail || e?.message || '结束复审失败',
    )
  } finally {
    busy.value = ''
  }
  if (wroteOk) void refreshAfter()
}

async function onCloseAndRebake() {
  if (busy.value || props.disabled) return
  const ok = await confirm(
    '结束复审后可到「一键生成」重新生成。已登记偏差会保留；重新生成会清空复审轮次与履约标记。',
    {
      title: '结束复审并重新生成',
      type: 'warning',
      positiveText: '结束并前往',
      negativeText: '取消',
    },
  )
  if (!ok) return
  busy.value = 'close-rebake'
  let wroteOk = false
  try {
    const res = await api.closeDeliveryReview(props.projectId)
    const st = res?.data?.review
    if (st && typeof st === 'object') {
      applyFromWrite({ review: st })
    }
    message.success('已结束复审 · 请确认选项后重新生成')
    wroteOk = true
  } catch (e) {
    message.error(
      isTimeoutErr(e) ? timeoutAlignMsg('结束复审') : e?.response?.data?.detail || e?.message || '结束复审失败',
    )
  } finally {
    busy.value = ''
  }
  if (wroteOk) {
    void refreshAfter()
    if (typeof props.goGenerate === 'function') {
      props.goGenerate()
    } else {
      emit('go-generate')
    }
  }
}

async function onAddNote() {
  const text = noteText.value.trim()
  if (!text || busy.value || props.disabled) return
  busy.value = 'note'
  let wroteOk = false
  try {
    const res = await api.addDeliveryFixNote(props.projectId, text)
    const note = res?.data?.note
    noteText.value = ''
    showDoneNotes.value = false
    // 响应已含新 note：先入投影，勿等 getDeliveryReview（指纹可达 120s）才消 loading
    if (note && typeof note === 'object') {
      const prev = props.deliveryReview?.review || {}
      const notes = [...(Array.isArray(prev.fix_notes) ? prev.fix_notes : []), note].slice(-40)
      applyFromWrite({
        review: {
          ...prev,
          status: prev.status === 'idle' || !prev.status ? 'active' : prev.status,
          fix_notes: notes,
        },
        delivery_mark: 'none',
      })
    }
    message.success('已登记偏差')
    wroteOk = true
  } catch (e) {
    message.error(
      isTimeoutErr(e) ? timeoutAlignMsg('登记偏差') : e?.response?.data?.detail || e?.message || '登记失败',
    )
  } finally {
    busy.value = ''
  }
  if (wroteOk) void refreshAfter()
}

async function onResolveNote(noteId, done) {
  if (!noteId || busy.value || props.disabled) return
  busy.value = `note-${noteId}`
  let wroteOk = false
  try {
    await api.resolveDeliveryFixNote(props.projectId, noteId, done)
    // 接口无投影体：本地改 note 状态，再轻量对齐
    const prev = props.deliveryReview?.review || {}
    const notes = (Array.isArray(prev.fix_notes) ? prev.fix_notes : []).map((n) => {
      if (!n || n.id !== noteId) return n
      return {
        ...n,
        status: done ? 'done' : 'open',
        resolved_at: done ? (n.resolved_at || new Date().toISOString()) : null,
      }
    })
    applyFromWrite({ review: { ...prev, fix_notes: notes } })
    message.success(done ? '已结案' : '已重开')
    wroteOk = true
  } catch (e) {
    message.error(
      isTimeoutErr(e) ? timeoutAlignMsg('结案') : e?.response?.data?.detail || e?.message || '操作失败',
    )
  } finally {
    busy.value = ''
  }
  if (wroteOk) void refreshAfter()
}
</script>

<style scoped>
.delivery-review .diag-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 8px;
}
.review-panel {
  border: 1px solid var(--border, #e8e8e8);
  border-radius: 8px;
  padding: 10px 12px;
}
.boss-check-list {
  max-height: 240px;
  overflow: auto;
  padding-right: 4px;
}
.wb-pulse {
  padding: 0;
  align-items: center;
}
.wb-pulse .pill {
  /* 四枚同规格；可点的也不另起 button 高度 */
  box-sizing: border-box;
}
.pill-click {
  cursor: pointer;
}
.pill-click:hover {
  filter: brightness(1.08);
}
.pill-click:focus-visible {
  outline: 2px solid var(--teal-deep, #3aa8a0);
  outline-offset: 2px;
}
.review-more {
  margin-top: 2px;
}
.block-panel {
  border-radius: 8px;
  padding: 10px 12px;
  border: 1px solid var(--border, #e8e8e8);
}
.block-panel.tone-info {
  background: rgba(32, 128, 180, 0.08);
  border-color: rgba(32, 128, 180, 0.35);
}
.block-panel.tone-warn {
  background: rgba(180, 120, 32, 0.1);
  border-color: rgba(180, 120, 32, 0.4);
}
.block-panel.tone-error {
  background: rgba(180, 48, 48, 0.1);
  border-color: rgba(180, 48, 48, 0.4);
}
.block-title {
  font-size: 13px;
  font-weight: 600;
  letter-spacing: -0.01em;
}
.block-points {
  margin: 8px 0 0;
  padding-left: 1.1em;
  font-size: 12px;
  line-height: 1.45;
}
.block-gates {
  margin-top: 8px;
}
.block-preview {
  margin-top: 6px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.block-preview-line {
  font-size: 12px;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.block-toggle {
  border: none;
  background: transparent;
  color: var(--teal-deep, #3aa8a0);
  font: inherit;
  font-size: 12px;
  padding: 0;
  margin-top: 6px;
  cursor: pointer;
  text-align: left;
}
/* 弹层可能 teleport 到 body：正文用非 scoped 规则，避免说明被截断 */
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

<style>
/* n-modal teleport 出 scoped；弹层内门禁说明必须整段换行，禁止截断 */
.gate-detail-modal .gate-modal-body {
  max-height: min(62vh, 560px);
  overflow: auto;
  padding-right: 4px;
}
.gate-detail-modal .gate-modal-block + .gate-modal-block {
  margin-top: 14px;
}
.gate-detail-modal .gate-full-list {
  margin: 8px 0 0;
  padding-left: 1.1em;
  list-style: disc;
}
.gate-detail-modal .gate-full-list > li {
  margin-bottom: 12px;
  white-space: normal !important;
  overflow: visible !important;
  text-overflow: unset !important;
  overflow-wrap: anywhere;
  word-break: break-word;
}
.gate-detail-modal .gate-full-label {
  display: block;
  font-size: 13px;
  line-height: 1.45;
  white-space: normal !important;
  overflow-wrap: anywhere;
  word-break: break-word;
}
.gate-detail-modal .gate-full-desc {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--muted, #888);
  white-space: pre-wrap !important;
  overflow: visible !important;
  text-overflow: unset !important;
  overflow-wrap: anywhere;
  word-break: break-word;
}
</style>
