<template>
  <div class="page-fill surface-page">
    <div class="surface-toolbar">
      <div>
        <h1 class="page-title">用例流程</h1>
        <p class="page-desc" style="margin-bottom:0">
          流程 kind × 皮 → 用例描述表模板。花括号占位符出表时按角色与菜单自动替换；台里保留
          <code>{actor}</code> 等形式，不要写成某个域的死中文。
        </p>
      </div>
      <AssetDeskActions
        :gap-loading="gapLoading"
        :migrating="migrating"
        create-label="登记流程"
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
          <div class="label">流程</div>
          <div class="value">{{ total }}</div>
        </div>
        <div class="stat">
          <div class="label">待补</div>
          <div class="value" :class="{ bad: gapsScanned && gapCount > 0 }">{{ gapStatDisplay(gapsScanned, gapCount) }}</div>
        </div>
      </div>

      <n-tabs v-model:value="mainTab" type="line" size="small" class="mb-12">
        <n-tab-pane name="entries" tab="流程" />
        <n-tab-pane name="gaps" tab="待补" />
      </n-tabs>

      <div v-show="mainTab === 'entries'" class="panel panel-quiet">
        <div class="panel-hd">
          <div class="row asset-desk-filter-row">
            <n-select
              v-model:value="kind"
              size="small"
              clearable
              filterable
              placeholder="全部 kind"
              :options="kindOptions"
              style="width:200px"
              @update:value="reloadFromTop"
            />
            <n-select
              v-model:value="face"
              size="small"
              clearable
              placeholder="全部皮"
              :options="faceOptions"
              style="width:140px"
              @update:value="reloadFromTop"
            />
            <n-input
              v-model:value="q"
              size="small"
              clearable
              placeholder="名称 / 摘要 / 步骤"
              style="width:200px"
              @keyup.enter="reloadFromTop"
            />
            <n-button size="small" @click="reloadFromTop">查询</n-button>
          </div>
        </div>
        <div class="panel-bd">
          <div v-if="!items.length" class="empty-hint">
            <div class="empty-title">还没有流程</div>
            <div class="empty-desc">用顶栏导入或登记一条。</div>
          </div>
          <template v-else>
            <div class="asset-desk-table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>kind</th>
                    <th>皮</th>
                    <th>名称模板</th>
                    <th>摘要</th>
                    <th style="width:100px"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="row in pagedItems"
                    :key="row.id"
                    :class="{ 'is-editing': editingId === row.id && drawerOpen }"
                  >
                    <td>{{ row.flow_kind }}</td>
                    <td class="muted">{{ faceLabel(row.face) }}</td>
                    <td>{{ row.name_tpl }}</td>
                    <td class="muted">{{ row.summary_tpl }}</td>
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
                  ? '种子与（若扫过）68 域菜单流程已齐。'
                  : '点顶栏「检查待补」或「扫 68 域」。'
              }}
            </div>
          </div>
          <template v-else>
            <div class="asset-desk-table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>kind</th>
                    <th>皮</th>
                    <th>域</th>
                    <th>说明</th>
                    <th style="width:80px"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(g, idx) in pagedGaps" :key="`${g.flow_kind}-${g.face}-${g.domain_id || ''}-${idx}`">
                    <td>{{ g.flow_kind }}</td>
                    <td class="muted">{{ faceLabel(g.face) }}</td>
                    <td class="muted">{{ g.domain_id || '—' }}</td>
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

    <n-drawer v-model:show="drawerOpen" :width="480" placement="right" @after-leave="onDrawerLeave">
      <n-drawer-content :title="editingId ? '改流程' : '登记流程'" closable>
        <div class="asset-desk-drawer-form">
          <n-form-item label="kind" :show-feedback="false">
            <n-select
              v-model:value="form.flow_kind"
              size="small"
              filterable
              tag
              :disabled="identityLocked"
              :options="kindOptions"
              placeholder="如 seat_shows"
            />
          </n-form-item>
          <n-form-item label="皮" :show-feedback="false">
            <n-select
              v-model:value="form.face"
              size="small"
              :disabled="identityLocked"
              :options="faceOptions"
            />
          </n-form-item>
          <n-form-item label="名称模板" :show-feedback="false">
            <n-input v-model:value="form.name_tpl" size="small" :maxlength="128" show-count />
          </n-form-item>
          <n-form-item label="摘要模板" :show-feedback="false">
            <n-input
              v-model:value="form.summary_tpl"
              size="small"
              type="textarea"
              :autosize="{ minRows: 2, maxRows: 4 }"
              :maxlength="256"
              show-count
            />
          </n-form-item>
          <n-form-item label="事件流（每行一步）" :show-feedback="false">
            <n-input
              v-model:value="form.flowText"
              size="small"
              type="textarea"
              :autosize="{ minRows: 5, maxRows: 12 }"
              placeholder="{actor}登录成功后…"
            />
          </n-form-item>
          <n-form-item label="排序" :show-feedback="false">
            <n-input-number v-model:value="form.sort" size="small" :min="0" style="width:100%" />
          </n-form-item>
          <div class="uf-ph">
            <div class="uf-ph-title">可用占位符（点击插入到事件流）</div>
            <div class="uf-ph-list">
              <button
                v-for="p in placeholders"
                :key="p.token"
                type="button"
                class="uf-ph-chip"
                :title="p.zh"
                @click="insertPlaceholder(p.token)"
              >
                <code>{{ p.token }}</code>
                <span>{{ p.zh }}</span>
              </button>
            </div>
            <p class="small muted" style="margin:8px 0 0">{{ formHint }}</p>
          </div>
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
const kind = ref(null)
const face = ref(null)
const q = ref('')
const gaps = ref([])
const gapCount = ref(0)
const gapsScanned = ref(false)
const gapPage = ref(1)
const gapPageSize = ref(20)
const lastScanDomains = ref(false)

const meta = reactive({ kind_options: [], face_options: [], placeholders: [] })
const form = reactive({
  flow_kind: 'open',
  face: '*',
  name_tpl: '',
  summary_tpl: '',
  flowText: '',
  sort: 0,
})

const identityLocked = computed(() => !!editingId.value || fromGap.value)

const placeholders = computed(() =>
  meta.placeholders.length
    ? meta.placeholders
    : [
        { token: '{actor}', zh: '本用例执行者（按端/岗位）' },
        { token: '{user}', zh: '用户端角色名' },
        { token: '{admin}', zh: '管理端角色名' },
        { token: '{label}', zh: '菜单中文名' },
        { token: '{entity}', zh: '主业务对象名' },
        { token: '{ticket_stem}', zh: '单据短名（由菜单名收短）' },
        { token: '{reserve_stem}', zh: '预约对象短名' },
        { token: '{app}', zh: '系统名' },
      ],
)

const formHint = computed(() => {
  if (identityLocked.value) {
    return editingId.value
      ? 'kind 与皮已锁定，可改模板与步骤。更换请删除后重新登记。'
      : '待补项标识已锁定，请补全模板后保存。'
  }
  return '保留花括号即可；出论文表时自动替换。演艺/影院皮用 face 覆盖默认句，不必改 * 行。'
})

function insertPlaceholder(token) {
  const t = String(token || '')
  if (!t) return
  form.flowText = form.flowText ? `${form.flowText}${form.flowText.endsWith('\n') ? '' : '\n'}${t}` : t
}

const kindOptions = computed(() =>
  meta.kind_options.length
    ? meta.kind_options
    : [{ value: 'open', label: 'open' }],
)

const faceOptions = computed(() =>
  meta.face_options.length
    ? meta.face_options
    : [
        { value: '*', label: '默认' },
        { value: 'performance', label: '演艺票务' },
        { value: 'cinema', label: '影院票务' },
      ],
)

const pagedItems = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return items.value.slice(start, start + pageSize.value)
})

const pagedGaps = computed(() => {
  const start = (gapPage.value - 1) * gapPageSize.value
  return gaps.value.slice(start, start + gapPageSize.value)
})

function faceLabel(f) {
  const hit = faceOptions.value.find((o) => o.value === f)
  return hit ? hit.label : f || '默认'
}


function onPageSize() {
  page.value = 1
}

function reloadFromTop() {
  page.value = 1
  reload()
}

function resetForm() {
  form.flow_kind = 'open'
  form.face = '*'
  form.name_tpl = ''
  form.summary_tpl = ''
  form.flowText = ''
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
  const res = await api.usecaseFlowsMeta()
  meta.kind_options = res.kind_options || []
  meta.face_options = res.face_options || []
  meta.placeholders = res.placeholders || []
}

async function reload() {
  try {
    const params = {}
    if (kind.value) params.flow_kind = kind.value
    if (face.value != null) params.face = face.value
    if (q.value) params.q = q.value
    const res = await api.usecaseFlows(params)
    items.value = res.items || []
    total.value = res.total ?? items.value.length
    const maxPage = Math.max(1, Math.ceil((total.value || 0) / pageSize.value) || 1)
    if (page.value > maxPage) page.value = maxPage
  } catch (e) {
    message.error(e?.message || '加载失败')
  }
}

async function scanGaps(scanDomains) {
  gapLoading.value = true
  lastScanDomains.value = !!scanDomains
  try {
    const res = await api.usecaseFlowsGaps({ scan_domains: !!scanDomains })
    gaps.value = res.gaps || []
    gapCount.value = res.gap_count ?? gaps.value.length
    gapsScanned.value = true
    gapPage.value = 1
    mainTab.value = 'gaps'
    if (gapCount.value) message.info(`待补 ${gapCount.value} 条`)
    else message.success(scanDomains ? '68 域菜单流程已齐' : '没有待补项')
  } catch (e) {
    message.error(e?.message || '检查失败')
  } finally {
    gapLoading.value = false
  }
}

async function migrate() {
  migrating.value = true
  try {
    const res = await api.usecaseFlowsMigrate()
    const n = res.inserted ?? 0
    message.success(n > 0 ? `已补 ${n} 条，合计 ${res.total || 0}` : '没有缺项可追加')
    page.value = 1
    await loadMeta()
    await reload()
    mainTab.value = 'entries'
  } catch (e) {
    message.error(e?.message || '导入失败')
  } finally {
    migrating.value = false
  }
}

function openCreate() {
  resetForm()
  form.name_tpl = '{actor}使用{label}'
  form.summary_tpl = '{actor}打开「{label}」并完成页面主操作。'
  form.flowText = [
    '{actor}登录成功后进入系统，点击「{label}」',
    '系统转至「{label}」界面',
    '{actor}查看页面主列表或主表单并完成可用操作',
    '系统按页面实现反馈操作结果',
  ].join('\n')
  drawerOpen.value = true
}

function editRow(row) {
  fromGap.value = false
  editingId.value = row.id
  form.flow_kind = row.flow_kind
  form.face = row.face || '*'
  form.name_tpl = row.name_tpl
  form.summary_tpl = row.summary_tpl
  form.flowText = (row.flow || []).join('\n')
  form.sort = row.sort || 0
  drawerOpen.value = true
}

function fillFromGap(g) {
  editingId.value = 0
  fromGap.value = true
  form.flow_kind = g.flow_kind
  form.face = g.face || '*'
  form.name_tpl = '{actor}使用{label}'
  form.summary_tpl = '{actor}打开「{label}」并完成页面主操作。'
  form.flowText = ''
  form.sort = 0
  drawerOpen.value = true
  mainTab.value = 'entries'
}

async function save() {
  if (!form.flow_kind?.trim()) {
    message.warning('kind 必填')
    return
  }
  if (!form.name_tpl.trim() || !form.summary_tpl.trim()) {
    message.warning('名称与摘要模板必填')
    return
  }
  saving.value = true
  try {
    const flow = form.flowText
      .split(/\r?\n/)
      .map((s) => s.trim())
      .filter(Boolean)
    await api.usecaseFlowsUpsert({
      flow_kind: form.flow_kind.trim(),
      face: form.face || '*',
      name_tpl: form.name_tpl.trim(),
      summary_tpl: form.summary_tpl.trim(),
      flow,
      sort: form.sort || 0,
      source: 'manual',
    })
    message.success(editingId.value ? '已保存修改' : '已保存')
    drawerOpen.value = false
    resetForm()
    await loadMeta()
    await reload()
    if (gapsScanned.value) {
      const gapRes = await api.usecaseFlowsGaps({ scan_domains: lastScanDomains.value })
      gaps.value = gapRes.gaps || []
      gapCount.value = gapRes.gap_count ?? gaps.value.length
    }
  } catch (e) {
    message.error(e?.response?.data?.detail || e?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function remove(row) {
  const ok = await confirm(`删除「${row.flow_kind} / ${faceLabel(row.face)}」？`, {
    title: '删除流程',
    positiveText: '删除',
  })
  if (!ok) return
  deletingId.value = row.id
  try {
    await api.usecaseFlowsDelete(row.id)
    message.success('已删除')
    if (editingId.value === row.id) closeDrawer()
    await reload()
  } catch (e) {
    message.error(e?.message || '删除失败')
  } finally {
    deletingId.value = 0
  }
}

onMounted(async () => {
  try {
    await loadMeta()
    await reload()
  } catch (e) {
    message.error(e?.message || '加载失败')
  } finally {
    booted.value = true
  }
})
</script>

<style scoped>
.asset-desk-drawer-form .uf-ph-title {
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 6px;
}
.uf-ph-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 180px;
  overflow: auto;
}
.uf-ph-chip {
  display: flex;
  align-items: baseline;
  gap: 8px;
  text-align: left;
  border: 1px solid var(--line, var(--line-soft));
  background: var(--surface);
  color: var(--ink-2, var(--ink));
  border-radius: 6px;
  padding: 6px 8px;
  cursor: pointer;
  font-size: 12px;
}
.uf-ph-chip:hover {
  border-color: var(--teal, #2a9d8f);
}
.uf-ph-chip code {
  font-size: 12px;
  white-space: nowrap;
}
</style>
