<template>
  <div class="page-fill surface-page">
    <div class="surface-toolbar">
      <div>
        <h1 class="page-title">状态话术</h1>
        <p class="page-desc" style="margin-bottom:0">
          维护状态码的列表名、主操作与空态文案；跨域默认可被具名域覆盖，出包写入状态文案。
        </p>
      </div>
      <AssetDeskActions
        :gap-loading="gapLoading"
        :migrating="migrating"
        :check-disabled="!gapDomain"
        migrate-label="导入初始话术"
        create-label="登记话术"
        @check="scanGaps(false)"
        @migrate="migrate"
        @create="openCreate"
      >
        <template #extra>
          <n-button size="small" :loading="gapLoading" @click="scanGaps(true)">扫 68 域</n-button>
        </template>
      </AssetDeskActions>
    </div>

    <PageSkeleton v-if="!booted" variant="dashboard" :rows="4" />
    <template v-else>
      <div class="stats mb-12" style="grid-template-columns:repeat(2,1fr);max-width:360px">
        <div class="stat">
          <div class="label">话术</div>
          <div class="value">{{ total }}</div>
        </div>
        <div class="stat">
          <div class="label">待补</div>
          <div class="value" :class="{ bad: gapsScanned && gapCount > 0 }">{{ gapStatDisplay(gapsScanned, gapCount) }}</div>
        </div>
      </div>

      <n-tabs v-model:value="mainTab" type="line" size="small" class="mb-12">
        <n-tab-pane name="entries" tab="话术" />
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
              v-model:value="machine"
              size="small"
              clearable
              placeholder="全部机"
              style="width:140px"
              :options="machineFilterOptions"
              @update:value="reloadFromTop"
            />
            <n-input
              v-model:value="q"
              size="small"
              clearable
              placeholder="状态码 / 中文"
              style="width:180px"
              @keyup.enter="reloadFromTop"
            />
            <n-button size="small" @click="reloadFromTop">查询</n-button>
          </div>
        </div>
        <div class="panel-bd">
          <div v-if="!items.length" class="empty-hint">
            <div class="empty-title">还没有话术</div>
            <div class="empty-desc">用顶栏导入或登记一条。</div>
          </div>
          <template v-else>
            <div class="asset-desk-table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>域</th>
                    <th>机</th>
                    <th>状态码</th>
                    <th>列表名</th>
                    <th>主按钮</th>
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
                    <td class="mono">{{ row.machine_id }}</td>
                    <td class="mono">{{ row.status_code }}</td>
                    <td>{{ row.label_zh }}</td>
                    <td class="muted">{{ row.action_zh || '—' }}</td>
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
                  ? lastScanDomains
                    ? '68 域具名话术已齐（无状态机的域不记缺口）。'
                    : '该域基线实体状态已在台账中。'
                  : '选一个域点「检查待补」，或点「扫 68 域」。'
              }}
            </div>
          </div>
          <template v-else>
            <div class="asset-desk-table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th v-if="lastScanDomains">域</th>
                    <th>机</th>
                    <th>状态码</th>
                    <th>基线现名</th>
                    <th style="width:88px"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="(g, i) in pagedGaps"
                    :key="`${g.domain_id || ''}-${g.machine_id}-${g.status_code}-${i}`"
                  >
                    <td v-if="lastScanDomains">{{ domainLabel(g.domain_id) }}</td>
                    <td class="mono">{{ g.machine_id }}</td>
                    <td class="mono">{{ g.status_code }}</td>
                    <td>{{ g.schema_label || '—' }}</td>
                    <td>
                      <n-button size="small" quaternary @click="fillFromGap(g)">补话术</n-button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-if="filteredGaps.length > 0" class="pager-row">
              <span class="small muted">共 {{ filteredGaps.length }} 条</span>
              <n-pagination
                v-model:page="gapPage"
                v-model:page-size="gapPageSize"
                :item-count="filteredGaps.length"
                :page-sizes="[10, 20, 50]"
                show-size-picker
                size="small"
                @update:page-size="gapPage = 1"
              />
            </div>
          </template>
        </div>
      </div>
    </template>

    <n-drawer v-model:show="drawerOpen" :width="400" placement="right" @after-leave="onDrawerLeave">
      <n-drawer-content :title="editingId ? '改话术' : '登记话术'" closable>
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
          <n-form-item label="状态机" :show-feedback="false">
            <n-select
              v-model:value="form.machine_id"
              size="small"
              tag
              filterable
              :disabled="identityLocked"
              :options="machineFormOptions"
            />
          </n-form-item>
          <n-form-item label="状态码" :show-feedback="false">
            <n-input
              v-model:value="form.status_code"
              size="small"
              :disabled="identityLocked"
              placeholder="如 pending"
            />
          </n-form-item>
          <n-form-item label="列表名" :show-feedback="false">
            <n-input
              v-model:value="form.label_zh"
              size="small"
              :maxlength="64"
              show-count
              placeholder="列表展示名"
            />
          </n-form-item>
          <n-form-item label="主按钮" :show-feedback="false">
            <n-input
              v-model:value="form.action_zh"
              size="small"
              :maxlength="64"
              show-count
              placeholder="可空"
            />
          </n-form-item>
          <n-form-item label="空态句" :show-feedback="false">
            <n-input
              v-model:value="form.empty_zh"
              size="small"
              type="textarea"
              :maxlength="128"
              show-count
              placeholder="可选"
            />
          </n-form-item>
          <n-form-item label="角色" :show-feedback="false">
            <n-select
              v-model:value="form.for_roles"
              size="small"
              multiple
              :options="roleOptions"
              placeholder="适用角色"
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
const machine = ref(null)
const q = ref('')

const gaps = ref([])
const gapCount = ref(0)
const gapsScanned = ref(false)
const gapDomain = ref(null)
const lastScanDomains = ref(false)
const gapPage = ref(1)
const gapPageSize = ref(20)

const meta = reactive({
  domains: [],
  machines: [],
  machine_options: [],
  roles: ['admin', 'staff', 'user'],
})

const ROLE_LABEL = {
  admin: '管理端',
  staff: '受理端',
  user: '用户端',
}

const form = reactive({
  domain_id: '*',
  machine_id: 'order',
  status_code: '',
  label_zh: '',
  action_zh: '',
  empty_zh: '',
  for_roles: ['admin', 'staff', 'user'],
})

const identityLocked = computed(() => !!editingId.value || fromGap.value)

const formHint = computed(() => {
  if (identityLocked.value) {
    return editingId.value
      ? '标识字段已锁定，可修改文案与适用角色。更换键请删除后重新登记。'
      : '待补项标识已锁定，请补全文案后保存。'
  }
  return '「跨域壳默认」适用于多数域；具名域优先生效。状态机对应业务对象，状态码对应具体节点。'
})

const domainFilterOptions = computed(() => [
  ...meta.domains.map((d) => ({
    label: domainSelectLabel(d.id),
    value: d.id,
  })),
])

const gapDomainOptions = computed(() =>
  meta.domains
    .filter((d) => d.id && d.id !== '*')
    .map((d) => ({ label: domainSelectLabel(d.id), value: d.id })),
)

const formDomainOptions = computed(() => domainFilterOptions.value)

const machineFilterOptions = computed(() => {
  if (meta.machine_options.length) return meta.machine_options
  return meta.machines.map((m) => ({ label: m, value: m }))
})

const machineFormOptions = computed(() => machineFilterOptions.value)

const roleOptions = computed(() =>
  (meta.roles.length ? meta.roles : ['admin', 'staff', 'user']).map((r) => ({
    label: ROLE_LABEL[r] || r,
    value: r,
  })),
)

function parseRoles(raw) {
  if (Array.isArray(raw)) return raw.filter(Boolean)
  return String(raw || '')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)
}

const pagedItems = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return items.value.slice(start, start + pageSize.value)
})

const filteredGaps = computed(() => gaps.value)

const pagedGaps = computed(() => {
  const start = (gapPage.value - 1) * gapPageSize.value
  return filteredGaps.value.slice(start, start + gapPageSize.value)
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


function onPageSize() {
  page.value = 1
}

function reloadFromTop() {
  page.value = 1
  load()
}

function onGapDomain() {
  gapsScanned.value = false
  lastScanDomains.value = false
  gaps.value = []
  gapCount.value = 0
  gapPage.value = 1
}

function resetForm() {
  form.domain_id = '*'
  form.machine_id = 'order'
  form.status_code = ''
  form.label_zh = ''
  form.action_zh = ''
  form.empty_zh = ''
  form.for_roles = ['admin', 'staff', 'user']
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
  form.machine_id = row.machine_id || 'order'
  form.status_code = row.status_code || ''
  form.label_zh = row.label_zh || ''
  form.action_zh = row.action_zh || ''
  form.empty_zh = row.empty_zh || ''
  form.for_roles = parseRoles(row.for_roles || 'admin,staff,user')
  drawerOpen.value = true
}

function fillFromGap(g) {
  editingId.value = 0
  fromGap.value = true
  form.domain_id = g.domain_id || gapDomain.value || '*'
  form.machine_id = g.machine_id || 'order'
  form.status_code = g.status_code || ''
  form.label_zh = g.schema_label || ''
  form.action_zh = ''
  form.empty_zh = ''
  form.for_roles = ['admin', 'staff', 'user']
  drawerOpen.value = true
}

async function loadMeta() {
  try {
    const res = await api.statusCopyMeta()
    meta.domains = res.domains || []
    meta.machines = res.machines || []
    meta.machine_options = res.machine_options || []
    meta.roles = res.roles || ['admin', 'staff', 'user']
  } catch (e) {
    toastApiError(e, '加载选项失败')
  }
}

async function load() {
  loading.value = true
  try {
    const params = {}
    if (domain.value !== null && domain.value !== undefined) params.domain_id = domain.value
    if (machine.value) params.machine_id = machine.value
    if (q.value) params.q = q.value
    const res = await api.statusCopy(params)
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
    const res = await api.statusCopyMigrate()
    domain.value = null
    machine.value = null
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

async function scanGaps(scanDomains = false) {
  if (!scanDomains && !gapDomain.value) {
    message.warning('先选一个域再检查，或点「扫 68 域」')
    return
  }
  gapLoading.value = true
  lastScanDomains.value = !!scanDomains
  try {
    const res = scanDomains
      ? await api.statusCopyGaps({ scan_domains: true })
      : await api.statusCopyGaps({ domain_id: gapDomain.value })
    gaps.value = res.gaps || []
    gapCount.value = res.gap_count ?? gaps.value.length
    gapsScanned.value = true
    gapPage.value = 1
    mainTab.value = 'gaps'
    if (gapCount.value) message.info(`待补 ${gapCount.value} 条`)
    else message.success(scanDomains ? '68 域具名话术已齐' : '没有待补项')
  } catch (e) {
    toastApiError(e, '检查失败')
  } finally {
    gapLoading.value = false
  }
}

async function save() {
  if (!form.machine_id?.trim() || !form.status_code?.trim() || !form.label_zh?.trim()) {
    message.warning('状态机、状态码与列表名都要填')
    return
  }
  saving.value = true
  try {
    await api.statusCopyUpsert({
      domain_id: form.domain_id || '*',
      machine_id: form.machine_id.trim(),
      status_code: form.status_code.trim(),
      label_zh: form.label_zh.trim(),
      action_zh: (form.action_zh || '').trim(),
      empty_zh: (form.empty_zh || '').trim(),
      for_roles: (form.for_roles?.length ? form.for_roles : ['admin', 'staff', 'user']).join(','),
      source: 'manual',
    })
    message.success(editingId.value ? '已保存修改' : '已保存')
    drawerOpen.value = false
    resetForm()
    await loadMeta()
    await load()
    if (gapsScanned.value) {
      const gapRes = lastScanDomains.value
        ? await api.statusCopyGaps({ scan_domains: true })
        : gapDomain.value
          ? await api.statusCopyGaps({ domain_id: gapDomain.value })
          : null
      if (gapRes) {
        gaps.value = gapRes.gaps || []
        gapCount.value = gapRes.gap_count ?? gaps.value.length
      }
    }
  } catch (e) {
    toastApiError(e, '保存失败')
  } finally {
    saving.value = false
  }
}

async function remove(row) {
  if (!row?.id) return
  const ok = await confirm(`删除「${row.machine_id}/${row.status_code} → ${row.label_zh}」？`, {
    title: '删除话术',
    positiveText: '删除',
  })
  if (!ok) return
  deletingId.value = row.id
  try {
    await api.statusCopyDelete(row.id)
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

