<template>
  <div class="page-fill surface-page">
    <div class="surface-toolbar">
      <div>
        <h1 class="page-title">规则参数</h1>
        <p class="page-desc" style="margin-bottom:0">
          维护超时天数、预约提前量、积分倍率等默认值；出包写入 schema.ruleParams，已知键仅补缺不覆盖扫词结果。
        </p>
      </div>
      <AssetDeskActions
        :gap-loading="gapLoading"
        :migrating="migrating"
        create-label="登记参数"
        @check="scanGaps"
        @migrate="migrate"
        @create="openCreate"
      />
    </div>

    <PageSkeleton v-if="!booted" variant="dashboard" :rows="4" />
    <template v-else>
      <div class="stats mb-12" style="grid-template-columns:repeat(2,1fr);max-width:360px">
        <div class="stat">
          <div class="label">参数</div>
          <div class="value">{{ total }}</div>
        </div>
        <div class="stat">
          <div class="label">待补</div>
          <div class="value" :class="{ bad: gapsScanned && gapCount > 0 }">{{ gapStatDisplay(gapsScanned, gapCount) }}</div>
        </div>
      </div>

      <n-tabs v-model:value="mainTab" type="line" size="small" class="mb-12">
        <n-tab-pane name="entries" tab="参数" />
        <n-tab-pane name="gaps" tab="待补" />
      </n-tabs>

      <div v-show="mainTab === 'entries'" class="panel panel-quiet">
        <div class="panel-hd">
          <div class="row asset-desk-filter-row">
            <n-select
              v-model:value="domain"
              size="small"
              clearable
              placeholder="全部域"
              :options="domainFilterOptions"
              style="width:200px"
              @update:value="reloadFromTop"
            />
            <n-input
              v-model:value="q"
              size="small"
              clearable
              placeholder="规则 / 名称 / 落点键"
              style="width:220px"
              @keyup.enter="reloadFromTop"
            />
            <n-button size="small" @click="reloadFromTop">查询</n-button>
          </div>
        </div>
        <div class="panel-bd">
          <div v-if="!items.length" class="empty-hint">
            <div class="empty-title">还没有参数</div>
            <div class="empty-desc">用顶栏导入或登记一条。</div>
          </div>
          <template v-else>
            <div class="asset-desk-table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>域</th>
                    <th>规则</th>
                    <th>名称</th>
                    <th>数值</th>
                    <th>落点键</th>
                    <th style="width:100px"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="row in pagedItems"
                    :key="row.id"
                    :class="{ 'is-editing': editingId === row.id }"
                  >
                    <td class="muted">{{ domainLabel(row.domain_id) }}</td>
                    <td class="mono">{{ row.rule_id }}</td>
                    <td>{{ row.label_zh || '—' }}</td>
                    <td>{{ formatValue(row) }}</td>
                    <td class="mono muted">{{ row.schema_key || '—' }}</td>
                    <td>
                      <div class="row" style="gap:4px">
                        <n-button size="small" quaternary @click="editRow(row)">改</n-button>
                        <n-button
                          size="small"
                          quaternary
                          type="error"
                          :loading="deletingId === row.id"
                          @click="remove(row)"
                        >删</n-button>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div class="pager-row">
              <span class="small muted">共 {{ total }} 条</span>
              <n-pagination
                v-model:page="page"
                v-model:page-size="pageSize"
                :item-count="total"
                :page-sizes="[20, 50]"
                show-size-picker
                size="small"
                @update:page-size="onPageSize"
              />
            </div>
          </template>
        </div>
      </div>

      <div v-show="mainTab === 'gaps'" class="panel panel-quiet">
        <div class="panel-bd">
          <div v-if="!gaps.length" class="empty-hint">
            <div class="empty-title">{{ gapsScanned ? '没有待补项' : '还没检查过' }}</div>
            <div class="empty-desc">
              {{ gapsScanned ? '种子参数已齐。' : '点顶栏「检查待补」扫描缺口。' }}
            </div>
          </div>
          <template v-else>
            <div class="asset-desk-table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>域</th>
                    <th>规则</th>
                    <th>说明</th>
                    <th style="width:100px"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="(g, idx) in pagedGaps"
                    :key="`${g.domain_id}-${g.rule_id}-${idx}`"
                  >
                    <td class="muted">{{ domainLabel(g.domain_id) }}</td>
                    <td class="mono">{{ g.rule_id }}</td>
                    <td>{{ g.reason }}</td>
                    <td>
                      <n-button size="small" quaternary @click="fillFromGap(g)">补</n-button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div class="pager-row">
              <span class="small muted">共 {{ gaps.length }} 条</span>
              <n-pagination
                v-model:page="gapPage"
                v-model:page-size="gapPageSize"
                :item-count="gaps.length"
                size="small"
              />
            </div>
          </template>
        </div>
      </div>
    </template>

    <n-drawer v-model:show="drawerOpen" :width="440" placement="right" @after-leave="onDrawerLeave">
      <n-drawer-content :title="editingId ? '改参数' : '登记参数'" closable>
        <div class="asset-desk-drawer-form">
          <n-form-item label="域" :show-feedback="false">
            <n-select
              v-model:value="form.domain_id"
              size="small"
              filterable
              :disabled="identityLocked"
              :options="formDomainOptions"
            />
          </n-form-item>
          <n-form-item label="规则 ID" :show-feedback="false">
            <n-select
              v-model:value="form.rule_id"
              size="small"
              filterable
              tag
              :disabled="identityLocked"
              :options="ruleIdOptions"
              placeholder="如 order_pay_timeout_min"
            />
          </n-form-item>
          <n-form-item label="名称" :show-feedback="false">
            <n-input
              v-model:value="form.label_zh"
              size="small"
              :maxlength="64"
              show-count
              placeholder="学生可见说明名"
            />
          </n-form-item>
          <n-form-item label="数值" :show-feedback="false">
            <n-input-number
              v-model:value="form.value_num"
              size="small"
              :min="0"
              style="width:100%"
            />
          </n-form-item>
          <n-form-item label="单位" :show-feedback="false">
            <n-select
              v-model:value="form.unit_zh"
              size="small"
              filterable
              tag
              clearable
              :options="unitOptions"
              placeholder="分钟 / 小时 / 倍"
            />
          </n-form-item>
          <n-form-item label="落点键" :show-feedback="false">
            <n-select
              v-model:value="form.schema_key"
              size="small"
              filterable
              clearable
              :options="schemaKeyOptions"
              placeholder="写入 schema 的键，可空"
            />
          </n-form-item>
          <n-form-item label="排序" :show-feedback="false">
            <n-input-number v-model:value="form.sort" size="small" :min="0" style="width:100%" />
          </n-form-item>
          <p class="small muted">{{ formHint }}</p>
          <div class="row" style="gap:8px;justify-content:flex-end">
            <n-button size="small" @click="closeDrawer">退出编辑</n-button>
            <n-button size="small" type="primary" :loading="saving" @click="save">保存</n-button>
          </div>
        </div>
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { api, message } from '../api'
import { gapStatDisplay } from '../utils/assetDesk'
import { confirm } from '../ui'
import PageSkeleton from '../components/PageSkeleton.vue'
import AssetDeskActions from '../components/AssetDeskActions.vue'

const booted = ref(false)
const migrating = ref(false)
const gapLoading = ref(false)
const saving = ref(false)
const deletingId = ref(0)
const editingId = ref(0)
const fromGap = ref(false)
const drawerOpen = ref(false)

const mainTab = ref('entries')
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const domain = ref(null)
const q = ref('')

const gaps = ref([])
const gapCount = ref(0)
const gapsScanned = ref(false)
const gapPage = ref(1)
const gapPageSize = ref(20)

const meta = reactive({
  domains: [],
  rule_ids: [],
  schema_key_options: [],
  unit_options: [],
})

const form = reactive({
  domain_id: '*',
  rule_id: '',
  label_zh: '',
  value_num: 0,
  unit_zh: null,
  schema_key: null,
  sort: 0,
})

const identityLocked = computed(() => !!editingId.value || fromGap.value)

const formHint = computed(() => {
  if (identityLocked.value) {
    return editingId.value
      ? '域与规则 ID 已锁定，可改名称、数值与落点键。更换键请删除后重新登记。'
      : '待补项标识已锁定，请补全名称与数值后保存。'
  }
  return '具名域优先生效，可覆盖跨域壳默认。落点键已有扫词/加厚写入时，出包不会用本台数值覆盖。'
})

const domainFilterOptions = computed(() =>
  meta.domains.map((d) => ({
    label: domainSelectLabel(d.id),
    value: d.id,
  })),
)

const formDomainOptions = computed(() => domainFilterOptions.value)

const ruleIdOptions = computed(() => {
  const set = new Set(meta.rule_ids || [])
  if (form.rule_id) set.add(form.rule_id)
  return [...set].map((r) => ({ label: r, value: r }))
})

const schemaKeyOptions = computed(() =>
  meta.schema_key_options.length
    ? meta.schema_key_options
    : [
        { value: 'orderTimeoutMinutes', label: 'orderTimeoutMinutes' },
        { value: 'reservationAdvanceHours', label: 'reservationAdvanceHours' },
        { value: 'pointsEarnRate', label: 'pointsEarnRate' },
      ],
)

const unitOptions = computed(() => {
  const base = meta.unit_options.length
    ? meta.unit_options
    : [
        { value: '分钟', label: '分钟' },
        { value: '小时', label: '小时' },
        { value: '倍', label: '倍' },
        { value: '天', label: '天' },
      ]
  if (form.unit_zh && !base.some((o) => o.value === form.unit_zh)) {
    return [...base, { value: form.unit_zh, label: form.unit_zh }]
  }
  return base
})

const pagedItems = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return items.value.slice(start, start + pageSize.value)
})

const pagedGaps = computed(() => {
  const start = (gapPage.value - 1) * gapPageSize.value
  return gaps.value.slice(start, start + gapPageSize.value)
})

function domainLabel(dom) {
  if (!dom || dom === '*') return '跨域壳默认'
  const hit = meta.domains.find((d) => d.id === dom)
  return hit ? hit.name || dom : dom
}

function domainSelectLabel(dom) {
  if (!dom || dom === '*') return '跨域壳默认（*）'
  return `${domainLabel(dom)}（${dom}）`
}

function formatValue(row) {
  const n = row.value_num
  const u = row.unit_zh || ''
  if (n === null || n === undefined || n === '') return '—'
  return u ? `${n} ${u}` : String(n)
}


function onPageSize() {
  page.value = 1
}

function reloadFromTop() {
  page.value = 1
  load()
}

function resetForm() {
  form.domain_id = '*'
  form.rule_id = ''
  form.label_zh = ''
  form.value_num = 0
  form.unit_zh = null
  form.schema_key = null
  form.sort = 0
  editingId.value = 0
  fromGap.value = false
}

function closeDrawer() {
  drawerOpen.value = false
}

function onDrawerLeave() {
  resetForm()
}

function openCreate() {
  resetForm()
  drawerOpen.value = true
}

function editRow(row) {
  fromGap.value = false
  editingId.value = row.id || 0
  form.domain_id = row.domain_id || '*'
  form.rule_id = row.rule_id || ''
  form.label_zh = row.label_zh || ''
  form.value_num = Number(row.value_num) || 0
  form.unit_zh = row.unit_zh || null
  form.schema_key = row.schema_key || null
  form.sort = row.sort ?? 0
  drawerOpen.value = true
}

function fillFromGap(g) {
  editingId.value = 0
  fromGap.value = true
  form.domain_id = g.domain_id || '*'
  form.rule_id = g.rule_id || ''
  form.label_zh = g.rule_id || ''
  form.value_num = 0
  form.unit_zh = null
  form.schema_key = null
  form.sort = 0
  drawerOpen.value = true
}

async function loadMeta() {
  try {
    const res = await api.ruleParamsMeta()
    meta.domains = res.domains || []
    meta.rule_ids = res.rule_ids || []
    meta.schema_key_options = res.schema_key_options || []
    meta.unit_options = res.unit_options || []
  } catch (e) {
    message.error(e?.message || '加载选项失败')
  }
}

async function load() {
  try {
    const params = {}
    if (domain.value !== null && domain.value !== undefined) params.domain_id = domain.value
    if (q.value) params.q = q.value
    const res = await api.ruleParams(params)
    items.value = res.items || []
    total.value = res.total ?? items.value.length
    const maxPage = Math.max(1, Math.ceil((total.value || 0) / pageSize.value) || 1)
    if (page.value > maxPage) page.value = maxPage
  } catch (e) {
    message.error(e?.message || '加载失败')
  } finally {
    booted.value = true
  }
}

async function migrate() {
  migrating.value = true
  try {
    const res = await api.ruleParamsMigrate()
    domain.value = null
    q.value = ''
    page.value = 1
    const n = res.inserted ?? 0
    message.success(n > 0 ? `已追加 ${n} 条` : '没有缺项可追加')
    await loadMeta()
    await load()
    mainTab.value = 'entries'
  } catch (e) {
    message.error(e?.message || '导入失败')
  } finally {
    migrating.value = false
  }
}

async function scanGaps() {
  gapLoading.value = true
  try {
    const res = await api.ruleParamsGaps()
    gaps.value = res.gaps || []
    gapCount.value = res.gap_count ?? gaps.value.length
    gapsScanned.value = true
    gapPage.value = 1
    mainTab.value = 'gaps'
    if (gapCount.value) message.info(`待补 ${gapCount.value} 条`)
    else message.success('没有待补项')
  } catch (e) {
    message.error(e?.message || '检查失败')
  } finally {
    gapLoading.value = false
  }
}

async function save() {
  if (!form.rule_id?.trim()) {
    message.warning('规则 ID 必填')
    return
  }
  if (form.value_num === null || form.value_num === undefined || Number.isNaN(form.value_num)) {
    message.warning('请填写数值')
    return
  }
  saving.value = true
  try {
    await api.ruleParamsUpsert({
      domain_id: form.domain_id || '*',
      rule_id: form.rule_id.trim(),
      label_zh: (form.label_zh || '').trim(),
      value_num: Number(form.value_num),
      unit_zh: form.unit_zh || '',
      schema_key: form.schema_key || '',
      sort: form.sort ?? 0,
      source: 'manual',
    })
    message.success(editingId.value ? '已保存修改' : '已保存')
    drawerOpen.value = false
    resetForm()
    await loadMeta()
    await load()
    if (gapsScanned.value) {
      const gapRes = await api.ruleParamsGaps()
      gaps.value = gapRes.gaps || []
      gapCount.value = gapRes.gap_count ?? gaps.value.length
    }
  } catch (e) {
    message.error(e?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function remove(row) {
  if (!row?.id) return
  const ok = await confirm(`删除「${row.rule_id}」？`, {
    title: '删除参数',
    positiveText: '删除',
  })
  if (!ok) return
  deletingId.value = row.id
  try {
    await api.ruleParamsDelete(row.id)
    message.success('已删除')
    if (editingId.value === row.id) closeDrawer()
    await load()
  } catch (e) {
    message.error(e?.message || '删除失败')
  } finally {
    deletingId.value = 0
  }
}

onMounted(async () => {
  await loadMeta()
  await load()
})
</script>

