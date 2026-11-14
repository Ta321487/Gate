<template>
  <div class="page-fill surface-ops">
    <h1 class="page-title">开工台</h1>
    <p class="page-desc">
      今日待办与队列入口；建项请至「项目」，按类型排修请至「失败分析」。
    </p>
    <PageSkeleton v-if="!booted" variant="dashboard" :rows="4" />
    <template v-else>
      <!-- 轻量数字条：不与主区同权抢视线 -->
      <div class="surface-strip" role="navigation" aria-label="今日指标">
        <button type="button" class="surface-chip" @click="go('/projects?focus=needs_confirm')">
          待匹配 <b>{{ needsConfirm.length }}</b>
        </button>
        <button type="button" class="surface-chip" @click="go('/jobs')">
          生成中 <b>{{ generatingCount }}</b>
        </button>
        <button type="button" class="surface-chip" @click="go('/fail-analysis')">
          近7日失败 <b>{{ failTotals.failed ?? 0 }}</b>
          <span class="chip-hint">{{ failTotals.codes ?? 0 }} 种</span>
        </button>
        <button type="button" class="surface-chip" @click="go('/projects?focus=review')">
          复审中 <b>{{ reviewActive.length }}</b>
        </button>
        <button type="button" class="surface-chip" @click="go('/projects?focus=fail')">
          门禁失败 <b>{{ gateFail.length }}</b>
        </button>
        <button type="button" class="surface-chip" @click="go('/projects?focus=undelivered')">
          可下未发 <b>{{ readyUndelivered.length }}</b>
        </button>
      </div>

      <!-- 唯一主区：轻托盘承载，非卡片墙 -->
      <section class="surface-main surface-tray" aria-labelledby="ops-today-hd">
        <div class="surface-main-hd">
          <h2 id="ops-today-hd">今日要处理</h2>
          <n-button text size="small" @click="go('/projects')">全部项目 →</n-button>
        </div>
        <div class="surface-main-split">
          <div>
            <div class="ops-col-label muted">待办项目</div>
            <div v-if="!todoProjects.length" class="empty-hint ops-empty">
              <div class="empty-title">暂无待办项目</div>
              <div class="empty-desc">第一次出单：去「项目」上传材料，或点「生成测试开题」再拖回上传。</div>
              <div class="row" style="margin-top:10px;gap:8px;justify-content:center;flex-wrap:wrap">
                <n-button size="small" type="primary" @click="go('/projects')">去项目建项</n-button>
                <n-button size="small" secondary @click="go('/help#help-card-第一次怎么出单')">第一次怎么出单</n-button>
              </div>
            </div>
            <div
              v-for="p in todoProjects.slice(0, 8)"
              :key="p.id"
              class="ops-row"
              @click="go(`/projects/${p.id}`)"
            >
              <div class="ops-row-main">
                <span class="ops-tag" :class="todoTagClass(p)">{{ todoTag(p) }}</span>
                <span class="ops-title">{{ p.title || p.id }}</span>
              </div>
              <div class="ops-row-sub muted">点进详情继续</div>
            </div>
          </div>
          <div>
            <div class="ops-col-hd">
              <span class="ops-col-label muted">最近失败任务</span>
              <n-button text size="tiny" @click="go('/jobs')">任务队列 →</n-button>
            </div>
            <div v-if="!recentFails.length" class="empty-hint ops-empty">
              <div class="empty-title">暂无失败任务</div>
              <div class="empty-desc">失败任务会出现在任务队列，并可按类型在失败分析中查看</div>
            </div>
            <div
              v-for="j in recentFails.slice(0, 8)"
              :key="j.id"
              class="ops-row"
            >
              <div class="ops-row-main">
                <a class="link ops-title" href="#" @click.prevent="go(`/projects/${j.project_id}`)">
                  {{ j.project_title || j.project_id }}
                </a>
              </div>
              <div class="ops-row-sub">
                <template v-if="j.error_code">
                  <a
                    class="link"
                    href="#"
                    @click.prevent="go(`/fail-analysis?code=${encodeURIComponent(j.error_code)}`)"
                  >查看失败类型</a>
                  <span class="muted"> · </span>
                </template>
                <span class="muted truncate" :title="j.error || ''">{{ shortErr(j.error) }}</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- 次要：优先排修（弱框） -->
      <section class="surface-aside" aria-labelledby="ops-prio-hd">
        <div class="surface-aside-hd">
          <h3 id="ops-prio-hd">优先排修类型</h3>
          <n-button text size="small" @click="go('/fail-analysis')">失败分析 →</n-button>
        </div>
        <div v-if="!priorities.length" class="empty-hint ops-empty">
          <div class="empty-title">近七日暂无集中失败</div>
          <div class="empty-desc">出现失败后，将按类型列出建议优先处理项</div>
        </div>
        <div
          v-for="p in priorities.slice(0, 6)"
          :key="p.code"
          class="ops-row"
          :title="p.fix_locus ? `相关位置：${p.fix_locus}` : ''"
          @click="go(`/fail-analysis?code=${encodeURIComponent(p.code)}`)"
        >
          <div class="ops-row-main">
            <strong>{{ p.count }}</strong>
            <span>{{ p.label }}</span>
          </div>
          <div class="ops-row-sub muted">点开失败分析查看相关位置</div>
        </div>
      </section>

      <!-- 环境沉底一行 -->
      <footer class="surface-env-line">
        <span>
          API
          <span :class="healthOk ? 'ok' : 'bad'">{{ healthOk ? '正常' : '异常' }}</span>
          <span v-if="!healthOk" class="muted"> · 后端未通时请先跑 scripts\launcher.bat，菜单 N 可查缺什么</span>
        </span>
        <span class="sep">·</span>
        <span>布局 <span :class="layoutGateOk === true ? 'ok' : layoutGateOk === false ? 'bad' : ''">{{ layoutGateLabel }}</span></span>
        <span class="sep">·</span>
        <span>控件 <span :class="controlsGateOk === true ? 'ok' : controlsGateOk === false ? 'bad' : ''">{{ controlsGateLabel }}</span></span>
        <span class="sep">·</span>
        <span>Token {{ formatK(stats.monthly_tokens) }}/{{ formatK(stats.monthly_budget) }}</span>
        <span class="sep">·</span>
        <span :class="previewQuotaFull ? 'bad' : ''">预览 {{ previewRunning }}/{{ previewMax }}</span>
        <span class="sep">·</span>
        <span>履约 待审{{ stats.pending_review || 0 }} · 待发{{ stats.delivery_ready || 0 }} · 已发{{ stats.delivery_delivered || 0 }}</span>
        <span class="sep">·</span>
        <n-button text size="tiny" @click="go('/system')">运行环境</n-button>
        <n-button text size="tiny" @click="go('/llm')">大模型</n-button>
        <n-button text size="tiny" :loading="loading" @click="load">刷新</n-button>
      </footer>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NButton } from 'naive-ui'
import { api, message } from '../api'
import PageSkeleton from '../components/PageSkeleton.vue'

const router = useRouter()
const booted = ref(false)
const loading = ref(false)
const stats = ref({})
const projects = ref([])
const jobs = ref([])
const fail = ref(null)
const system = ref(null)
const healthOk = ref(false)
const layoutGateOk = ref(null)
const layoutGateSummary = ref('')
const controlsGateOk = ref(null)
const controlsGateSummary = ref('')

const failTotals = computed(() => fail.value?.totals || {})
const priorities = computed(() => fail.value?.priorities || [])
const needsConfirm = computed(() =>
  projects.value.filter((p) => p.status === 'needs_confirm' || p.match_confirmed === false),
)
const reviewActive = computed(() =>
  projects.value.filter((p) => p.review_status === 'active'),
)
/** 门禁失败：已出包但不可下载（与 projectIsDownloadable 同口径） */
const gateFail = computed(() =>
  projects.value.filter((p) => {
    const st = String(p.status || '')
    if (!['generated', 'running', 'failed'].includes(st)) return false
    if (p.review_status === 'active') return false
    if ('download_blocked_reason' in p) return !!p.download_blocked_reason
    return !p.zip_ready
  }),
)
/** 可下载未发出：机器可下且履约未 delivered */
const readyUndelivered = computed(() =>
  projects.value.filter((p) => {
    const st = String(p.status || '')
    if (!['generated', 'running'].includes(st)) return false
    const mark = String(p.delivery_mark || 'none')
    if (mark === 'delivered') return false
    if ('download_blocked_reason' in p) return !p.download_blocked_reason
    return !!p.zip_ready
  }),
)
const generatingCount = computed(() => {
  const fromStats = stats.value?.generating
  if (typeof fromStats === 'number') return fromStats
  return jobs.value.filter((j) => j.status === 'running' || j.status === 'queued').length
})
const recentFails = computed(() =>
  jobs.value
    .filter((j) => j.status === 'failed')
    .slice()
    .sort((a, b) => (b.id || 0) - (a.id || 0)),
)
const todoProjects = computed(() => {
  const seen = new Set()
  const out = []
  for (const p of [
    ...needsConfirm.value,
    ...reviewActive.value,
    ...gateFail.value,
    ...readyUndelivered.value,
    ...projects.value.filter((x) => x.status === 'failed'),
  ]) {
    if (seen.has(p.id)) continue
    seen.add(p.id)
    out.push(p)
  }
  return out
})

const previewMax = computed(() => Number(system.value?.preview_max_running) || 3)
const previewRunning = computed(() => Number(system.value?.preview_running) || 0)
const previewQuotaFull = computed(() => previewRunning.value >= previewMax.value)

const layoutGateLabel = computed(() => {
  if (layoutGateOk.value === true) return '通过'
  if (layoutGateOk.value === false) {
    const s = String(layoutGateSummary.value || '').trim()
    return s ? (s.length > 36 ? `${s.slice(0, 36)}…` : s) : '未通过'
  }
  return '未加载'
})

const controlsGateLabel = computed(() => {
  if (controlsGateOk.value === true) return '通过'
  if (controlsGateOk.value === false) {
    const s = String(controlsGateSummary.value || '').trim()
    return s ? (s.length > 36 ? `${s.slice(0, 36)}…` : s) : '未通过'
  }
  return '未加载'
})

function formatK(n) {
  const x = Number(n) || 0
  if (x >= 1000) return `${(x / 1000).toFixed(x >= 10000 ? 0 : 1)}k`
  return String(x)
}

function shortErr(msg) {
  const t = String(msg || '').trim()
  if (!t) return '生成未完成'
  return t.length > 48 ? `${t.slice(0, 48)}…` : t
}

function go(to) {
  router.push(to)
}

function todoTag(p) {
  if (p.status === 'needs_confirm' || p.match_confirmed === false) return '待匹配'
  if (p.review_status === 'active') return '复审中'
  if (p.status === 'failed') return '生成失败'
  const st = String(p.status || '')
  if (['generated', 'running'].includes(st)) {
    const blocked = 'download_blocked_reason' in p ? !!p.download_blocked_reason : !p.zip_ready
    if (blocked) return '门禁失败'
    if (String(p.delivery_mark || 'none') !== 'delivered') return '可下未发'
  }
  return '待办'
}

function todoTagClass(p) {
  if (p.status === 'needs_confirm' || p.match_confirmed === false) return 'is-warn'
  if (p.review_status === 'active') return 'is-teal'
  if (p.status === 'failed') return 'is-bad'
  const tag = todoTag(p)
  if (tag === '门禁失败') return 'is-bad'
  if (tag === '可下未发') return 'is-teal'
  return ''
}

async function load() {
  loading.value = true
  try {
    const [st, plist, jlist, fa, sys, health, lg, cg] = await Promise.all([
      api.stats().catch(() => ({})),
      api.listProjects().catch(() => []),
      api.listJobs().catch(() => []),
      api.failAnalysis({}).catch(() => null),
      api.system().catch(() => null),
      api.health().catch(() => null),
      api.layoutGate().catch(() => null),
      api.formControlsGate().catch(() => null),
    ])
    stats.value = st || {}
    projects.value = Array.isArray(plist) ? plist : []
    jobs.value = Array.isArray(jlist) ? jlist : []
    fail.value = fa
    system.value = sys
    healthOk.value = !!(health && (health.ok === true || health.status === 'ok'))
    if (lg?.data) {
      layoutGateOk.value = lg.data.ok === true
      layoutGateSummary.value = lg.data.summary || lg.message || ''
    } else {
      layoutGateOk.value = null
      layoutGateSummary.value = ''
    }
    if (cg?.data) {
      controlsGateOk.value = cg.data.ok === true
      controlsGateSummary.value = cg.data.summary || cg.message || ''
    } else {
      controlsGateOk.value = null
      controlsGateSummary.value = ''
    }
  } catch (e) {
    message.error(e?.message || '开工台加载失败')
  } finally {
    loading.value = false
    booted.value = true
  }
}

onMounted(load)
</script>

<style scoped>
.ops-col-label {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: none;
  margin-bottom: 8px;
  color: var(--muted);
}
.ops-col-hd {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}
.ops-col-hd .ops-col-label {
  margin-bottom: 0;
}
.ops-empty {
  padding: 28px 12px;
}
.ops-row {
  padding: 10px 10px;
  margin: 0 -10px;
  border-radius: 8px;
  border-bottom: none;
  cursor: pointer;
  transition: background 0.12s ease;
}
.ops-row + .ops-row {
  margin-top: 2px;
}
.ops-row:hover {
  background: color-mix(in srgb, var(--teal-soft) 45%, var(--surface-2));
}
.ops-row:hover .ops-title {
  color: var(--teal-deep);
}
.ops-row-main {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: baseline;
  color: var(--ink);
}
.ops-row-sub {
  margin-top: 3px;
  font-size: 12px;
  line-height: 1.4;
  display: flex;
  flex-wrap: wrap;
  gap: 0 4px;
  align-items: baseline;
}
.ops-row-sub .truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}
.ops-title {
  min-width: 0;
  font-weight: 550;
}
.ops-tag {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 999px;
  background: var(--surface-2);
  color: var(--ink-2);
  flex-shrink: 0;
}
.ops-tag.is-warn {
  background: var(--amber-soft);
  color: var(--amber);
}
.ops-tag.is-teal {
  background: var(--teal-soft);
  color: var(--teal-deep);
}
.ops-tag.is-bad {
  background: var(--red-soft);
  color: var(--red);
}
.surface-aside .ops-row-main strong {
  font-variant-numeric: tabular-nums;
  color: var(--teal-deep);
  min-width: 1.25em;
}
</style>
