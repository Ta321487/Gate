<template>
  <div class="page-fill">
    <h1 class="page-title">开工台</h1>
    <p class="page-desc">
      汇总待匹配、生成中、复审中与近七日失败，便于安排当日处理顺序。建项请至「项目」，任务操作请至「任务队列」，按类型排修请至「失败分析」。
    </p>
    <PageSkeleton v-if="!booted" variant="dashboard" :rows="4" />
    <template v-else>
      <div class="stats ops-stats mb-16">
        <div class="stat clickable" role="button" tabindex="0" @click="go('/projects?focus=needs_confirm')" @keydown.enter="go('/projects?focus=needs_confirm')">
          <div class="label">待匹配确认</div>
          <div class="value">{{ needsConfirm.length }}</div>
          <div class="hint">确认后方可生成</div>
        </div>
        <div class="stat clickable" role="button" tabindex="0" @click="go('/jobs')" @keydown.enter="go('/jobs')">
          <div class="label">生成中</div>
          <div class="value">{{ generatingCount }}</div>
          <div class="hint">队列中的进行中任务</div>
        </div>
        <div class="stat clickable" role="button" tabindex="0" @click="go('/fail-analysis')" @keydown.enter="go('/fail-analysis')">
          <div class="label">近 7 日失败</div>
          <div class="value">{{ failTotals.failed ?? 0 }}</div>
          <div class="hint">{{ failTotals.codes ?? 0 }} 种类型</div>
        </div>
        <div class="stat clickable" role="button" tabindex="0" @click="go('/projects?focus=review')" @keydown.enter="go('/projects?focus=review')">
          <div class="label">复审进行中</div>
          <div class="value">{{ reviewActive.length }}</div>
          <div class="hint">交付复审尚未关闭</div>
        </div>
      </div>

      <div class="grid-2 mb-16">
        <div class="panel">
          <div class="panel-hd">
            <h3>优先排修类型</h3>
            <n-button text size="small" @click="go('/fail-analysis')">失败分析 →</n-button>
          </div>
          <div class="panel-bd">
            <div v-if="!priorities.length" class="empty-hint">
              <div class="empty-title">近七日暂无集中失败</div>
              <div class="empty-desc">出现失败后，将按类型列出建议优先处理项</div>
            </div>
            <div
              v-for="p in priorities.slice(0, 6)"
              :key="p.code"
              class="ops-row"
              @click="go(`/fail-analysis?code=${encodeURIComponent(p.code)}`)"
            >
              <div class="ops-row-main">
                <strong>{{ p.count }}</strong>
                <span>{{ p.label }}</span>
                <span class="mono muted">{{ p.code }}</span>
              </div>
              <div class="ops-row-sub mono">{{ p.fix_locus }}</div>
            </div>
          </div>
        </div>

        <div class="panel">
          <div class="panel-hd">
            <h3>环境与额度</h3>
            <n-button text size="small" @click="go('/system')">运行环境 →</n-button>
          </div>
          <div class="panel-bd">
            <div class="ops-env">
              <div class="ops-env-line">
                <span class="muted">API</span>
                <span :class="healthOk ? 'ok' : 'bad'">{{ healthOk ? '正常' : '异常' }}</span>
              </div>
              <div class="ops-env-line">
                <span class="muted">JDK / Maven / Node</span>
                <span class="small">{{ envBrief }}</span>
              </div>
              <div class="ops-env-line">
                <span class="muted">学生 MySQL</span>
                <span class="small">{{ system?.mysql || '—' }}</span>
              </div>
              <div class="ops-env-line">
                <span class="muted">本月 Token</span>
                <span class="small">
                  {{ formatK(stats.monthly_tokens) }}
                  <span class="muted"> / {{ formatK(stats.monthly_budget) }}</span>
                </span>
              </div>
              <div class="ops-env-line">
                <span class="muted">履约</span>
                <span class="small">
                  待审 {{ stats.pending_review || 0 }} · 待发 {{ stats.delivery_ready || 0 }} · 已发 {{ stats.delivery_delivered || 0 }}
                </span>
              </div>
            </div>
            <div class="row mt-12" style="gap:8px;flex-wrap:wrap">
              <n-button size="small" @click="go('/llm')">大模型</n-button>
              <n-button size="small" secondary @click="load" :loading="loading">刷新</n-button>
            </div>
          </div>
        </div>
      </div>

      <div class="grid-2 mb-16">
        <div class="panel">
          <div class="panel-hd">
            <h3>待办项目</h3>
            <n-button text size="small" @click="go('/projects')">全部项目 →</n-button>
          </div>
          <div class="panel-bd">
            <div v-if="!todoProjects.length" class="empty-hint">
              <div class="empty-title">暂无待办项目</div>
              <div class="empty-desc">待匹配确认、复审中或生成失败的项目将显示于此</div>
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
              <div class="ops-row-sub muted">{{ p.domain || '—' }} · {{ p.status }}</div>
            </div>
          </div>
        </div>

        <div class="panel">
          <div class="panel-hd">
            <h3>最近失败任务</h3>
            <n-button text size="small" @click="go('/jobs')">任务队列 →</n-button>
          </div>
          <div class="panel-bd">
            <div v-if="!recentFails.length" class="empty-hint">
              <div class="empty-title">暂无失败任务</div>
              <div class="empty-desc">失败任务将显示于任务队列，并可按类型在失败分析中查看</div>
            </div>
            <div
              v-for="j in recentFails.slice(0, 8)"
              :key="j.id"
              class="ops-row"
            >
              <div class="ops-row-main">
                <span class="mono muted">#{{ j.id }}</span>
                <a class="link ops-title" href="#" @click.prevent="go(`/projects/${j.project_id}`)">
                  {{ j.project_title || j.project_id }}
                </a>
              </div>
              <div class="ops-row-sub">
                <template v-if="j.error_code">
                  <a
                    class="link mono"
                    href="#"
                    @click.prevent="go(`/fail-analysis?code=${encodeURIComponent(j.error_code)}`)"
                  >{{ j.error_code }}</a>
                  <span class="muted"> · </span>
                </template>
                <span class="muted truncate">{{ j.error || '—' }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
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

const failTotals = computed(() => fail.value?.totals || {})
const priorities = computed(() => fail.value?.priorities || [])
const needsConfirm = computed(() =>
  projects.value.filter((p) => p.status === 'needs_confirm' || p.match_confirmed === false),
)
const reviewActive = computed(() =>
  projects.value.filter((p) => p.review_status === 'active'),
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
  for (const p of [...needsConfirm.value, ...reviewActive.value, ...projects.value.filter((x) => x.status === 'failed')]) {
    if (seen.has(p.id)) continue
    seen.add(p.id)
    out.push(p)
  }
  return out
})

const envBrief = computed(() => {
  const s = system.value
  if (!s) return '—'
  const short = (v) => {
    const t = String(v || '').trim()
    if (!t) return '?'
    return t.length > 28 ? `${t.slice(0, 28)}…` : t
  }
  return `${short(s.jdk)} · ${short(s.maven)} · ${short(s.node)}`
})

function formatK(n) {
  const x = Number(n) || 0
  if (x >= 1000) return `${(x / 1000).toFixed(x >= 10000 ? 0 : 1)}k`
  return String(x)
}

function go(to) {
  router.push(to)
}

function todoTag(p) {
  if (p.status === 'needs_confirm' || p.match_confirmed === false) return '待匹配'
  if (p.review_status === 'active') return '复审中'
  if (p.status === 'failed') return '生成失败'
  return '待办'
}

function todoTagClass(p) {
  if (p.status === 'needs_confirm' || p.match_confirmed === false) return 'is-warn'
  if (p.review_status === 'active') return 'is-teal'
  if (p.status === 'failed') return 'is-bad'
  return ''
}

async function load() {
  loading.value = true
  try {
    const [st, plist, jlist, fa, sys, health] = await Promise.all([
      api.stats().catch(() => ({})),
      api.listProjects().catch(() => []),
      api.listJobs().catch(() => []),
      api.failAnalysis({}).catch(() => null),
      api.system().catch(() => null),
      api.health().catch(() => null),
    ])
    stats.value = st || {}
    projects.value = Array.isArray(plist) ? plist : []
    jobs.value = Array.isArray(jlist) ? jlist : []
    fail.value = fa
    system.value = sys
    healthOk.value = !!(health && (health.ok === true || health.status === 'ok'))
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
.ops-stats {
  margin-bottom: 16px;
}
.ops-row {
  padding: 10px 0;
  border-bottom: 1px solid var(--line-soft);
  cursor: pointer;
}
.ops-row:last-child {
  border-bottom: 0;
}
.ops-row:hover .ops-title {
  color: var(--teal);
}
.ops-row-main {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: baseline;
  color: var(--ink);
}
.ops-row-sub {
  margin-top: 4px;
  font-size: 12px;
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
}
.ops-tag {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 4px;
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
.ops-env {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.ops-env-line {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 13px;
  align-items: baseline;
}
.ops-env-line .ok {
  color: var(--green);
}
.ops-env-line .bad {
  color: var(--red);
}
.mb-16 {
  margin-bottom: 16px;
}
.mt-12 {
  margin-top: 12px;
}
</style>
