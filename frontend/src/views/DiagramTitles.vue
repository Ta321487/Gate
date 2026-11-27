<template>
  <div class="page-fill surface-page">
    <div class="surface-toolbar">
      <div>
        <h1 class="page-title">论文图题</h1>
        <p class="page-desc" style="margin-bottom:0">
          图种 × 域 → 标题模板（占位符 name）；出包写入 schema.diagramTitleTemplates。几何排版仍归论文图债，不在本台。
        </p>
      </div>
      <AssetDeskActions
        :gap-loading="gapLoading"
        :migrating="migrating"
        create-label="登记图题"
        @check="scanGaps"
        @migrate="migrate"
        @create="openCreate"
      />
    </div>

    <PageSkeleton v-if="!booted" variant="dashboard" :rows="4" />
    <template v-else>
      <div class="stats mb-12" style="grid-template-columns:repeat(2,1fr);max-width:360px">
        <div class="stat">
          <div class="label">图题</div>
          <div class="value">{{ total }}</div>
        </div>
        <div class="stat">
          <div class="label">待补</div>
          <div class="value" :class="{ bad: gapsScanned && gapCount > 0 }">{{ gapStatDisplay(gapsScanned, gapCount) }}</div>
        </div>
      </div>

      <n-tabs v-model:value="mainTab" type="line" size="small" class="mb-12">
        <n-tab-pane name="entries" tab="图题" />
        <n-tab-pane name="gaps" tab="待补" />
      </n-tabs>

      <div v-show="mainTab === 'entries'" class="panel panel-quiet">
        <div class="panel-hd">
          <div class="row asset-desk-filter-row">
            <n-select
              v-model:value="kind"
              size="small"
              clearable
              placeholder="全部图种"
              :options="kindOptions"
              style="width:160px"
              @update:value="reloadFromTop"
            />
            <n-select
              v-model:value="domain"
              size="small"
              clearable
              filterable
              placeholder="全部域"
              :options="domainOptions"
              style="width:220px"
              :consistent-menu-width="false"
              :menu-props="{ style: { minWidth: '320px' } }"
              @update:value="reloadFromTop"
            />
            <n-input
              v-model:value="q"
              size="small"
              clearable
              placeholder="模板 / 图种"
              style="width:180px"
              @keyup.enter="reloadFromTop"
            />
            <n-button size="small" @click="reloadFromTop">查询</n-button>
          </div>
        </div>
        <div class="panel-bd">
          <div v-if="!items.length" class="empty-hint">
            <div class="empty-title">还没有图题</div>
            <div class="empty-desc">用顶栏导入或登记一条。</div>
          </div>
          <template v-else>
            <div class="asset-desk-table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>图种</th>
                    <th>域</th>
                    <th>标题模板</th>
                    <th style="width:100px"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="row in pagedItems"
                    :key="row.id"
                    :class="{ 'is-editing': editingId === row.id && drawerOpen }"
                  >
                    <td>{{ kindLabel(row.diagram_kind) }}</td>
                    <td class="muted">{{ domainLabel(row.domain_id) }}</td>
                    <td>{{ row.title_tpl }}</td>
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

      <div v-show="mainTab === 'gaps'" class="panel panel-quiet">
        <div class="panel-bd">
          <div v-if="!gaps.length" class="empty-hint">
            <div class="empty-title">{{ gapsScanned ? '没有待补项' : '还没检查过' }}</div>
            <div class="empty-desc">
              {{
                gapsScanned
                  ? '各图种跨域壳默认已齐。'
                  : '点顶栏「检查待补」扫描缺口。'
              }}
            </div>
          </div>
          <template v-else>
            <div class="asset-desk-table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>图种</th>
                    <th>域</th>
                    <th>说明</th>
                    <th style="width:80px"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(g, idx) in pagedGaps" :key="`${g.diagram_kind}-${g.domain_id}-${idx}`">
                    <td>{{ kindLabel(g.diagram_kind) }}</td>
                    <td class="muted">{{ domainLabel(g.domain_id) }}</td>
                    <td>{{ g.reason }}</td>
                    <td>
                      <n-button size="small" quaternary @click="fillFromGap(g)">补</n-button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-if="gaps.length > 0" class="pager-row">
              <span class="small muted">共 {{ gaps.length }} 条</span>
              <n-pagination
                v-model:page="gapPage"
                v-model:page-size="gapPageSize"
                :item-count="gaps.length"
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

    <n-drawer v-model:show="drawerOpen" :width="420" placement="right" @after-leave="onDrawerLeave">
      <n-drawer-content :title="editingId ? '改图题' : '登记图题'" closable>
        <div class="asset-desk-drawer-form">
          <n-form-item label="图种" :show-feedback="false">
            <n-select
              v-model:value="form.diagram_kind"
              size="small"
              :disabled="identityLocked"
              :options="kindOptions"
            />
          </n-form-item>
          <n-form-item label="域" :show-feedback="false">
            <n-select
              v-model:value="form.domain_id"
              size="small"
              filterable
              :disabled="identityLocked"
              :options="domainOptions"
              :consistent-menu-width="false"
              :menu-props="{ style: { minWidth: '320px' } }"
            />
          </n-form-item>
          <n-form-item label="标题模板" :show-feedback="false">
            <n-input
              v-model:value="form.title_tpl"
              size="small"
              :maxlength="128"
              show-count
              placeholder="如 {name}类图"
            />
          </n-form-item>
          <n-form-item label="排序" :show-feedback="false">
            <n-input-number v-model:value="form.sort" size="small" :min="0" style="width:100%" />
          </n-form-item>
          <p class="small muted">{{ formHint }}</p>
          <div class="row" style="gap:8px;justify-content:flex-end;margin-top:12px">
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
const kind = ref(null)
const domain = ref(null)
const q = ref('')
const gaps = ref([])
const gapCount = ref(0)
const gapsScanned = ref(false)
const gapPage = ref(1)
const gapPageSize = ref(20)

const meta = reactive({ domains: [], kind_options: [] })
const form = reactive({
  diagram_kind: 'class',
  domain_id: '*',
  title_tpl: '',
  sort: 0,
})

const identityLocked = computed(() => !!editingId.value || fromGap.value)

const formHint = computed(() => {
  if (identityLocked.value) {
    return editingId.value
      ? '图种与域已锁定，可改标题模板与排序。更换请删除后重新登记。'
      : '待补项标识已锁定，请补全标题模板后保存。'
  }
  return '占位符 name（花括号包裹）= 系统名或功能名；具名域覆盖跨域壳默认。'
})

const kindOptions = computed(() =>
  meta.kind_options.length
    ? meta.kind_options
    : [
        { value: 'class', label: '类图' },
        { value: 'sequence', label: '序列图' },
        { value: 'activity', label: '活动图' },
        { value: 'er', label: 'E-R图' },
        { value: 'architecture', label: '逻辑架构图' },
        { value: 'modules', label: '功能模块图' },
      ],
)

const domainOptions = computed(() =>
  meta.domains.map((d) => ({
    label: d.id === '*' ? '跨域壳默认' : `${d.name || d.id}（${d.id}）`,
    value: d.id,
  })),
)

const pagedItems = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return items.value.slice(start, start + pageSize.value)
})

const pagedGaps = computed(() => {
  const start = (gapPage.value - 1) * gapPageSize.value
  return gaps.value.slice(start, start + gapPageSize.value)
})

function kindLabel(k) {
  const hit = kindOptions.value.find((o) => o.value === k)
  return hit ? hit.label : k
}

function domainLabel(id) {
  if (!id || id === '*') return '跨域壳默认'
  const hit = meta.domains.find((d) => d.id === id)
  return hit ? hit.name || id : id
}


function onPageSize() {
  page.value = 1
}

function reloadFromTop() {
  page.value = 1
  reload()
}

function resetForm() {
  form.diagram_kind = 'class'
  form.domain_id = '*'
  form.title_tpl = ''
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

async function loadMeta() {
  const res = await api.diagramTitlesMeta()
  meta.domains = res.domains || []
  meta.kind_options = res.kind_options || []
}

async function reload() {
  try {
    const params = {}
    if (kind.value) params.diagram_kind = kind.value
    if (domain.value != null) params.domain_id = domain.value
    if (q.value) params.q = q.value
    const res = await api.diagramTitles(params)
    items.value = res.items || []
    total.value = res.total ?? items.value.length
    const maxPage = Math.max(1, Math.ceil((total.value || 0) / pageSize.value) || 1)
    if (page.value > maxPage) page.value = maxPage
  } catch (e) {
    toastApiError(e, '加载失败')
  }
}

async function scanGaps() {
  gapLoading.value = true
  try {
    const res = await api.diagramTitlesGaps()
    gaps.value = res.gaps || []
    gapCount.value = res.gap_count ?? gaps.value.length
    gapsScanned.value = true
    gapPage.value = 1
    mainTab.value = 'gaps'
    if (gapCount.value) message.info(`待补 ${gapCount.value} 条`)
    else message.success('没有待补项')
  } catch (e) {
    toastApiError(e, '检查失败')
  } finally {
    gapLoading.value = false
  }
}

async function migrate() {
  migrating.value = true
  try {
    const res = await api.diagramTitlesMigrate()
    const n = res.inserted ?? 0
    message.success(n > 0 ? `已补 ${n} 条，合计 ${res.total || 0}` : '没有缺项可追加')
    page.value = 1
    await reload()
    mainTab.value = 'entries'
  } catch (e) {
    toastApiError(e, '导入失败')
  } finally {
    migrating.value = false
  }
}

function openCreate() {
  resetForm()
  form.title_tpl = '{name}类图'
  drawerOpen.value = true
}

function editRow(row) {
  fromGap.value = false
  editingId.value = row.id
  form.diagram_kind = row.diagram_kind
  form.domain_id = row.domain_id
  form.title_tpl = row.title_tpl
  form.sort = row.sort || 0
  drawerOpen.value = true
}

function fillFromGap(g) {
  editingId.value = 0
  fromGap.value = true
  form.diagram_kind = g.diagram_kind
  form.domain_id = g.domain_id || '*'
  form.title_tpl = `{name}${kindLabel(g.diagram_kind)}`
  form.sort = 0
  drawerOpen.value = true
  mainTab.value = 'entries'
}

async function save() {
  if (!form.title_tpl.trim()) {
    message.warning('标题模板必填')
    return
  }
  saving.value = true
  try {
    await api.diagramTitlesUpsert({
      diagram_kind: form.diagram_kind,
      domain_id: form.domain_id || '*',
      title_tpl: form.title_tpl.trim(),
      sort: form.sort || 0,
      source: 'manual',
    })
    message.success(editingId.value ? '已保存修改' : '已保存')
    drawerOpen.value = false
    resetForm()
    await reload()
    if (gapsScanned.value) {
      const gapRes = await api.diagramTitlesGaps()
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
  const ok = await confirm(`删除「${row.title_tpl}」？`, {
    title: '删除图题',
    positiveText: '删除',
  })
  if (!ok) return
  deletingId.value = row.id
  try {
    await api.diagramTitlesDelete(row.id)
    message.success('已删除')
    if (editingId.value === row.id) closeDrawer()
    await reload()
  } catch (e) {
    toastApiError(e, '删除失败')
  } finally {
    deletingId.value = 0
  }
}

onMounted(async () => {
  try {
    await loadMeta()
    await reload()
  } catch (e) {
    toastApiError(e, '加载失败')
  } finally {
    booted.value = true
  }
})
</script>

