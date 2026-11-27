<template>
  <div class="page-fill surface-page">
    <div class="surface-toolbar">
      <div>
        <h1 class="page-title">演示剧本</h1>
        <p class="page-desc" style="margin-bottom:0">
          配置各域答辩演示步骤与所需业务数据，出包写入演示剧本。
        </p>
      </div>
      <AssetDeskActions
        :gap-loading="gapLoading"
        :migrating="migrating"
        :check-disabled="!gapDomain"
        migrate-label="导入初始剧本"
        create-label="登记步骤"
        @check="scanGaps"
        @migrate="migrate"
        @create="openCreate"
      />
    </div>

    <PageSkeleton v-if="!booted" variant="dashboard" :rows="4" />
    <template v-else>
      <div class="stats mb-12" style="grid-template-columns:repeat(2,1fr);max-width:360px">
        <div class="stat">
          <div class="label">步骤</div>
          <div class="value">{{ total }}</div>
        </div>
        <div class="stat">
          <div class="label">待补</div>
          <div class="value" :class="{ bad: gapsScanned && gapCount > 0 }">{{ gapStatDisplay(gapsScanned, gapCount) }}</div>
        </div>
      </div>

      <n-tabs v-model:value="mainTab" type="line" size="small" class="mb-12">
        <n-tab-pane name="entries" tab="步骤" />
        <n-tab-pane name="gaps" tab="待补" />
      </n-tabs>

      <div v-show="mainTab === 'entries'" class="panel panel-quiet">
        <div class="panel-hd">
          <div class="row asset-desk-filter-row">
            <n-select
              v-model:value="domain"
              size="small"
              clearable
              filterable
              placeholder="全部域"
              style="width:220px"
              :consistent-menu-width="false"
              :menu-props="{ style: { minWidth: '320px' } }"
              :options="domainFilterOptions"
              @update:value="reloadFromTop"
            />
            <n-select
              v-model:value="scriptId"
              size="small"
              clearable
              placeholder="全部剧本"
              style="width:140px"
              :options="scriptFilterOptions"
              @update:value="reloadFromTop"
            />
            <n-input
              v-model:value="q"
              size="small"
              clearable
              placeholder="标题 / 角色"
              style="width:180px"
              @keyup.enter="reloadFromTop"
            />
            <n-button size="small" @click="reloadFromTop">查询</n-button>
          </div>
        </div>
        <div class="panel-bd">
          <div v-if="!items.length" class="empty-hint">
            <div class="empty-title">还没有步骤</div>
            <div class="empty-desc">用顶栏导入或登记一条。</div>
          </div>
          <template v-else>
            <div class="asset-desk-table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>域</th>
                    <th>皮</th>
                    <th>剧本</th>
                    <th>步</th>
                    <th>角色</th>
                    <th>标题</th>
                    <th>所需数据</th>
                    <th style="width:100px"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="row in pagedItems"
                    :key="row.id"
                    :class="{ 'is-editing': editingId === row.id }"
                  >
                    <td>{{ domainLabel(row.domain_id) }}</td>
                    <td class="mono muted">{{ row.skin_id || '—' }}</td>
                    <td class="mono">{{ row.script_id }}</td>
                    <td class="mono">{{ row.step_no }}</td>
                    <td>{{ roleLabel(row.role) }}</td>
                    <td>{{ row.title_zh }}</td>
                    <td class="muted">{{ needRowsSummary(row.need_rows) }}</td>
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
                :page-sizes="[10, 20, 50]"
                show-size-picker
                size="small"
                @update:page-size="onPageSize"
              />
            </div>
          </template>
        </div>
      </div>

      <div v-show="mainTab === 'gaps'" class="panel panel-quiet">
        <div class="panel-hd">
          <div class="row asset-desk-filter-row" style="align-items:center">
            <n-select
              v-model:value="gapDomain"
              size="small"
              filterable
              placeholder="选域再检查"
              style="width:260px"
              :consistent-menu-width="false"
              :menu-props="{ style: { minWidth: '320px' } }"
              :options="gapDomainOptions"
              @update:value="onGapDomain"
            />
          </div>
        </div>
        <div class="panel-bd">
          <div v-if="!gaps.length" class="empty-hint">
            <div class="empty-title">{{ gapsScanned ? '没有待补项' : '还没检查过' }}</div>
            <div class="empty-desc">
              {{
                gapsScanned
                  ? '该域已有 default 演示剧本。'
                  : '选一个域，点顶栏「检查待补」。'
              }}
            </div>
          </div>
          <template v-else>
            <div class="asset-desk-table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>域</th>
                    <th>说明</th>
                    <th style="width:88px"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(g, i) in pagedGaps" :key="`${g.domain_id}-${i}`">
                    <td>{{ domainLabel(g.domain_id) }}</td>
                    <td>{{ g.reason || '—' }}</td>
                    <td>
                      <n-button size="small" quaternary @click="fillFromGap(g)">补步骤</n-button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </template>
        </div>
      </div>
    </template>

    <n-drawer v-model:show="drawerOpen" :width="420" placement="right" @after-leave="onDrawerLeave">
      <n-drawer-content :title="editingId ? '改步骤' : '登记步骤'" closable>
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
          <n-form-item label="皮" :show-feedback="false">
            <n-select
              v-model:value="form.skin_id"
              size="small"
              filterable
              clearable
              :disabled="identityLocked"
              placeholder="默认（空）"
              :options="skinFormOptions"
            />
          </n-form-item>
          <n-form-item label="剧本" :show-feedback="false">
            <n-select
              v-model:value="form.script_id"
              size="small"
              filterable
              :disabled="identityLocked"
              :options="scriptFormOptions"
            />
          </n-form-item>
          <n-form-item label="步号" :show-feedback="false">
            <n-input-number
              v-model:value="form.step_no"
              size="small"
              :min="1"
              :disabled="identityLocked"
              style="width:100%"
            />
          </n-form-item>
          <n-form-item label="操作角色" :show-feedback="false">
            <n-select
              v-model:value="form.role"
              size="small"
              :options="roleOptions"
            />
          </n-form-item>
          <n-form-item label="步骤标题" :show-feedback="false">
            <n-input
              v-model:value="form.title_zh"
              size="small"
              :maxlength="128"
              show-count
              placeholder="浏览并下单"
            />
          </n-form-item>
          <n-form-item label="业务对象" :show-feedback="false">
            <n-select
              v-model:value="form.need_object"
              size="small"
              :options="needObjectOptions"
              placeholder="请选择"
            />
          </n-form-item>
          <n-form-item label="最少条数" :show-feedback="false">
            <n-input-number
              v-model:value="form.need_min"
              size="small"
              :min="1"
              style="width:100%"
            />
          </n-form-item>
          <n-form-item label="状态范围" :show-feedback="false">
            <n-select
              v-model:value="form.need_statuses"
              size="small"
              multiple
              filterable
              tag
              clearable
              placeholder="可选，默认不限"
              :options="needStatusOptions"
            />
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
import { api, message, toastApiError } from '../api'
import { gapStatDisplay } from '../utils/assetDesk'
import { confirm } from '../ui'
import PageSkeleton from '../components/PageSkeleton.vue'
import AssetDeskActions from '../components/AssetDeskActions.vue'

const booted = ref(false)
const loading = ref(false)
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
const scriptId = ref(null)
const q = ref('')

const gaps = ref([])
const gapCount = ref(0)
const gapsScanned = ref(false)
const gapDomain = ref(null)
const gapPage = ref(1)
const gapPageSize = ref(20)

const meta = reactive({
  domains: [],
  scripts: ['default'],
  skins: [],
})

const form = reactive({
  domain_id: '',
  skin_id: null,
  script_id: 'default',
  step_no: 1,
  role: 'user',
  title_zh: '',
  need_object: 'ticket',
  need_min: 1,
  need_statuses: [],
})

const roleOptions = [
  { label: '用户端', value: 'user' },
  { label: '受理端', value: 'staff' },
  { label: '管理端', value: 'admin' },
]

const skinFormOptions = computed(() => {
  const set = new Set(meta.skins || [])
  if (form.skin_id) set.add(form.skin_id)
  return [...set].map((s) => ({ label: s, value: s }))
})

const scriptFormOptions = computed(() => {
  const set = new Set(meta.scripts.length ? meta.scripts : ['default'])
  if (form.script_id) set.add(form.script_id)
  return [...set].map((s) => ({ label: s, value: s }))
})

const needObjectOptions = [
  { label: '单据', value: 'ticket' },
  { label: '订单', value: 'biz_order' },
  { label: '预约', value: 'reservation' },
  { label: '档案', value: 'archive' },
  { label: '公告', value: 'sys_notice' },
  { label: '用户', value: 'sys_user' },
]

const NEED_OBJECT_LABEL = Object.fromEntries(needObjectOptions.map((o) => [o.value, o.label]))

const needStatusOptions = [
  { label: '待处理', value: 'pending' },
  { label: '已确认', value: 'confirmed' },
  { label: '已通过', value: 'approved' },
  { label: '已发货', value: 'shipped' },
  { label: '已完成', value: 'completed' },
  { label: '已取消', value: 'cancelled' },
]

const identityLocked = computed(() => !!editingId.value || fromGap.value)

const formHint = computed(() => {
  if (identityLocked.value) {
    return editingId.value
      ? '标识字段已锁定，可修改角色、标题与所需数据。更换步骤请删除后重新登记。'
      : '待补项标识已锁定，请补全标题与所需数据后保存。'
  }
  return '业务对象与最少条数构成该步的数据底线；状态范围用于收窄可用记录，默认可留空。'
})

function roleLabel(role) {
  const hit = roleOptions.find((o) => o.value === role)
  return hit ? hit.label : role || '—'
}

function needRowsSummary(need) {
  if (!need || typeof need !== 'object') return '—'
  const keys = Object.keys(need)
  if (!keys.length) return '—'
  const key = keys[0]
  const spec = need[key] || {}
  const min = Number(spec.min) || 1
  const label = NEED_OBJECT_LABEL[key] || key
  const st = Array.isArray(spec.status_in) && spec.status_in.length
    ? ` · ${spec.status_in.join(' / ')}`
    : ''
  return `${label} ≥ ${min}${st}`
}

function applyNeedRowsToForm(need) {
  const keys = need && typeof need === 'object' ? Object.keys(need) : []
  if (!keys.length) {
    form.need_object = 'ticket'
    form.need_min = 1
    form.need_statuses = []
    return
  }
  const key = keys[0]
  const spec = need[key] || {}
  form.need_object = key
  form.need_min = Number(spec.min) || 1
  form.need_statuses = Array.isArray(spec.status_in) ? [...spec.status_in] : []
}

function buildNeedRowsFromForm() {
  const key = (form.need_object || '').trim() || 'ticket'
  const min = Math.max(1, Number(form.need_min) || 1)
  const statuses = (form.need_statuses || []).map((s) => String(s).trim()).filter(Boolean)
  const spec = { min }
  if (statuses.length) spec.status_in = statuses
  return { [key]: spec }
}

const domainFilterOptions = computed(() =>
  meta.domains.map((d) => ({
    label: domainSelectLabel(d.id),
    value: d.id,
  })),
)

const gapDomainOptions = computed(() =>
  meta.domains.map((d) => ({ label: domainSelectLabel(d.id), value: d.id })),
)

const formDomainOptions = computed(() => domainFilterOptions.value)

const scriptFilterOptions = computed(() =>
  (meta.scripts || ['default']).map((s) => ({ label: s, value: s })),
)

const pagedItems = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return items.value.slice(start, start + pageSize.value)
})

const pagedGaps = computed(() => {
  const start = (gapPage.value - 1) * gapPageSize.value
  return gaps.value.slice(start, start + gapPageSize.value)
})

function domainLabel(dom) {
  if (!dom) return '—'
  const hit = meta.domains.find((d) => d.id === dom)
  return hit ? hit.name || dom : dom
}

function domainSelectLabel(dom) {
  return `${domainLabel(dom)}（${dom}）`
}


function onPageSize() {
  page.value = 1
}

function reloadFromTop() {
  page.value = 1
  load()
}

function onGapDomain() {
  gapsScanned.value = false
  gaps.value = []
  gapCount.value = 0
  gapPage.value = 1
}

function resetForm() {
  form.domain_id = meta.domains[0]?.id || ''
  form.skin_id = null
  form.script_id = 'default'
  form.step_no = 1
  form.role = 'user'
  form.title_zh = ''
  form.need_object = 'ticket'
  form.need_min = 1
  form.need_statuses = []
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
  form.domain_id = row.domain_id || ''
  form.skin_id = row.skin_id || null
  form.script_id = row.script_id || 'default'
  form.step_no = row.step_no || 1
  form.role = row.role || 'user'
  form.title_zh = row.title_zh || ''
  applyNeedRowsToForm(row.need_rows)
  drawerOpen.value = true
}

function fillFromGap(g) {
  editingId.value = 0
  fromGap.value = true
  form.domain_id = g.domain_id || gapDomain.value || ''
  form.skin_id = null
  form.script_id = g.script_id || 'default'
  form.step_no = 1
  form.role = 'user'
  form.title_zh = '提交单据'
  form.need_object = 'ticket'
  form.need_min = 1
  form.need_statuses = []
  drawerOpen.value = true
}

async function loadMeta() {
  try {
    const res = await api.demoScriptsMeta()
    meta.domains = res.domains || []
    meta.scripts = res.scripts || ['default']
    meta.skins = res.skins || []
  } catch (e) {
    toastApiError(e, '加载选项失败')
  }
}

async function load() {
  loading.value = true
  try {
    const params = {}
    if (domain.value) params.domain_id = domain.value
    if (scriptId.value) params.script_id = scriptId.value
    if (q.value) params.q = q.value
    const res = await api.demoScripts(params)
    items.value = res.items || []
    total.value = res.total ?? items.value.length
    const maxPage = Math.max(1, Math.ceil((total.value || 0) / pageSize.value) || 1)
    if (page.value > maxPage) page.value = maxPage
  } catch (e) {
    toastApiError(e, '加载失败')
  } finally {
    loading.value = false
    booted.value = true
  }
}

async function migrate() {
  migrating.value = true
  try {
    const res = await api.demoScriptsMigrate()
    domain.value = null
    scriptId.value = null
    q.value = ''
    page.value = 1
    const n = res.inserted ?? 0
    message.success(n > 0 ? `已追加 ${n} 条` : '没有缺项可追加')
    await loadMeta()
    await load()
    mainTab.value = 'entries'
  } catch (e) {
    toastApiError(e, '导入失败')
  } finally {
    migrating.value = false
  }
}

async function scanGaps() {
  if (!gapDomain.value) {
    message.warning('先选一个域再检查')
    return
  }
  gapLoading.value = true
  try {
    const res = await api.demoScriptsGaps(gapDomain.value)
    gaps.value = res.gaps || []
    gapCount.value = res.gap_count ?? gaps.value.length
    gapsScanned.value = true
    gapPage.value = 1
    mainTab.value = 'gaps'
    if (gapCount.value) {
      message.info(`待补 ${gapCount.value} 条`)
    } else {
      message.success('没有待补项')
    }
  } catch (e) {
    toastApiError(e, '检查失败')
  } finally {
    gapLoading.value = false
  }
}

async function save() {
  if (!form.domain_id || !form.title_zh?.trim() || !form.step_no) {
    message.warning('域、步号与标题都要填')
    return
  }
  if (!form.need_object) {
    message.warning('请选择业务对象')
    return
  }
  const needRows = buildNeedRowsFromForm()
  saving.value = true
  try {
    await api.demoScriptsUpsert({
      domain_id: form.domain_id,
      skin_id: (form.skin_id || '').trim(),
      script_id: (form.script_id || 'default').trim(),
      step_no: form.step_no,
      role: form.role || 'user',
      title_zh: form.title_zh.trim(),
      need_rows: needRows,
      seed_fragment_id: '',
      source: 'manual',
    })
    message.success(editingId.value ? '已保存修改' : '已保存')
    drawerOpen.value = false
    resetForm()
    await loadMeta()
    await load()
    if (gapsScanned.value && gapDomain.value) {
      const gapRes = await api.demoScriptsGaps(gapDomain.value)
      gaps.value = gapRes.gaps || []
      gapCount.value = gapRes.gap_count ?? gaps.value.length
    }
  } catch (e) {
    toastApiError(e, '保存失败')
  } finally {
    saving.value = false
  }
}

async function remove(row) {
  if (!row?.id) return
  const ok = await confirm(`删除「${row.domain_id} #${row.step_no} ${row.title_zh}」？`, {
    title: '删除步骤',
    positiveText: '删除',
  })
  if (!ok) return
  deletingId.value = row.id
  try {
    await api.demoScriptsDelete(row.id)
    message.success('已删除')
    if (editingId.value === row.id) closeDrawer()
    await load()
  } catch (e) {
    toastApiError(e, '删除失败')
  } finally {
    deletingId.value = 0
  }
}

onMounted(async () => {
  await loadMeta()
  await load()
})
</script>

