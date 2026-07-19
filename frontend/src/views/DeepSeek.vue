<template>
  <div>
    <h1 class="page-title">DeepSeek</h1>
    <p class="page-desc">连接、用量与阶段开关。旧模型名将于 7/24 停用，请改用 V4。</p>

    <div class="grid-2 mb-16">
      <div class="panel">
        <div class="panel-hd">
          <h3>连接</h3>
          <span class="pill" :class="cfg.key_configured ? 'pill-green' : 'pill-amber'">{{ cfg.key_configured ? '已配置' : '未配置 Key' }}</span>
        </div>
        <div class="panel-bd stack">
          <n-form-item label="API Key">
            <n-input :value="cfg.key_masked" disabled />
          </n-form-item>
          <n-form-item label="Base URL">
            <n-input v-model:value="form.base_url" />
          </n-form-item>
          <div class="grid-2">
            <n-form-item label="模型">
              <n-select v-model:value="form.model" :options="modelOptions" />
            </n-form-item>
            <n-form-item label="Thinking">
              <n-select v-model:value="form.thinking" :options="[{label:'开启 · 更准更贵',value:true},{label:'关闭 · 更快更省',value:false}]" />
            </n-form-item>
          </div>
          <div class="row">
            <n-button type="primary" size="small" @click="test">测试连接</n-button>
            <n-button size="small" @click="save">保存</n-button>
            <span class="small muted">{{ latency }}</span>
          </div>
        </div>
      </div>
      <div class="panel">
        <div class="panel-hd">
          <h3>用量与预算</h3>
          <n-button size="small" :loading="balanceLoading" @click="loadBalance">刷新</n-button>
        </div>
        <div class="panel-bd">
          <div class="balance-box mb-16">
            <div class="small muted mb-8">DeepSeek 账户余额（官方 /user/balance）</div>
            <template v-if="balance.ok && balance.balance_infos?.length">
              <div v-for="(b, i) in balance.balance_infos" :key="i" class="balance-row">
                <strong class="mono">{{ b.total_balance }} {{ b.currency }}</strong>
                <span class="small muted">充值 {{ b.topped_up_balance }} · 赠送 {{ b.granted_balance }}</span>
              </div>
              <div class="small mt-8" :class="balance.is_available === false ? 'warn' : 'muted'">
                {{ balance.is_available === false ? '当前余额可能不足以调用 API' : '账户可调用' }}
              </div>
            </template>
            <div v-else class="small muted">{{ balance.message || '点击刷新查询余额' }}</div>
          </div>
          <div class="small mb-8">
            本月 Token ·
            <span class="mono">{{ cfg.monthly_tokens_used || 0 }}</span>
            /
            <span class="mono">{{ form.monthly_token_budget || cfg.monthly_token_budget }}</span>
            <span v-if="monthPct >= 90" class="warn"> · 接近上限</span>
          </div>
          <div class="progress mb-16"><i :style="{ width: monthPct + '%' }" /></div>
          <n-form-item label="月度 Token 预算">
            <n-input-number v-model:value="form.monthly_token_budget" :min="10000" :step="10000" style="width:100%" />
          </n-form-item>
          <n-form-item label="项目级 Token 预算">
            <n-input-number v-model:value="form.project_token_budget" :min="1000" :step="10000" style="width:100%" />
          </n-form-item>
          <n-form-item label="修复轮次上限">
            <n-input-number v-model:value="form.fix_rounds_max" :min="0" :max="10" style="width:100%" />
          </n-form-item>
        </div>
      </div>
    </div>

    <div class="panel mb-16">
      <div class="panel-hd"><h3>阶段开关</h3><span class="small muted">关闭后仍可确定性 bake</span></div>
      <div class="panel-bd">
        <div class="row" style="justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--line-soft)">
          <div><strong>Agent A · Spec</strong><div class="small muted">润色开题摘要/功能点；关则仅关键词</div></div>
          <n-switch v-model:value="form.parse_spec" />
        </div>
        <div class="row" style="justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--line-soft)">
          <div><strong>Agent B · 填岛</strong><div class="small muted">labels/seeds 白名单 JSON，不改源码</div></div>
          <n-switch v-model:value="form.island_fill" />
        </div>
        <div class="row" style="justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--line-soft)">
          <div><strong>Agent C · 编译修复</strong><div class="small muted">mvn 失败诊断并重放交付配置</div></div>
          <n-switch v-model:value="form.auto_fix" />
        </div>
        <div class="row" style="justify-content:space-between;padding:10px 0">
          <div><strong>Agent D · QA</strong><div class="small muted">漂移扫描 + 摘要，写入 islands/qa_report.json</div></div>
          <n-switch v-model:value="form.qa_report" />
        </div>
        <div class="row mt-12">
          <n-button type="primary" size="small" @click="save">保存开关</n-button>
        </div>
      </div>
    </div>

    <div class="panel mb-16">
      <div class="panel-hd">
        <h3>按项目用量</h3>
        <n-button size="small" :loading="usageLoading" @click="loadUsage">刷新</n-button>
      </div>
      <div class="panel-bd">
        <div class="row mb-12" style="gap:10px;flex-wrap:wrap">
          <n-date-picker
            v-model:value="usageRange"
            type="datetimerange"
            clearable
            size="small"
            :shortcuts="dateRangeShortcuts"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            style="width:340px"
            @update:value="onUsageRange"
          />
          <n-input
            v-model:value="usageQ"
            clearable
            size="small"
            placeholder="项目 ID…"
            style="width:200px"
            @update:value="onUsageSearch"
          />
        </div>
        <p class="small muted mb-12">超项目预算或月度预算时 Agent 会跳过 LLM · 点项目可筛调用</p>
        <n-data-table
          v-if="projectUsages.length"
          :columns="usageCols"
          :data="projectUsages"
          :row-key="(r) => r.project_id"
          :bordered="false"
          size="small"
          remote
          :row-props="usageRowProps"
          @update:sorter="onUsageSorter"
        />
        <div v-else-if="usageLoading" class="skel-stack" style="padding:8px 0">
          <div v-for="i in 4" :key="i" class="skel skel-row-bar" />
        </div>
        <div v-else class="empty-hint">无匹配项目</div>
        <div v-if="usageTotal > 0" class="pager-row">
          <span class="small muted">共 {{ usageTotal }} 个项目</span>
          <n-pagination
            v-model:page="usagePage"
            v-model:page-size="usagePageSize"
            :item-count="usageTotal"
            :page-sizes="[10, 20, 50]"
            show-size-picker
            size="small"
            @update:page="loadUsage"
            @update:page-size="onUsagePageSize"
          />
        </div>
      </div>
    </div>

    <div class="panel">
      <div class="panel-hd">
        <h3>最近调用</h3>
        <n-button size="small" :loading="callsLoading" @click="loadCalls">刷新</n-button>
      </div>
      <div class="panel-bd">
        <div class="row mb-12" style="gap:10px;flex-wrap:wrap">
          <n-date-picker
            v-model:value="callRange"
            type="datetimerange"
            clearable
            size="small"
            :shortcuts="dateRangeShortcuts"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            style="width:340px"
            @update:value="onCallFilter"
          />
          <n-input
            v-model:value="callFilter.project_id"
            clearable
            size="small"
            placeholder="项目 ID（精确）"
            style="width:180px"
            @update:value="onCallFilter"
          />
          <n-select
            v-model:value="callFilter.stage"
            clearable
            size="small"
            placeholder="阶段"
            :options="stageOptions"
            style="width:130px"
            @update:value="onCallFilter"
          />
          <n-select
            v-model:value="callFilter.ok"
            clearable
            size="small"
            placeholder="结果"
            :options="okOptions"
            style="width:100px"
            @update:value="onCallFilter"
          />
          <n-input
            v-model:value="callFilter.q"
            clearable
            size="small"
            placeholder="明细 / 阶段关键字…"
            style="width:180px"
            @update:value="onCallSearch"
          />
        </div>
        <n-data-table
          v-if="calls.length"
          :columns="cols"
          :data="calls"
          :bordered="false"
          size="small"
          :row-key="(r) => r.id"
        />
        <div v-else-if="callsLoading" class="skel-stack" style="padding:8px 0">
          <div v-for="i in 4" :key="i" class="skel skel-row-bar" />
        </div>
        <div v-else class="empty-hint">无匹配调用</div>
        <div v-if="callsTotal > 0" class="pager-row">
          <span class="small muted">共 {{ callsTotal }} 条</span>
          <n-pagination
            v-model:page="callsPage"
            v-model:page-size="callsPageSize"
            :item-count="callsTotal"
            :page-sizes="[10, 20, 50]"
            show-size-picker
            size="small"
            @update:page="loadCalls"
            @update:page-size="onCallsPageSize"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, h, onMounted, reactive, ref } from 'vue'
import { NButton, NTag } from 'naive-ui'
import { api, message } from '../api'
import {
  dateRangeShortcuts,
  debounce,
  monthRangeMs,
  rangeToParams,
} from '../opsShared'

const cfg = reactive({})
const form = reactive({
  base_url: '',
  model: 'deepseek-v4-flash',
  thinking: true,
  parse_spec: true,
  island_fill: true,
  auto_fix: true,
  qa_report: false,
  project_token_budget: 100000,
  monthly_token_budget: 1000000,
  fix_rounds_max: 5,
})
const latency = ref('')
const calls = ref([])
const projectUsages = ref([])
const usageLoading = ref(false)
const callsLoading = ref(false)
const usageQ = ref('')
const usageRange = ref(monthRangeMs())
const usagePage = ref(1)
const usagePageSize = ref(10)
const usageTotal = ref(0)
/** @type {import('vue').Ref<{ columnKey: string, order: 'ascend' | 'descend' | false } | null>} */
const usageSorter = ref({ columnKey: 'tokens', order: 'descend' })
const callRange = ref(monthRangeMs())
const callsPage = ref(1)
const callsPageSize = ref(20)
const callsTotal = ref(0)
const callFilter = reactive({
  project_id: null,
  stage: null,
  ok: null,
  q: '',
})
const balanceLoading = ref(false)
const balance = reactive({
  ok: false,
  message: '',
  is_available: null,
  balance_infos: [],
})
const modelOptions = [
  { label: 'deepseek-v4-flash · 日常 / 省钱', value: 'deepseek-v4-flash' },
  { label: 'deepseek-v4-pro · 难任务 / 质量', value: 'deepseek-v4-pro' },
]
const stageOptions = [
  { label: 'parse_spec', value: 'parse_spec' },
  { label: 'island_fill', value: 'island_fill' },
  { label: 'auto_fix', value: 'auto_fix' },
  { label: 'qa_report', value: 'qa_report' },
  { label: 'emit', value: 'emit' },
]
const okOptions = [
  { label: 'OK', value: true },
  { label: 'FAIL', value: false },
]
const monthPct = computed(() => {
  const budget = form.monthly_token_budget || cfg.monthly_token_budget || 1
  const used = cfg.monthly_tokens_used || 0
  return Math.min(100, Math.round((used / budget) * 100))
})
function usageSortOrder(key) {
  const s = usageSorter.value
  if (!s || s.columnKey !== key || !s.order) return false
  return s.order
}

const usageCols = computed(() => [
  {
    title: '项目',
    key: 'project_id',
    ellipsis: { tooltip: true },
    render: (r) =>
      h(
        NButton,
        {
          text: true,
          type: 'primary',
          size: 'tiny',
          onClick: (e) => {
            e.stopPropagation()
            filterCallsByProject(r.project_id)
          },
        },
        { default: () => r.project_id }
      ),
  },
  {
    title: 'Tokens',
    key: 'tokens',
    width: 100,
    sorter: true,
    sortOrder: usageSortOrder('tokens'),
    render: (r) => h('span', { class: 'mono' }, String(r.tokens)),
  },
  {
    title: '次数',
    key: 'calls',
    width: 70,
    sorter: true,
    sortOrder: usageSortOrder('calls'),
  },
  {
    title: '占项目预算',
    key: 'pct',
    width: 120,
    sorter: true,
    sortOrder: usageSortOrder('pct'),
    render: (r) => {
      const budget = form.project_token_budget || cfg.project_token_budget || 1
      const pct = Math.min(100, Math.round((r.tokens / budget) * 100))
      const over = r.tokens >= budget
      return h('span', { class: over ? 'warn mono' : 'mono' }, `${pct}%`)
    },
  },
  {
    title: '最近',
    key: 'last_at',
    width: 160,
    sorter: true,
    sortOrder: usageSortOrder('last_at'),
    render: (r) => (r.last_at ? new Date(r.last_at).toLocaleString() : '—'),
  },
])
const cols = [
  { title: '时间', key: 'created_at', width: 160, render: (r) => (r.created_at ? new Date(r.created_at).toLocaleString() : '—') },
  { title: '项目', key: 'project_id', ellipsis: { tooltip: true } },
  { title: '阶段', key: 'stage', width: 110 },
  { title: 'Tokens', key: 'tokens', width: 90, render: (r) => h('span', { class: 'mono' }, String(r.tokens)) },
  { title: '结果', key: 'ok', width: 70, render: (r) => h(NTag, { size: 'small', type: r.ok ? 'success' : 'error', bordered: false }, { default: () => (r.ok ? 'OK' : 'FAIL') }) },
  { title: '明细', key: 'detail', ellipsis: { tooltip: true }, render: (r) => r.detail || '—' },
]

function usageRowProps(row) {
  return {
    style: 'cursor:pointer',
    onClick: () => filterCallsByProject(row.project_id),
  }
}

function filterCallsByProject(pid) {
  callFilter.project_id = pid
  callRange.value = usageRange.value ? [...usageRange.value] : null
  callsPage.value = 1
  loadCalls()
}

async function loadBalance() {
  balanceLoading.value = true
  try {
    const res = await api.deepseekBalance()
    Object.assign(balance, {
      ok: !!res.ok,
      message: res.message || '',
      is_available: res.is_available,
      balance_infos: res.balance_infos || [],
    })
    if (!res.ok) message.warning(res.message || '余额查询失败')
  } finally {
    balanceLoading.value = false
  }
}

function migrateModel(m) {
  if (m === 'deepseek-chat' || m === 'deepseek-reasoner') return 'deepseek-v4-flash'
  return m || 'deepseek-v4-flash'
}

async function loadUsage() {
  usageLoading.value = true
  try {
    const s = usageSorter.value
    const params = {
      q: usageQ.value || undefined,
      page: usagePage.value,
      page_size: usagePageSize.value,
      ...rangeToParams(usageRange.value),
    }
    if (s?.columnKey && s.order) {
      params.sort_by = s.columnKey
      params.sort_order = s.order === 'ascend' ? 'asc' : 'desc'
    }
    const res = await api.deepseekUsage(params)
    projectUsages.value = res.items || []
    usageTotal.value = res.total || 0
  } finally {
    usageLoading.value = false
  }
}

function onUsageSorter(sorter) {
  // remote：单列排序；取消时回退 tokens 降序
  const next = Array.isArray(sorter) ? sorter[0] : sorter
  if (next?.columnKey && next.order) {
    usageSorter.value = { columnKey: next.columnKey, order: next.order }
  } else {
    usageSorter.value = { columnKey: 'tokens', order: 'descend' }
  }
  usagePage.value = 1
  loadUsage()
}

async function loadCalls() {
  callsLoading.value = true
  try {
    const params = {
      page: callsPage.value,
      page_size: callsPageSize.value,
      ...rangeToParams(callRange.value),
    }
    if (callFilter.project_id) params.project_id = callFilter.project_id
    if (callFilter.stage) params.stage = callFilter.stage
    if (callFilter.ok !== null && callFilter.ok !== undefined) params.ok = callFilter.ok
    if (callFilter.q) params.q = callFilter.q
    const res = await api.deepseekCalls(params)
    if (Array.isArray(res)) {
      calls.value = res
      callsTotal.value = res.length
    } else {
      calls.value = res.items || []
      callsTotal.value = res.total || 0
    }
  } finally {
    callsLoading.value = false
  }
}

const onUsageSearch = debounce(() => {
  usagePage.value = 1
  loadUsage()
}, 300)

const onCallSearch = debounce(() => {
  callsPage.value = 1
  loadCalls()
}, 300)

function onUsageRange() {
  usagePage.value = 1
  loadUsage()
}

function onCallFilter() {
  callsPage.value = 1
  loadCalls()
}

function onUsagePageSize() {
  usagePage.value = 1
  loadUsage()
}

function onCallsPageSize() {
  callsPage.value = 1
  loadCalls()
}

async function load() {
  Object.assign(cfg, await api.deepseek())
  form.base_url = cfg.base_url
  form.model = migrateModel(cfg.model)
  form.thinking = cfg.thinking
  form.parse_spec = cfg.parse_spec
  form.island_fill = cfg.island_fill
  form.auto_fix = cfg.auto_fix
  form.qa_report = cfg.qa_report
  form.project_token_budget = cfg.project_token_budget
  form.monthly_token_budget = cfg.monthly_token_budget
  form.fix_rounds_max = cfg.fix_rounds_max
  await Promise.all([loadUsage(), loadCalls(), loadBalance()])
}

async function save() {
  Object.assign(cfg, await api.saveDeepseek({ ...form }))
  message.success('已保存（Key 仍只读环境变量）')
}

async function test() {
  latency.value = '测试中…'
  const res = await api.testDeepseek()
  latency.value = res.message
  if (res.ok) message.success(res.message)
  else message.error(res.message)
}

onMounted(load)
</script>

<style scoped>
.balance-box {
  padding: 12px 14px;
  border-radius: 10px;
  background: var(--bg-soft, #f5f7fa);
  border: 1px solid var(--line-soft, #e8eef2);
}
.balance-row {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.balance-row + .balance-row { margin-top: 8px; }
.warn { color: #c45c26; }
.empty-hint {
  padding: 20px 16px;
  color: var(--muted, #888);
  font-size: 13px;
}
.pager-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 12px;
  padding-top: 4px;
}
</style>
