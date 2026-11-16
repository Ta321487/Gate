<template>
  <div class="page-fill surface-page">
    <div class="surface-toolbar">
      <div>
        <h1 class="page-title">词表维护</h1>
        <p class="page-desc" style="margin-bottom:0">
          给库列起中文名，出包后写进 schema.sql 的注释。列名保持英文。
        </p>
      </div>
      <div class="row" style="gap:8px;flex-wrap:wrap">
        <n-button size="small" :loading="gapLoading" @click="scanGaps">检查待补</n-button>
        <n-button size="small" :loading="migrating" @click="migrate">导入初始词表</n-button>
        <n-button size="small" type="primary" @click="openCreate">登记词条</n-button>
      </div>
    </div>

    <PageSkeleton v-if="!booted" variant="dashboard" :rows="4" />
    <template v-else>
      <div class="stats mb-12" style="grid-template-columns:repeat(2,1fr);max-width:360px">
        <div class="stat">
          <div class="label">词条</div>
          <div class="value">{{ total }}</div>
        </div>
        <div class="stat">
          <div class="label">待补</div>
          <div class="value" :class="{ bad: gapCount > 0 }">{{ gapCount }}</div>
        </div>
      </div>

      <n-tabs v-model:value="mainTab" type="line" size="small" class="mb-12" @update:value="onTab">
        <n-tab-pane name="entries" tab="词条" />
        <n-tab-pane name="gaps" tab="待补" />
      </n-tabs>

      <!-- 词条 -->
      <div v-show="mainTab === 'entries'" class="panel panel-quiet">
        <div class="panel-hd">
          <div class="row zl-filter-row">
            <n-select
              v-model:value="kind"
              size="small"
              style="width:130px"
              :options="kindOptions"
              @update:value="reloadFromTop"
            />
            <n-select
              v-model:value="domain"
              size="small"
              clearable
              filterable
              placeholder="全部域"
              style="width:220px"
              :consistent-menu-width="false"
              :menu-props="{ style: { minWidth: '320px' } }"
              :options="filterDomainOptions"
              @update:value="onFilterDomain"
            />
            <n-select
              v-model:value="skin"
              size="small"
              clearable
              filterable
              placeholder="全部皮"
              style="width:150px"
              :consistent-menu-width="false"
              :menu-props="{ style: { minWidth: '200px' } }"
              :options="filterSkinOptions"
              @update:value="reloadFromTop"
            />
            <n-input
              v-model:value="q"
              size="small"
              clearable
              placeholder="搜英文键 / 中文"
              style="width:180px"
              @keyup.enter="reloadFromTop"
            />
          </div>
          <n-button size="small" :loading="loading" @click="reloadFromTop">刷新</n-button>
        </div>
        <div class="panel-bd">
          <div v-if="!items.length" class="empty-hint">
            <div class="empty-title">还没有词条</div>
            <div class="empty-desc">先导入初始词表，或直接登记一条。</div>
            <div class="row" style="gap:8px;justify-content:center;flex-wrap:wrap;margin-top:10px">
              <n-button size="small" type="primary" :loading="migrating" @click="migrate">导入初始词表</n-button>
              <n-button size="small" @click="openCreate">登记词条</n-button>
            </div>
          </div>
          <template v-else>
            <div class="zl-table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>类型</th>
                    <th>英文键</th>
                    <th>中文</th>
                    <th>域</th>
                    <th>皮</th>
                    <th>表</th>
                    <th style="width:120px"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="row in pagedItems"
                    :key="row.id"
                    :class="{ 'is-editing': editingId === row.id && drawerOpen }"
                  >
                    <td>{{ kindLabel(row.kind) }}</td>
                    <td class="mono">{{ row.key_name }}</td>
                    <td>{{ row.zh }}</td>
                    <td>{{ domainLabel(row.domain) }}</td>
                    <td class="mono muted">{{ row.skin || '—' }}</td>
                    <td class="mono muted">{{ row.table_name || '—' }}</td>
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
            <div v-if="total > 0" class="pager-row">
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

      <!-- 待补：条数只在底部分页；检查只走顶栏「检查待补」 -->
      <div v-show="mainTab === 'gaps'" class="panel panel-quiet">
        <div class="panel-hd">
          <div class="row zl-filter-row" style="align-items:center">
            <n-select
              v-model:value="gapDomain"
              size="small"
              clearable
              filterable
              placeholder="全部域"
              style="width:220px"
              :consistent-menu-width="false"
              :menu-props="{ style: { minWidth: '320px' } }"
              :options="gapDomainOptions"
              @update:value="gapPage = 1"
            />
          </div>
        </div>
        <div class="panel-bd">
          <div v-if="!gaps.length" class="empty-hint">
            <div class="empty-title">{{ gapsScanned ? '没有待补项' : '还没检查过' }}</div>
            <div class="empty-desc">
              {{
                gapsScanned
                  ? '当前词表已覆盖扫到的列；有新域模板后再检查一次。'
                  : '点顶栏「检查待补」，对照各域建表 SQL 找出缺中文的列。'
              }}
            </div>
          </div>
          <template v-else>
            <div class="zl-table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>列名</th>
                    <th>域</th>
                    <th>表</th>
                    <th>皮</th>
                    <th style="width:88px"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(g, i) in pagedGaps" :key="`${g.domain}-${g.table_name}-${g.key_name}-${i}`">
                    <td class="mono">{{ g.key_name }}</td>
                    <td>{{ domainLabel(g.domain) }}</td>
                    <td class="mono">{{ g.table_name || '—' }}</td>
                    <td class="mono muted">{{ g.skin || '—' }}</td>
                    <td>
                      <n-button size="small" quaternary @click="fillFromGap(g)">补中文</n-button>
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
      <n-drawer-content :title="editingId ? '改词条' : '登记词条'" closable>
        <div class="zl-drawer-form">
          <n-form-item label="类型" :show-feedback="false">
            <n-select
              v-model:value="form.kind"
              size="small"
              :disabled="identityLocked"
              :options="kindOptionsNoAll"
              @update:value="onFormKind"
            />
          </n-form-item>
          <n-form-item :label="formKeyLabel" :show-feedback="false">
            <n-input
              v-model:value="form.key_name"
              size="small"
              :disabled="identityLocked"
              :placeholder="formKeyPlaceholder"
            />
          </n-form-item>
          <n-form-item label="中文" :show-feedback="false">
            <n-input
              v-model:value="form.zh"
              size="small"
              :maxlength="ZH_MAX_LEN"
              show-count
              :placeholder="formZhPlaceholder"
            />
          </n-form-item>
          <p v-if="zhDupWarn" class="small zl-warn">{{ zhDupWarn }}</p>
          <template v-if="formShowDomainSkin">
            <n-form-item label="域" :show-feedback="false">
              <n-select
                v-model:value="form.domain"
                size="small"
                filterable
                :disabled="identityLocked"
                :consistent-menu-width="false"
                :menu-props="{ style: { minWidth: '320px' } }"
                :options="formDomainOptions"
                @update:value="onFormDomain"
              />
            </n-form-item>
            <n-form-item label="皮" :show-feedback="false">
              <n-select
                v-model:value="form.skin"
                size="small"
                filterable
                :disabled="identityLocked"
                :consistent-menu-width="false"
                :menu-props="{ style: { minWidth: '200px' } }"
                :options="formSkinOptions"
              />
            </n-form-item>
          </template>
          <n-form-item v-if="form.kind === 'column'" label="表（可选）" :show-feedback="false">
            <n-select
              v-model:value="form.table_name"
              size="small"
              filterable
              clearable
              :disabled="identityLocked"
              :consistent-menu-width="false"
              :menu-props="{ style: { minWidth: '220px' } }"
              :options="formTableOptions"
              placeholder="不限表"
            />
          </n-form-item>
          <p class="small muted">{{ formHint }}</p>
        </div>
        <template #footer>
          <div class="row" style="gap:8px;justify-content:flex-end">
            <n-button size="small" @click="closeDrawer">{{ editingId ? '退出编辑' : '取消' }}</n-button>
            <n-button type="primary" size="small" :loading="saving" @click="save">
              {{ editingId ? '保存修改' : '保存' }}
            </n-button>
          </div>
        </template>
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { api, message } from '../api'
import { confirm } from '../ui'
import PageSkeleton from '../components/PageSkeleton.vue'

const ZH_MAX_LEN = 64

const kindOptions = [
  { label: '全部类型', value: '' },
  { label: '列', value: 'column' },
  { label: '表', value: 'table' },
  { label: '词根', value: 'stem' },
  { label: '表名片断', value: 'table_part' },
]
const kindOptionsNoAll = kindOptions.filter((o) => o.value)

const mainTab = ref('entries')
const kind = ref('column')
const domain = ref(null)
const skin = ref(null)
const q = ref('')
const items = ref([])
/** 全量列词条（不受列表筛选项影响），供同表同中文弱警告 */
const columnCorpus = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const gaps = ref([])
const gapCount = ref(0)
const gapsScanned = ref(false)
const gapDomain = ref(null)
const gapPage = ref(1)
const gapPageSize = ref(20)
const booted = ref(false)
const loading = ref(false)
const migrating = ref(false)
const gapLoading = ref(false)
const saving = ref(false)
const deletingId = ref(0)
const editingId = ref(0)
const fromGap = ref(false)
const drawerOpen = ref(false)
const identityLocked = computed(() => !!editingId.value || fromGap.value)

const meta = reactive({
  domains: [],
  skins: [],
  skins_by_domain: {},
  tables_by_domain: {},
})

const form = reactive({
  kind: 'column',
  key_name: '',
  zh: '',
  domain: '',
  skin: '',
  table_name: '',
})

const pagedItems = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return items.value.slice(start, start + pageSize.value)
})

const filteredGaps = computed(() => {
  if (!gapDomain.value) return gaps.value
  return gaps.value.filter((g) => (g.domain || '') === gapDomain.value)
})

const pagedGaps = computed(() => {
  const start = (gapPage.value - 1) * gapPageSize.value
  return filteredGaps.value.slice(start, start + gapPageSize.value)
})

const gapDomainOptions = computed(() => {
  const ids = [...new Set(gaps.value.map((g) => g.domain || ''))]
  return ids
    .map((id) => ({
      label: domainSelectLabel(id),
      value: id,
    }))
    .sort((a, b) => String(a.label).localeCompare(String(b.label), 'zh'))
})

const formShowDomainSkin = computed(
  () => form.kind === 'column' || form.kind === 'table',
)

const formKeyLabel = computed(() => {
  if (form.kind === 'table') return '表名'
  if (form.kind === 'stem') return '词根'
  if (form.kind === 'table_part') return '片断'
  return '列名'
})

const formKeyPlaceholder = computed(() => {
  if (form.kind === 'table') return '英文表名，snake_case'
  if (form.kind === 'stem') return '英文词根'
  if (form.kind === 'table_part') return '英文片断'
  return '英文列名，snake_case'
})

const formZhPlaceholder = computed(() => {
  if (form.kind === 'table') return '表的中文名'
  if (form.kind === 'stem') return '词根中文'
  if (form.kind === 'table_part') return '片断中文'
  return '列的中文含义'
})

const formHint = computed(() => {
  if (identityLocked.value) {
    return editingId.value
      ? '类型与键、域、皮、表已锁定，只改中文。换键请删后重登。'
      : '待补项身份已锁定，只填中文后保存。'
  }
  if (form.kind === 'column') return '列可挂域/皮，也可选表收窄。同键再存即更新。中文最多 64 字。'
  if (form.kind === 'table') return '表中文名；可挂域/皮。中文最多 64 字。'
  if (form.kind === 'stem') return '全局词根，供组合建议；不挂域/皮。中文最多 64 字。'
  return '全局表名片断，供拆名组词；不挂域/皮。中文最多 64 字。'
})

const zhDupWarn = computed(() => {
  if (form.kind !== 'column') return ''
  const zh = (form.zh || '').trim()
  const table = (form.table_name || '').trim()
  const key = (form.key_name || '').trim()
  if (!zh || !table || !key) return ''
  const domain = form.domain || ''
  const twins = columnCorpus.value
    .filter(
      (r) =>
        (r.kind || 'column') === 'column' &&
        (r.table_name || '') === table &&
        (r.domain || '') === domain &&
        (r.zh || '').trim() === zh &&
        (r.key_name || '') !== key,
    )
    .map((r) => r.key_name)
  if (!twins.length) return ''
  const uniq = [...new Set(twins)].sort()
  const shown = uniq.slice(0, 5).join('、')
  const more = uniq.length > 5 ? ` 等${uniq.length}列` : ''
  return `同表已有列也叫「${zh}」（${shown}${more}），可保存，但答辩看 COMMENT 时可能分不清`
})

const globalDomainOpt = { label: '（全局）', value: '' }

const formDomainOptions = computed(() => [
  globalDomainOpt,
  ...meta.domains.map((d) => ({
    label: domainSelectLabel(d.id),
    value: d.id,
  })),
])

const filterDomainOptions = computed(() => [
  globalDomainOpt,
  ...meta.domains.map((d) => ({
    label: domainSelectLabel(d.id),
    value: d.id,
  })),
])

function skinsForDomain(dom) {
  const set = new Set()
  ;(meta.skins_by_domain?.[dom || ''] || []).forEach((s) => s && set.add(s))
  ;(meta.skins || []).forEach((s) => s && set.add(s))
  return [...set].sort()
}

const filterSkinOptions = computed(() => {
  const skins = domain.value
    ? skinsForDomain(domain.value)
    : [...new Set([...(meta.skins || []), ...Object.values(meta.skins_by_domain || {}).flat()])].sort()
  return [
    { label: '无皮特化', value: '' },
    ...skins.map((s) => ({ label: s, value: s })),
  ]
})

const formSkinOptions = computed(() => [
  { label: '无皮特化', value: '' },
  ...skinsForDomain(form.domain).map((s) => ({ label: s, value: s })),
])

const formTableOptions = computed(() => {
  const tables = new Set()
  ;(meta.tables_by_domain?.[form.domain || ''] || []).forEach((t) => t && tables.add(t))
  gaps.value.forEach((g) => {
    if ((g.domain || '') === (form.domain || '') && g.table_name) tables.add(g.table_name)
  })
  return [
    { label: '（不限表）', value: '' },
    ...[...tables].sort().map((t) => ({ label: t, value: t })),
  ]
})

function kindLabel(k) {
  return { column: '列', table: '表', stem: '词根', table_part: '表名片断' }[k] || k
}

function domainLabel(dom) {
  if (!dom) return '（全局）'
  const hit = meta.domains.find((d) => d.id === dom)
  return hit ? hit.name || dom : dom
}

/** 下拉统一：中文名（DOM-*）；空域为（全局） */
function domainSelectLabel(dom) {
  if (!dom) return '（全局）'
  return `${domainLabel(dom)}（${dom}）`
}

function onTab(tab) {
  if (tab === 'gaps' && !gapsScanned.value) scanGaps()
}

function onPageSize() {
  page.value = 1
}

function reloadFromTop() {
  page.value = 1
  load()
}

function onFilterDomain() {
  skin.value = null
  reloadFromTop()
}

function onFormKind() {
  if (form.kind !== 'column') form.table_name = ''
  if (form.kind === 'stem' || form.kind === 'table_part') {
    form.domain = ''
    form.skin = ''
  }
}

function onFormDomain() {
  const skins = new Set(skinsForDomain(form.domain))
  if (form.skin && !skins.has(form.skin)) form.skin = ''
  const tables = new Set(formTableOptions.value.map((o) => o.value))
  if (form.table_name && !tables.has(form.table_name)) form.table_name = ''
}

function resetForm() {
  form.kind = 'column'
  form.key_name = ''
  form.zh = ''
  form.domain = ''
  form.skin = ''
  form.table_name = ''
  editingId.value = 0
  fromGap.value = false
}

function openCreate() {
  resetForm()
  drawerOpen.value = true
}

function closeDrawer() {
  drawerOpen.value = false
}

function onDrawerLeave() {
  resetForm()
}

function editRow(row) {
  fromGap.value = false
  editingId.value = row.id || 0
  form.kind = row.kind
  form.key_name = row.key_name
  form.zh = row.zh
  form.domain = row.domain || ''
  form.skin = row.skin || ''
  form.table_name = row.table_name || ''
  drawerOpen.value = true
}

function fillFromGap(g) {
  editingId.value = 0
  fromGap.value = true
  form.kind = g.kind || 'column'
  form.key_name = g.key_name || ''
  form.zh = ''
  form.domain = g.domain || ''
  form.skin = g.skin || ''
  form.table_name = g.table_name || ''
  drawerOpen.value = true
}

async function loadMeta() {
  try {
    const res = await api.zhLexiconMeta()
    meta.domains = res.domains || []
    meta.skins = res.skins || []
    meta.skins_by_domain = res.skins_by_domain || {}
    meta.tables_by_domain = res.tables_by_domain || {}
  } catch (e) {
    message.error(e?.message || '加载域/皮选项失败')
  }
}

async function loadColumnCorpus() {
  try {
    const res = await api.zhLexicon({ kind: 'column' })
    columnCorpus.value = res.items || []
  } catch {
    /* 弱警告用；失败不挡主流程 */
  }
}

async function load() {
  loading.value = true
  try {
    const params = {}
    if (kind.value) params.kind = kind.value
    if (domain.value !== null && domain.value !== undefined) params.domain = domain.value
    if (skin.value !== null && skin.value !== undefined) params.skin = skin.value
    if (q.value) params.q = q.value
    const res = await api.zhLexicon(params)
    items.value = res.items || []
    total.value = res.total ?? items.value.length
    const maxPage = Math.max(1, Math.ceil((total.value || 0) / pageSize.value) || 1)
    if (page.value > maxPage) page.value = maxPage
  } catch (e) {
    message.error(e?.message || '加载词表失败')
  } finally {
    loading.value = false
    booted.value = true
  }
}

async function migrate() {
  migrating.value = true
  try {
    const res = await api.zhLexiconMigrate()
    message.success(`已导入 ${res.inserted ?? 0} 条，合计 ${res.total ?? 0}`)
    await loadMeta()
    await load()
    await loadColumnCorpus()
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
    const res = await api.zhLexiconGaps()
    gaps.value = res.gaps || []
    gapCount.value = res.gap_count ?? gaps.value.length
    gapsScanned.value = true
    gapPage.value = 1
    await loadMeta()
    if (gapCount.value) {
      mainTab.value = 'gaps'
      message.info(`待补 ${gapCount.value} 条`)
    } else {
      message.success('没有待补项')
    }
  } catch (e) {
    message.error(e?.message || '检查失败')
  } finally {
    gapLoading.value = false
  }
}

async function save() {
  if (!form.key_name?.trim() || !form.zh?.trim()) {
    message.warning(`${formKeyLabel.value}与中文都要填`)
    return
  }
  if (form.zh.trim().length > ZH_MAX_LEN) {
    message.warning(`中文最多 ${ZH_MAX_LEN} 字`)
    return
  }
  saving.value = true
  try {
    const scoped = formShowDomainSkin.value
    const res = await api.zhLexiconUpsert({
      kind: form.kind,
      key_name: form.key_name.trim(),
      zh: form.zh.trim(),
      domain: scoped ? form.domain || '' : '',
      skin: scoped ? form.skin || '' : '',
      table_name: form.kind === 'column' ? form.table_name || '' : '',
      source: 'manual',
    })
    const warns = res.warnings || []
    if (warns.length) {
      message.warning(warns[0])
    } else {
      message.success(editingId.value ? '已保存修改' : '已保存')
    }
    drawerOpen.value = false
    resetForm()
    await loadMeta()
    await load()
    await loadColumnCorpus()
    if (gapsScanned.value) {
      const gapRes = await api.zhLexiconGaps()
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
  const ok = await confirm(`删除词条「${row.key_name} → ${row.zh}」？`, {
    title: '删除词条',
    positiveText: '删除',
  })
  if (!ok) return
  deletingId.value = row.id
  try {
    await api.zhLexiconDelete(row.id)
    message.success('已删除')
    if (editingId.value === row.id) closeDrawer()
    await load()
    await loadColumnCorpus()
  } catch (e) {
    message.error(e?.message || '删除失败')
  } finally {
    deletingId.value = 0
  }
}

onMounted(async () => {
  await loadMeta()
  await load()
  await loadColumnCorpus()
  try {
    const res = await api.zhLexiconGaps()
    gapCount.value = res.gap_count ?? 0
    gaps.value = res.gaps || []
    gapsScanned.value = true
  } catch {
    /* ignore */
  }
})
</script>

<style scoped>
.zl-table-wrap {
  overflow: auto;
  max-height: calc(100vh - 380px);
}
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.data-table th,
.data-table td {
  text-align: left;
  padding: 8px 10px;
  border-bottom: 1px solid var(--line, var(--line-soft));
  vertical-align: middle;
  color: var(--ink-2, var(--ink));
}
.data-table th {
  color: var(--muted);
  font-weight: 500;
  position: sticky;
  top: 0;
  background: var(--surface);
  z-index: 1;
}
.data-table tr.is-editing {
  background: color-mix(in srgb, var(--teal-soft, #2a9d8f) 22%, transparent);
}
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
}
.bad {
  color: var(--error, #c00);
}
.pager-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 12px;
}
.zl-filter-row {
  gap: 8px;
  flex-wrap: wrap;
  flex: 1;
  min-width: 0;
}
.panel-quiet .panel-hd {
  align-items: flex-start;
}
.zl-drawer-form :deep(.n-form-item) {
  margin-bottom: 10px;
}
.zl-warn {
  margin: -4px 0 10px;
  color: var(--warning, #b45309);
  line-height: 1.4;
}
</style>
