<template>
  <div class="page-fill surface-page">
    <div class="surface-toolbar">
      <div>
        <h1 class="page-title">控件语义</h1>
        <p class="page-desc" style="margin-bottom:0">
          维护档案字段标签启发式到控件的映射；类型直映仍由代码保证，本台只管可扩展的标签规则。
        </p>
      </div>
      <AssetDeskActions
        :gap-loading="gapLoading"
        :migrating="migrating"
        create-label="登记规则"
        @check="scanGaps"
        @migrate="migrate"
        @create="openCreate"
      />
    </div>

    <PageSkeleton v-if="!booted" variant="dashboard" :rows="4" />
    <template v-else>
      <div class="stats mb-12" style="grid-template-columns:repeat(2,1fr);max-width:360px">
        <div class="stat">
          <div class="label">规则</div>
          <div class="value">{{ total }}</div>
        </div>
        <div class="stat">
          <div class="label">待补</div>
          <div class="value" :class="{ bad: gapsScanned && gapCount > 0 }">{{ gapStatDisplay(gapsScanned, gapCount) }}</div>
        </div>
      </div>

      <n-tabs v-model:value="mainTab" type="line" size="small" class="mb-12">
        <n-tab-pane name="entries" tab="规则" />
        <n-tab-pane name="gaps" tab="待补" />
      </n-tabs>

      <div v-show="mainTab === 'entries'" class="panel panel-quiet">
        <div class="panel-hd">
          <div class="row asset-desk-filter-row">
            <n-input
              v-model:value="q"
              size="small"
              clearable
              placeholder="规则键 / 模式 / 控件"
              style="width:240px"
              @keyup.enter="reloadFromTop"
            />
            <n-button size="small" @click="reloadFromTop">查询</n-button>
          </div>
        </div>
        <div class="panel-bd">
          <div v-if="!items.length" class="empty-hint">
            <div class="empty-title">还没有规则</div>
            <div class="empty-desc">用顶栏导入或登记一条。</div>
          </div>
          <template v-else>
            <div class="asset-desk-table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>规则键</th>
                    <th>匹配</th>
                    <th>控件</th>
                    <th>说明</th>
                    <th style="width:100px"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="row in pagedItems"
                    :key="row.id"
                    :class="{ 'is-editing': editingId === row.id }"
                  >
                    <td class="mono">{{ row.rule_key }}</td>
                    <td>
                      <span class="muted">{{ scopeLabel(row.match_scope) }}</span>
                      · <span class="mono">{{ row.match_pattern }}</span>
                    </td>
                    <td>{{ widgetLabel(row.widget) }}</td>
                    <td class="muted">{{ row.note_zh || '—' }}</td>
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
              {{ gapsScanned ? '种子规则已齐。' : '点顶栏「检查待补」扫描缺口。' }}
            </div>
          </div>
          <template v-else>
            <div class="asset-desk-table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>规则键</th>
                    <th>说明</th>
                    <th style="width:100px"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="g in pagedGaps" :key="g.rule_key">
                    <td class="mono">{{ g.rule_key }}</td>
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
      <n-drawer-content :title="editingId ? '改规则' : '登记规则'" closable>
        <div class="asset-desk-drawer-form">
          <n-form-item label="规则键" :show-feedback="false">
            <n-input
              v-model:value="form.rule_key"
              size="small"
              :disabled="identityLocked"
              placeholder="如 textarea_label"
            />
          </n-form-item>
          <n-form-item label="匹配范围" :show-feedback="false">
            <n-select v-model:value="form.match_scope" size="small" :options="scopeOptions" />
          </n-form-item>
          <n-form-item label="匹配模式" :show-feedback="false">
            <n-input
              v-model:value="form.match_pattern"
              size="small"
              type="textarea"
              :rows="2"
              placeholder="标签原文、| 分隔精确表，或正则"
            />
          </n-form-item>
          <n-form-item label="限定类型" :show-feedback="false">
            <n-select
              v-model:value="form.when_type"
              size="small"
              clearable
              placeholder="不限"
              :options="whenTypeOptions"
            />
          </n-form-item>
          <n-form-item label="控件" :show-feedback="false">
            <n-select v-model:value="form.widget" size="small" filterable :options="widgetOptions" />
          </n-form-item>
          <n-form-item label="说明" :show-feedback="false">
            <n-input v-model:value="form.note_zh" size="small" :maxlength="128" show-count />
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
const q = ref('')

const gaps = ref([])
const gapCount = ref(0)
const gapsScanned = ref(false)
const gapPage = ref(1)
const gapPageSize = ref(20)

const meta = reactive({
  widget_options: [],
  scope_options: [],
  when_type_options: [],
})

const FALLBACK_WIDGET_OPTIONS = [
  { value: 'text', label: '单行文本' },
  { value: 'textarea', label: '多行文本' },
  { value: 'richtext', label: '富文本' },
  { value: 'number', label: '数字' },
  { value: 'money', label: '金额' },
  { value: 'switch', label: '开关' },
  { value: 'select', label: '下拉选择' },
  { value: 'date', label: '日期' },
  { value: 'datetime', label: '日期时间' },
  { value: 'time', label: '时刻' },
  { value: 'url', label: '链接' },
  { value: 'hidden', label: '隐藏' },
]

const FALLBACK_SCOPE_OPTIONS = [
  { value: 'label_exact', label: '标签精确' },
  { value: 'label_contains', label: '标签包含' },
  { value: 'label_regex', label: '标签正则' },
  { value: 'key', label: '字段键' },
]

const FALLBACK_WHEN_TYPE_OPTIONS = [
  { value: 'string', label: '字符串' },
  { value: 'number', label: '数字' },
]

const form = reactive({
  rule_key: '',
  match_scope: 'label_contains',
  match_pattern: '',
  when_type: null,
  widget: 'textarea',
  note_zh: '',
  sort: 0,
  enabled: true,
})

const identityLocked = computed(() => !!editingId.value || fromGap.value)

const formHint = computed(() => {
  if (identityLocked.value) {
    return editingId.value
      ? '规则键已锁定，可修改匹配与控件。更换键请删除后重新登记。'
      : '待补项标识已锁定，请补全匹配模式与控件后保存。'
  }
  return '类型直映（如 date→日期选择器）由代码保证；本台扩展标签启发式。出包投影为 fieldWidgetRules.js（学生腔关键词表）。'
})

const scopeOptions = computed(() =>
  meta.scope_options.length ? meta.scope_options : FALLBACK_SCOPE_OPTIONS,
)

const widgetOptions = computed(() =>
  meta.widget_options.length ? meta.widget_options : FALLBACK_WIDGET_OPTIONS,
)

const whenTypeOptions = computed(() =>
  meta.when_type_options.length ? meta.when_type_options : FALLBACK_WHEN_TYPE_OPTIONS,
)

function widgetLabel(code) {
  const hit = widgetOptions.value.find((o) => o.value === code)
  return hit ? hit.label : code || '—'
}

function scopeLabel(code) {
  const hit = scopeOptions.value.find((o) => o.value === code)
  return hit ? hit.label : code || '—'
}

const pagedItems = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return items.value.slice(start, start + pageSize.value)
})

const pagedGaps = computed(() => {
  const start = (gapPage.value - 1) * gapPageSize.value
  return gaps.value.slice(start, start + gapPageSize.value)
})


function onPageSize() {
  page.value = 1
}

function reloadFromTop() {
  page.value = 1
  load()
}

function resetForm() {
  form.rule_key = ''
  form.match_scope = 'label_contains'
  form.match_pattern = ''
  form.when_type = null
  form.widget = 'textarea'
  form.note_zh = ''
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
  form.rule_key = row.rule_key || ''
  form.match_scope = row.match_scope || 'label_contains'
  form.match_pattern = row.match_pattern || ''
  form.when_type = row.when_type || null
  form.widget = row.widget || 'text'
  form.note_zh = row.note_zh || ''
  form.sort = row.sort ?? 0
  form.enabled = row.enabled !== false
  drawerOpen.value = true
}

function fillFromGap(g) {
  editingId.value = 0
  fromGap.value = true
  form.rule_key = g.rule_key || ''
  form.match_scope = 'label_contains'
  form.match_pattern = ''
  form.when_type = null
  form.widget = 'text'
  form.note_zh = ''
  form.sort = 0
  form.enabled = true
  drawerOpen.value = true
}

async function loadMeta() {
  try {
    const res = await api.widgetHintsMeta()
    meta.widget_options = res.widget_options || []
    meta.scope_options = res.scope_options || []
    meta.when_type_options = res.when_type_options || []
  } catch (e) {
    message.error(e?.message || '加载选项失败')
  }
}

async function load() {
  try {
    const params = {}
    if (q.value) params.q = q.value
    const res = await api.widgetHints(params)
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
    const res = await api.widgetHintsMigrate()
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
    const res = await api.widgetHintsGaps()
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
  if (!form.rule_key?.trim() || !form.match_pattern?.trim() || !form.widget) {
    message.warning('规则键、匹配模式与控件都要填')
    return
  }
  saving.value = true
  try {
    await api.widgetHintsUpsert({
      rule_key: form.rule_key.trim(),
      match_scope: form.match_scope,
      match_pattern: form.match_pattern.trim(),
      when_type: form.when_type || '',
      widget: form.widget,
      note_zh: (form.note_zh || '').trim(),
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
      const gapRes = await api.widgetHintsGaps()
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
  const ok = await confirm(`删除规则「${row.rule_key}」？`, {
    title: '删除规则',
    positiveText: '删除',
  })
  if (!ok) return
  deletingId.value = row.id
  try {
    await api.widgetHintsDelete(row.id)
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

