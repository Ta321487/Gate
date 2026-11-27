<template>
  <div class="page-fill surface-page">
    <div class="surface-toolbar">
      <div>
        <h1 class="page-title">开关建议</h1>
        <p class="page-desc" style="margin-bottom:0">
          维护开题扫词与开关证据；命中后在匹配确认展示建议，须人工确认后落库。
        </p>
      </div>
      <AssetDeskActions
        :gap-loading="gapLoading"
        :migrating="migrating"
        create-label="登记扫词"
        @check="scanGaps"
        @migrate="migrate"
        @create="openCreate"
      />
    </div>

    <PageSkeleton v-if="!booted" variant="dashboard" :rows="4" />
    <template v-else>
      <div class="stats mb-12" style="grid-template-columns:repeat(2,1fr);max-width:360px">
        <div class="stat">
          <div class="label">扫词</div>
          <div class="value">{{ total }}</div>
        </div>
        <div class="stat">
          <div class="label">待补</div>
          <div class="value" :class="{ bad: gapsScanned && gapCount > 0 }">{{ gapStatDisplay(gapsScanned, gapCount) }}</div>
        </div>
      </div>

      <n-tabs v-model:value="mainTab" type="line" size="small" class="mb-12">
        <n-tab-pane name="entries" tab="扫词" />
        <n-tab-pane name="gaps" tab="待补" />
      </n-tabs>

      <div v-show="mainTab === 'entries'" class="panel panel-quiet">
        <div class="panel-hd">
          <div class="row asset-desk-filter-row">
            <n-select
              v-model:value="addonId"
              size="small"
              clearable
              filterable
              placeholder="全部开关"
              style="width:220px"
              :options="addonFilterOptions"
              @update:value="reloadFromTop"
            />
            <n-input
              v-model:value="q"
              size="small"
              clearable
              placeholder="提示词 / 证据"
              style="width:200px"
              @keyup.enter="reloadFromTop"
            />
            <n-button size="small" @click="reloadFromTop">查询</n-button>
          </div>
        </div>
        <div class="panel-bd">
          <div v-if="!items.length" class="empty-hint">
            <div class="empty-title">还没有扫词</div>
            <div class="empty-desc">用顶栏导入或登记一条。</div>
          </div>
          <template v-else>
            <div class="asset-desk-table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>开关</th>
                    <th>提示词</th>
                    <th>证据</th>
                    <th>建议开启</th>
                    <th style="width:100px"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="row in pagedItems"
                    :key="row.id"
                    :class="{ 'is-editing': editingId === row.id }"
                  >
                    <td>{{ row.addon_label || row.addon_id }}</td>
                    <td class="mono">{{ row.hint }}</td>
                    <td>{{ row.evidence_zh || '—' }}</td>
                    <td>{{ row.recommend ? '是' : '否' }}</td>
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
                :page-sizes="[20, 50, 100]"
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
              {{ gapsScanned ? '种子中的开关均已有扫词。' : '点顶栏「检查待补」扫描缺少扫词的开关。' }}
            </div>
          </div>
          <template v-else>
            <div class="asset-desk-table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>开关</th>
                    <th>说明</th>
                    <th style="width:100px"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="g in pagedGaps" :key="g.addon_id">
                    <td class="mono">{{ g.addon_id }}</td>
                    <td>{{ g.reason || '缺少扫词规则' }}</td>
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
                :page-sizes="[20, 50]"
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
      <n-drawer-content :title="editingId ? '改扫词' : '登记扫词'" closable>
        <div class="asset-desk-drawer-form">
          <n-form-item label="开关" :show-feedback="false">
            <n-select
              v-model:value="form.addon_id"
              size="small"
              filterable
              tag
              :disabled="identityLocked"
              :options="addonFormOptions"
              placeholder="如 ai_assistant"
            />
          </n-form-item>
          <n-form-item label="展示名" :show-feedback="false">
            <n-input
              v-model:value="form.addon_label"
              size="small"
              :maxlength="64"
              show-count
              placeholder="匹配页显示名"
            />
          </n-form-item>
          <n-form-item label="提示词" :show-feedback="false">
            <n-input
              v-model:value="form.hint"
              size="small"
              :disabled="identityLocked"
              placeholder="开题中出现的原文片段"
            />
          </n-form-item>
          <n-form-item label="证据句" :show-feedback="false">
            <n-input
              v-model:value="form.evidence_zh"
              size="small"
              type="textarea"
              :rows="2"
              :maxlength="256"
              show-count
              placeholder="匹配页列出的命中说明"
            />
          </n-form-item>
          <n-form-item label="摘要" :show-feedback="false">
            <n-input
              v-model:value="form.summary_zh"
              size="small"
              type="textarea"
              :rows="2"
              :maxlength="256"
              show-count
              placeholder="建议卡一行说明"
            />
          </n-form-item>
          <n-form-item label="建议开启" :show-feedback="false">
            <n-switch v-model:value="form.recommend" />
          </n-form-item>
          <n-form-item label="可交付" :show-feedback="false">
            <n-switch v-model:value="form.deliverable" />
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
const addonId = ref(null)
const q = ref('')

const gaps = ref([])
const gapCount = ref(0)
const gapsScanned = ref(false)
const gapPage = ref(1)
const gapPageSize = ref(20)

const meta = reactive({
  addons: [],
})

const form = reactive({
  addon_id: 'ai_assistant',
  addon_label: '',
  hint: '',
  evidence_zh: '',
  summary_zh: '',
  recommend: true,
  deliverable: true,
  sort: 0,
})

const identityLocked = computed(() => !!editingId.value || fromGap.value)

const formHint = computed(() => {
  if (identityLocked.value) {
    return editingId.value
      ? '开关与提示词已锁定，可修改证据、摘要与建议开关。更换键请删除后重新登记。'
      : '待补项标识已锁定，请补全提示词与证据后保存。'
  }
  return '提示词在开题中命中后进入匹配页建议卡；建议开启不自动落库，须运营确认。不可交付的命中仅作记录。'
})

const addonFilterOptions = computed(() =>
  meta.addons.map((a) => ({
    label: a.label ? `${a.label}（${a.id}）` : a.id,
    value: a.id,
  })),
)

const addonFormOptions = computed(() => {
  const base = addonFilterOptions.value
  const known = new Set(base.map((o) => o.value))
  const extras = ['ai_assistant', 'spring_security', 'echarts']
    .filter((id) => !known.has(id))
    .map((id) => ({ label: id, value: id }))
  return [...base, ...extras]
})

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
  form.addon_id = meta.addons[0]?.id || 'ai_assistant'
  form.addon_label = meta.addons[0]?.label || ''
  form.hint = ''
  form.evidence_zh = ''
  form.summary_zh = ''
  form.recommend = true
  form.deliverable = true
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
  form.addon_id = row.addon_id || ''
  form.addon_label = row.addon_label || ''
  form.hint = row.hint || ''
  form.evidence_zh = row.evidence_zh || ''
  form.summary_zh = row.summary_zh || ''
  form.recommend = row.recommend !== false
  form.deliverable = row.deliverable !== false
  form.sort = row.sort ?? 0
  drawerOpen.value = true
}

function fillFromGap(g) {
  editingId.value = 0
  fromGap.value = true
  form.addon_id = g.addon_id || ''
  form.addon_label = g.addon_id || ''
  form.hint = ''
  form.evidence_zh = ''
  form.summary_zh = ''
  form.recommend = true
  form.deliverable = true
  form.sort = 0
  drawerOpen.value = true
}

async function loadMeta() {
  try {
    const res = await api.addonSuggestMeta()
    meta.addons = res.addons || []
  } catch (e) {
    toastApiError(e, '加载选项失败')
  }
}

async function load() {
  loading.value = true
  try {
    const params = {}
    if (addonId.value) params.addon_id = addonId.value
    if (q.value) params.q = q.value
    const res = await api.addonSuggest(params)
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
    const res = await api.addonSuggestMigrate()
    addonId.value = null
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
  gapLoading.value = true
  try {
    const res = await api.addonSuggestGaps()
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
  if (!form.addon_id?.trim() || !form.hint?.trim()) {
    message.warning('开关与提示词都要填')
    return
  }
  saving.value = true
  try {
    await api.addonSuggestUpsert({
      addon_id: form.addon_id.trim(),
      addon_label: (form.addon_label || '').trim(),
      hint: form.hint.trim(),
      evidence_zh: (form.evidence_zh || '').trim(),
      summary_zh: (form.summary_zh || '').trim(),
      recommend: form.recommend !== false,
      deliverable: form.deliverable !== false,
      sort: form.sort ?? 0,
      source: 'manual',
    })
    message.success(editingId.value ? '已保存修改' : '已保存')
    drawerOpen.value = false
    resetForm()
    await loadMeta()
    await load()
    if (gapsScanned.value) {
      const gapRes = await api.addonSuggestGaps()
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
  const ok = await confirm(`删除「${row.addon_id} / ${row.hint}」？`, {
    title: '删除扫词',
    positiveText: '删除',
  })
  if (!ok) return
  deletingId.value = row.id
  try {
    await api.addonSuggestDelete(row.id)
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

