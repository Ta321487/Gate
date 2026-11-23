<template>
  <div class="page-fill surface-page">
    <div class="surface-toolbar">
      <div>
        <h1 class="page-title">错误码中文</h1>
        <p class="page-desc" style="margin-bottom:0">
          维护业务错误码的默认中文；出包写入学生包，空消息时回落本台文案。
        </p>
      </div>
      <div class="row" style="gap:8px;flex-wrap:wrap">
        <n-button size="small" :loading="gapLoading" @click="scanGaps">检查待补</n-button>
        <n-button
          size="small"
          :loading="migrating"
          title="仅追加缺失项，不覆盖已有记录"
          @click="migrate"
        >导入初始错误码</n-button>
        <n-button size="small" type="primary" @click="openCreate">登记错误码</n-button>
      </div>
    </div>

    <PageSkeleton v-if="!booted" variant="dashboard" :rows="4" />
    <template v-else>
      <div class="stats mb-12" style="grid-template-columns:repeat(2,1fr);max-width:360px">
        <div class="stat">
          <div class="label">错误码</div>
          <div class="value">{{ total }}</div>
        </div>
        <div class="stat">
          <div class="label">待补</div>
          <div class="value" :class="{ bad: gapsScanned && gapCount > 0 }">{{ gapsScanned ? gapCount : '—' }}</div>
        </div>
      </div>

      <n-tabs v-model:value="mainTab" type="line" size="small" class="mb-12" @update:value="onTab">
        <n-tab-pane name="entries" tab="错误码" />
        <n-tab-pane name="gaps" tab="待补" />
      </n-tabs>

      <div v-show="mainTab === 'entries'" class="panel panel-quiet">
        <div class="panel-hd">
          <div class="row ec-filter-row">
            <n-input
              v-model:value="q"
              size="small"
              clearable
              placeholder="码名 / 中文 / 数字码"
              style="width:240px"
              @keyup.enter="reloadFromTop"
            />
            <n-button size="small" @click="reloadFromTop">查询</n-button>
          </div>
        </div>
        <div class="panel-bd">
          <div v-if="!items.length" class="empty-hint">
            <div class="empty-title">还没有错误码</div>
            <div class="empty-desc">用顶栏导入或登记一条。</div>
          </div>
          <template v-else>
            <div class="ec-table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>错误码</th>
                    <th>数字码</th>
                    <th>中文</th>
                    <th style="width:100px"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="row in pagedItems"
                    :key="row.id"
                    :class="{ 'is-editing': editingId === row.id }"
                  >
                    <td class="mono">{{ row.error_code }}</td>
                    <td class="mono muted">{{ row.code_num }}</td>
                    <td>{{ row.message_zh }}</td>
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
              {{ gapsScanned ? '基线错误码均已覆盖。' : '点顶栏「检查待补」扫描缺口。' }}
            </div>
          </div>
          <template v-else>
            <div class="ec-table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>错误码</th>
                    <th>说明</th>
                    <th style="width:100px"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="g in pagedGaps" :key="g.error_code">
                    <td class="mono">{{ g.error_code }}</td>
                    <td>{{ g.reason || '缺少默认中文' }}</td>
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

    <n-drawer v-model:show="drawerOpen" :width="400" placement="right" @after-leave="onDrawerLeave">
      <n-drawer-content :title="editingId ? '改错误码' : '登记错误码'" closable>
        <div class="ec-drawer-form">
          <n-form-item label="错误码" :show-feedback="false">
            <n-select
              v-model:value="form.error_code"
              size="small"
              filterable
              tag
              :disabled="identityLocked"
              :options="codeOptions"
              placeholder="如 BAD_REQUEST"
            />
          </n-form-item>
          <n-form-item label="数字码" :show-feedback="false">
            <n-input-number v-model:value="form.code_num" size="small" :min="0" style="width:100%" />
          </n-form-item>
          <n-form-item label="中文" :show-feedback="false">
            <n-input
              v-model:value="form.message_zh"
              size="small"
              :maxlength="128"
              show-count
              placeholder="学生可见默认句"
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

const meta = reactive({ expected: [] })

const form = reactive({
  error_code: 'BAD_REQUEST',
  code_num: 40000,
  message_zh: '',
  sort: 0,
})

const identityLocked = computed(() => !!editingId.value || fromGap.value)

const formHint = computed(() => {
  if (identityLocked.value) {
    return editingId.value
      ? '错误码已锁定，可修改中文与数字码。更换错误码请删除后重新登记。'
      : '待补项标识已锁定，请补全中文后保存。'
  }
  return '接口已带具体说明时优先生效；空消息时回落本台默认中文。与工厂失败码不是同一套。'
})

const codeOptions = computed(() => {
  const list = meta.expected.length
    ? meta.expected
    : [{ id: 'BAD_REQUEST', label: 'BAD_REQUEST', code_num: 40000 }]
  return list.map((c) => ({
    label: `${c.id}（${c.code_num}）`,
    value: c.id,
  }))
})

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
  const first = meta.expected[0]
  form.error_code = first?.id || 'BAD_REQUEST'
  form.code_num = first?.code_num ?? 40000
  form.message_zh = ''
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
  form.error_code = row.error_code || ''
  form.code_num = row.code_num ?? 0
  form.message_zh = row.message_zh || ''
  form.sort = row.sort ?? 0
  drawerOpen.value = true
}

function fillFromGap(g) {
  editingId.value = 0
  fromGap.value = true
  form.error_code = g.error_code || ''
  form.code_num = g.code_num ?? 0
  form.message_zh = ''
  form.sort = 0
  drawerOpen.value = true
}

async function loadMeta() {
  try {
    const res = await api.errorCopyMeta()
    meta.expected = res.expected || res.codes || []
  } catch (e) {
    message.error(e?.message || '加载选项失败')
  }
}

async function load() {
  try {
    const params = {}
    if (q.value) params.q = q.value
    const res = await api.errorCopy(params)
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
    const res = await api.errorCopyMigrate()
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
    const res = await api.errorCopyGaps()
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
  if (!form.error_code?.trim() || !form.message_zh?.trim()) {
    message.warning('错误码与中文都要填')
    return
  }
  saving.value = true
  try {
    await api.errorCopyUpsert({
      error_code: form.error_code.trim(),
      message_zh: form.message_zh.trim(),
      code_num: form.code_num ?? 0,
      sort: form.sort ?? 0,
      source: 'manual',
    })
    message.success(editingId.value ? '已保存修改' : '已保存')
    drawerOpen.value = false
    resetForm()
    await loadMeta()
    await load()
    if (gapsScanned.value) {
      const gapRes = await api.errorCopyGaps()
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
  const ok = await confirm(`删除「${row.error_code} → ${row.message_zh}」？`, {
    title: '删除错误码',
    positiveText: '删除',
  })
  if (!ok) return
  deletingId.value = row.id
  try {
    await api.errorCopyDelete(row.id)
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
.ec-table-wrap {
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
.ec-filter-row {
  gap: 8px;
  flex-wrap: wrap;
}
.ec-drawer-form :deep(.n-form-item) {
  margin-bottom: 10px;
}
</style>
