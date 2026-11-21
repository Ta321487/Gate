<template>
  <div class="page-fill surface-page">
    <div class="surface-toolbar">
      <div>
        <h1 class="page-title">能力说明</h1>
        <p class="page-desc" style="margin-bottom:0">
          维护按需能力的 README 说明与菜单入口；开则必有、关则不得假宣称。
        </p>
      </div>
      <div class="row" style="gap:8px;flex-wrap:wrap">
        <n-button size="small" :loading="gapLoading" @click="scanGaps">检查待补</n-button>
        <n-button
          size="small"
          :loading="migrating"
          title="仅追加缺失项，不覆盖已有记录"
          @click="migrate"
        >导入初始说明</n-button>
        <n-button size="small" type="primary" @click="openCreate">登记说明</n-button>
      </div>
    </div>

    <PageSkeleton v-if="!booted" variant="dashboard" :rows="4" />
    <template v-else>
      <div class="stats mb-12" style="grid-template-columns:repeat(2,1fr);max-width:360px">
        <div class="stat">
          <div class="label">说明卡</div>
          <div class="value">{{ total }}</div>
        </div>
        <div class="stat">
          <div class="label">待补</div>
          <div class="value" :class="{ bad: gapCount > 0 }">{{ gapCount }}</div>
        </div>
      </div>

      <n-tabs v-model:value="mainTab" type="line" size="small" class="mb-12" @update:value="onTab">
        <n-tab-pane name="entries" tab="说明卡" />
        <n-tab-pane name="gaps" tab="待补" />
      </n-tabs>

      <div v-show="mainTab === 'entries'" class="panel panel-quiet">
        <div class="panel-hd">
          <div class="row cc-filter-row">
            <n-input
              v-model:value="q"
              size="small"
              clearable
              placeholder="能力 / 标题 / 正文"
              style="width:240px"
              @keyup.enter="reloadFromTop"
            />
            <n-button size="small" @click="reloadFromTop">查询</n-button>
          </div>
        </div>
        <div class="panel-bd">
          <div v-if="!items.length" class="empty-hint">
            <div class="empty-title">还没有说明卡</div>
            <div class="empty-desc">用顶栏导入或登记一条。</div>
          </div>
          <template v-else>
            <div class="cc-table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>能力</th>
                    <th>标题</th>
                    <th>菜单入口</th>
                    <th>README 槽</th>
                    <th style="width:100px"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="row in pagedItems"
                    :key="row.id"
                    :class="{ 'is-editing': editingId === row.id }"
                  >
                    <td class="mono">{{ row.cap_id }}</td>
                    <td>{{ row.title_zh || '—' }}</td>
                    <td class="mono muted">{{ row.menu_ids || '—' }}</td>
                    <td class="mono muted">{{ row.readme_slot || '—' }}</td>
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
              {{ gapsScanned ? '种子中的能力均已有说明卡。' : '点顶栏「检查待补」扫描缺口。' }}
            </div>
          </div>
          <template v-else>
            <div class="cc-table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>能力</th>
                    <th>说明</th>
                    <th style="width:100px"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="g in pagedGaps" :key="g.cap_id">
                    <td class="mono">{{ g.cap_id }}</td>
                    <td>{{ g.reason || '缺少能力说明卡' }}</td>
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

    <n-drawer v-model:show="drawerOpen" :width="460" placement="right" @after-leave="onDrawerLeave">
      <n-drawer-content :title="editingId ? '改说明' : '登记说明'" closable>
        <div class="cc-drawer-form">
          <n-form-item label="能力 ID" :show-feedback="false">
            <n-input
              v-model:value="form.cap_id"
              size="small"
              :disabled="identityLocked"
              placeholder="如 ai_assistant"
            />
          </n-form-item>
          <n-form-item label="标题" :show-feedback="false">
            <n-input v-model:value="form.title_zh" size="small" :maxlength="64" show-count />
          </n-form-item>
          <n-form-item label="README 正文" :show-feedback="false">
            <n-input
              v-model:value="form.body_zh"
              size="small"
              type="textarea"
              :rows="8"
              placeholder="开启时写入学生包 README 的 FAQ 段"
            />
          </n-form-item>
          <n-form-item label="鉴权句（开）" :show-feedback="false">
            <n-input v-model:value="form.auth_line_on" size="small" type="textarea" :rows="2" />
          </n-form-item>
          <n-form-item label="鉴权句（关）" :show-feedback="false">
            <n-input v-model:value="form.auth_line_off" size="small" type="textarea" :rows="2" />
          </n-form-item>
          <n-form-item label="技术栈后缀" :show-feedback="false">
            <n-input
              v-model:value="form.backend_suffix"
              size="small"
              placeholder="如 + Spring Security"
            />
          </n-form-item>
          <n-form-item label="菜单入口" :show-feedback="false">
            <n-input
              v-model:value="form.menu_ids"
              size="small"
              placeholder="逗号分隔，如 ai_assistant,ai_knowledge"
            />
          </n-form-item>
          <n-form-item label="宣称针" :show-feedback="false">
            <n-select
              v-model:value="form.claim_needles"
              size="small"
              multiple
              filterable
              tag
              placeholder="关开关时 README 不得出现"
            />
          </n-form-item>
          <n-form-item label="README 槽" :show-feedback="false">
            <n-select
              v-model:value="form.readme_slot"
              size="small"
              filterable
              clearable
              placeholder="选择 README 占位槽"
              :options="readmeSlotOptions"
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
import { confirm } from '../ui'
import PageSkeleton from '../components/PageSkeleton.vue'

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
  caps: [],
  readme_slot_options: [
    { value: 'AI_ASSISTANT_FAQ', label: 'AI 助手 FAQ' },
    { value: 'SECURITY_FAQ', label: '鉴权 FAQ' },
  ],
})

const form = reactive({
  cap_id: '',
  title_zh: '',
  body_zh: '',
  auth_line_on: '',
  auth_line_off: '',
  backend_suffix: '',
  menu_ids: '',
  claim_needles: [],
  readme_slot: null,
  sort: 0,
})

const identityLocked = computed(() => !!editingId.value || fromGap.value)

const formHint = computed(() => {
  if (identityLocked.value) {
    return editingId.value
      ? '能力 ID 已锁定，可修改正文、菜单与宣称针。更换能力请删除后重新登记。'
      : '待补项标识已锁定，请补全标题与正文后保存。'
  }
  return '开启对应开关时注入 README；宣称针用于关开关时拦截假集成表述。'
})

const readmeSlotOptions = computed(() =>
  meta.readme_slot_options.length
    ? meta.readme_slot_options
    : [
        { value: 'AI_ASSISTANT_FAQ', label: 'AI 助手 FAQ' },
        { value: 'SECURITY_FAQ', label: '鉴权 FAQ' },
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

function resetForm() {
  form.cap_id = ''
  form.title_zh = ''
  form.body_zh = ''
  form.auth_line_on = ''
  form.auth_line_off = ''
  form.backend_suffix = ''
  form.menu_ids = ''
  form.claim_needles = []
  form.readme_slot = null
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
  form.cap_id = row.cap_id || ''
  form.title_zh = row.title_zh || ''
  form.body_zh = row.body_zh || ''
  form.auth_line_on = row.auth_line_on || ''
  form.auth_line_off = row.auth_line_off || ''
  form.backend_suffix = row.backend_suffix || ''
  form.menu_ids = row.menu_ids || ''
  form.claim_needles = Array.isArray(row.claim_needles) ? [...row.claim_needles] : []
  form.readme_slot = row.readme_slot || null
  form.sort = row.sort ?? 0
  drawerOpen.value = true
}

function fillFromGap(g) {
  editingId.value = 0
  fromGap.value = true
  form.cap_id = g.cap_id || ''
  form.title_zh = g.cap_id || ''
  form.body_zh = ''
  form.auth_line_on = ''
  form.auth_line_off = ''
  form.backend_suffix = ''
  form.menu_ids = ''
  form.claim_needles = []
  form.readme_slot = null
  form.sort = 0
  drawerOpen.value = true
}

async function loadMeta() {
  try {
    const res = await api.capCardsMeta()
    meta.caps = res.caps || []
    meta.readme_slot_options = res.readme_slot_options || []
  } catch (e) {
    message.error(e?.message || '加载选项失败')
  }
}

async function load() {
  try {
    const params = {}
    if (q.value) params.q = q.value
    const res = await api.capCards(params)
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
    const res = await api.capCardsMigrate()
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
    const res = await api.capCardsGaps()
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
  if (!form.cap_id?.trim()) {
    message.warning('能力 ID 必填')
    return
  }
  if (!form.body_zh?.trim()) {
    message.warning('请填写 README 正文')
    return
  }
  saving.value = true
  try {
    await api.capCardsUpsert({
      cap_id: form.cap_id.trim(),
      title_zh: (form.title_zh || '').trim(),
      body_zh: form.body_zh,
      auth_line_on: form.auth_line_on || '',
      auth_line_off: form.auth_line_off || '',
      backend_suffix: (form.backend_suffix || '').trim(),
      menu_ids: (form.menu_ids || '').trim(),
      claim_needles: form.claim_needles || [],
      readme_slot: form.readme_slot || '',
      sort: form.sort ?? 0,
      source: 'manual',
    })
    message.success(editingId.value ? '已保存修改' : '已保存')
    drawerOpen.value = false
    resetForm()
    await loadMeta()
    await load()
    if (gapsScanned.value) {
      const gapRes = await api.capCardsGaps()
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
  const ok = await confirm(`删除「${row.cap_id}」说明卡？`, {
    title: '删除说明',
    positiveText: '删除',
  })
  if (!ok) return
  deletingId.value = row.id
  try {
    await api.capCardsDelete(row.id)
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

<style scoped>
.cc-table-wrap {
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
.cc-filter-row {
  gap: 8px;
  flex-wrap: wrap;
  flex: 1;
  min-width: 0;
}
.panel-quiet .panel-hd {
  align-items: flex-start;
}
.cc-drawer-form :deep(.n-form-item) {
  margin-bottom: 10px;
}
</style>
