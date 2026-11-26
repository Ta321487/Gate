<template>
  <div class="page-fill surface-page">
    <div class="surface-toolbar">
      <div>
        <h1 class="page-title">字典台</h1>
        <p class="page-desc" style="margin-bottom:0">
          维护业务枚举与展示名；出包后下拉与筛选项统一读取本台。
        </p>
      </div>
      <AssetDeskActions
        :gap-loading="gapLoading"
        :migrating="migrating"
        :check-disabled="!gapDomain"
        migrate-label="导入初始字典"
        create-label="登记枚举"
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
          <div class="label">枚举</div>
          <div class="value">{{ total }}</div>
        </div>
        <div class="stat">
          <div class="label">待补</div>
          <div class="value" :class="{ bad: gapsScanned && gapCount > 0 }">{{ gapStatDisplay(gapsScanned, gapCount) }}</div>
        </div>
      </div>

      <n-tabs v-model:value="mainTab" type="line" size="small" class="mb-12">
        <n-tab-pane name="entries" tab="枚举" />
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
              v-model:value="dictKey"
              size="small"
              clearable
              filterable
              placeholder="全部键"
              style="width:180px"
              :options="dictKeyFilterOptions"
              @update:value="reloadFromTop"
            />
            <n-input
              v-model:value="q"
              size="small"
              clearable
              placeholder="码 / 中文"
              style="width:160px"
              @keyup.enter="reloadFromTop"
            />
            <n-button size="small" @click="reloadFromTop">查询</n-button>
          </div>
        </div>
        <div class="panel-bd">
          <div v-if="!items.length" class="empty-hint">
            <div class="empty-title">还没有枚举</div>
            <div class="empty-desc">用顶栏导入或登记一条。</div>
          </div>
          <template v-else>
            <div class="asset-desk-table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>域</th>
                    <th>皮</th>
                    <th>键</th>
                    <th>码</th>
                    <th>中文</th>
                    <th>序</th>
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
                    <td class="mono">{{ row.dict_key }}</td>
                    <td class="mono">{{ row.value_code }}</td>
                    <td>{{ row.label_zh }}</td>
                    <td class="muted">{{ row.sort }}</td>
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
                    ? '68 域具名字典已齐（无期望字典的域不记缺口）。'
                    : '该域期望的枚举码已在台账中。'
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
                    <th>键</th>
                    <th>码</th>
                    <th style="width:88px"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="(g, i) in pagedGaps"
                    :key="`${g.domain_id || ''}-${g.dict_key}-${g.value_code}-${i}`"
                  >
                    <td v-if="lastScanDomains">{{ domainLabel(g.domain_id) }}</td>
                    <td class="mono">{{ g.dict_key }}</td>
                    <td class="mono">{{ g.value_code }}</td>
                    <td>
                      <n-button size="small" quaternary @click="fillFromGap(g)">补枚举</n-button>
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
      <n-drawer-content :title="editingId ? '改枚举' : '登记枚举'" closable>
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
          <n-form-item label="字典键" :show-feedback="false">
            <n-select
              v-model:value="form.dict_key"
              size="small"
              tag
              filterable
              :disabled="identityLocked"
              :options="dictKeyFormOptions"
            />
          </n-form-item>
          <n-form-item label="值码" :show-feedback="false">
            <n-input
              v-model:value="form.value_code"
              size="small"
              :disabled="identityLocked"
              placeholder="值码"
            />
          </n-form-item>
          <n-form-item label="中文" :show-feedback="false">
            <n-input
              v-model:value="form.label_zh"
              size="small"
              :maxlength="64"
              show-count
              placeholder="下拉显示名"
            />
          </n-form-item>
          <n-form-item label="排序" :show-feedback="false">
            <n-input-number v-model:value="form.sort" size="small" :min="0" style="width:100%" />
          </n-form-item>
          <n-form-item label="启用" :show-feedback="false">
            <n-switch v-model:value="form.enabled" />
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
const dictKey = ref(null)
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
  dict_keys: [],
  skins: [],
})

const form = reactive({
  domain_id: '*',
  skin_id: null,
  dict_key: 'ticket_priority',
  value_code: '',
  label_zh: '',
  sort: 0,
  enabled: true,
})

const identityLocked = computed(() => !!editingId.value || fromGap.value)

const formHint = computed(() => {
  if (identityLocked.value) {
    return editingId.value
      ? '标识字段已锁定，可修改展示名、排序与启用状态。更换键请删除后重新登记。'
      : '待补项标识已锁定，请补全展示名后保存。'
  }
  return '同一字典键下的多条值码构成下拉选项；皮用于软皮差异，默认可留空。'
})

const domainFilterOptions = computed(() =>
  meta.domains.map((d) => ({
    label: domainSelectLabel(d.id),
    value: d.id,
  })),
)

const gapDomainOptions = computed(() =>
  meta.domains
    .filter((d) => d.id && d.id !== '*')
    .map((d) => ({ label: domainSelectLabel(d.id), value: d.id })),
)

const formDomainOptions = computed(() => domainFilterOptions.value)

const dictKeyFilterOptions = computed(() =>
  meta.dict_keys.map((k) => ({ label: k, value: k })),
)

const dictKeyFormOptions = computed(() =>
  meta.dict_keys.map((k) => ({ label: k, value: k })),
)

const skinFormOptions = computed(() => {
  const set = new Set(meta.skins || [])
  if (form.skin_id) set.add(form.skin_id)
  return [...set].map((s) => ({ label: s, value: s }))
})

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
  form.skin_id = null
  form.dict_key = 'ticket_priority'
  form.value_code = ''
  form.label_zh = ''
  form.sort = 0
  form.enabled = true
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
  form.skin_id = row.skin_id || null
  form.dict_key = row.dict_key || ''
  form.value_code = row.value_code || ''
  form.label_zh = row.label_zh || ''
  form.sort = row.sort ?? 0
  form.enabled = row.enabled !== false
  drawerOpen.value = true
}

function fillFromGap(g) {
  editingId.value = 0
  fromGap.value = true
  form.domain_id = g.domain_id || gapDomain.value || '*'
  form.skin_id = g.skin_id || null
  form.dict_key = g.dict_key || ''
  form.value_code = g.value_code || ''
  form.label_zh = g.value_code || ''
  form.sort = 0
  form.enabled = true
  drawerOpen.value = true
}

async function loadMeta() {
  try {
    const res = await api.dictValuesMeta()
    meta.domains = res.domains || []
    meta.dict_keys = res.dict_keys || []
    meta.skins = res.skins || []
  } catch (e) {
    message.error(e?.message || '加载选项失败')
  }
}

async function load() {
  loading.value = true
  try {
    const params = {}
    if (domain.value !== null && domain.value !== undefined) params.domain_id = domain.value
    if (dictKey.value) params.dict_key = dictKey.value
    if (q.value) params.q = q.value
    const res = await api.dictValues(params)
    items.value = res.items || []
    total.value = res.total ?? items.value.length
    const maxPage = Math.max(1, Math.ceil((total.value || 0) / pageSize.value) || 1)
    if (page.value > maxPage) page.value = maxPage
  } catch (e) {
    message.error(e?.message || '加载失败')
  } finally {
    loading.value = false
    booted.value = true
  }
}

async function migrate() {
  migrating.value = true
  try {
    const res = await api.dictValuesMigrate()
    domain.value = null
    dictKey.value = null
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

async function scanGaps(scanDomains = false) {
  if (!scanDomains && !gapDomain.value) {
    message.warning('先选一个域再检查，或点「扫 68 域」')
    return
  }
  gapLoading.value = true
  lastScanDomains.value = !!scanDomains
  try {
    const res = scanDomains
      ? await api.dictValuesGaps({ scan_domains: true })
      : await api.dictValuesGaps({ domain_id: gapDomain.value })
    gaps.value = res.gaps || []
    gapCount.value = res.gap_count ?? gaps.value.length
    gapsScanned.value = true
    gapPage.value = 1
    mainTab.value = 'gaps'
    if (gapCount.value) message.info(`待补 ${gapCount.value} 条`)
    else message.success(scanDomains ? '68 域具名字典已齐' : '没有待补项')
  } catch (e) {
    message.error(e?.message || '检查失败')
  } finally {
    gapLoading.value = false
  }
}

async function save() {
  if (!form.dict_key?.trim() || !form.value_code?.trim() || !form.label_zh?.trim()) {
    message.warning('字典键、值码与中文都要填')
    return
  }
  saving.value = true
  try {
    await api.dictValuesUpsert({
      domain_id: form.domain_id || '*',
      skin_id: (form.skin_id || '').trim(),
      dict_key: form.dict_key.trim(),
      value_code: form.value_code.trim(),
      label_zh: form.label_zh.trim(),
      sort: form.sort ?? 0,
      enabled: form.enabled !== false,
      source: 'manual',
    })
    message.success(editingId.value ? '已保存修改' : '已保存')
    drawerOpen.value = false
    resetForm()
    await loadMeta()
    await load()
    if (gapsScanned.value) {
      const gapRes = lastScanDomains.value
        ? await api.dictValuesGaps({ scan_domains: true })
        : gapDomain.value
          ? await api.dictValuesGaps({ domain_id: gapDomain.value })
          : null
      if (gapRes) {
        gaps.value = gapRes.gaps || []
        gapCount.value = gapRes.gap_count ?? gaps.value.length
      }
    }
  } catch (e) {
    message.error(e?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function remove(row) {
  if (!row?.id) return
  const ok = await confirm(`删除「${row.dict_key}/${row.value_code} → ${row.label_zh}」？`, {
    title: '删除枚举',
    positiveText: '删除',
  })
  if (!ok) return
  deletingId.value = row.id
  try {
    await api.dictValuesDelete(row.id)
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

