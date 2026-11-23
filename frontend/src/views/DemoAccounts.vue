<template>
  <div class="page-fill surface-page">
    <div class="surface-toolbar">
      <div>
        <h1 class="page-title">测试账号</h1>
        <p class="page-desc" style="margin-bottom:0">
          维护各端演示账号与登录提示；出包写入 schema.demoAccounts，与演示剧本角色列对齐。
        </p>
      </div>
      <div class="row" style="gap:8px;flex-wrap:wrap">
        <n-button size="small" :loading="gapLoading" @click="scanGaps">检查待补</n-button>
        <n-button
          size="small"
          :loading="migrating"
          title="仅追加缺失项，不覆盖已有记录"
          @click="migrate"
        >导入初始账号</n-button>
        <n-button size="small" type="primary" @click="openCreate">登记账号</n-button>
      </div>
    </div>

    <PageSkeleton v-if="!booted" variant="dashboard" :rows="4" />
    <template v-else>
      <div class="stats mb-12" style="grid-template-columns:repeat(2,1fr);max-width:360px">
        <div class="stat">
          <div class="label">账号</div>
          <div class="value">{{ total }}</div>
        </div>
        <div class="stat">
          <div class="label">待补</div>
          <div class="value" :class="{ bad: gapsScanned && gapCount > 0 }">{{ gapsScanned ? gapCount : '—' }}</div>
        </div>
      </div>

      <n-tabs v-model:value="mainTab" type="line" size="small" class="mb-12" @update:value="onTab">
        <n-tab-pane name="entries" tab="账号" />
        <n-tab-pane name="gaps" tab="待补" />
      </n-tabs>

      <div v-show="mainTab === 'entries'" class="panel panel-quiet">
        <div class="panel-hd">
          <div class="row da-filter-row">
            <n-select
              v-model:value="domain"
              size="small"
              clearable
              placeholder="全部域"
              :options="domainFilterOptions"
              style="width:200px"
              @update:value="reloadFromTop"
            />
            <n-select
              v-model:value="role"
              size="small"
              clearable
              placeholder="全部岗位"
              :options="roleOptions"
              style="width:140px"
              @update:value="reloadFromTop"
            />
            <n-input
              v-model:value="q"
              size="small"
              clearable
              placeholder="用户名 / 昵称 / 提示"
              style="width:200px"
              @keyup.enter="reloadFromTop"
            />
            <n-button size="small" @click="reloadFromTop">查询</n-button>
          </div>
        </div>
        <div class="panel-bd">
          <div v-if="!items.length" class="empty-hint">
            <div class="empty-title">还没有账号</div>
            <div class="empty-desc">用顶栏导入或登记一条。</div>
          </div>
          <template v-else>
            <div class="da-table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>域</th>
                    <th>岗位</th>
                    <th>用户名</th>
                    <th>昵称</th>
                    <th>登录提示</th>
                    <th style="width:100px"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="row in pagedItems"
                    :key="row.id"
                    :class="{ 'is-editing': editingId === row.id }"
                  >
                    <td class="muted">{{ domainLabel(row.domain_id) }}</td>
                    <td>{{ roleLabel(row.role) }}</td>
                    <td class="mono">{{ row.username }}</td>
                    <td>{{ row.nickname_zh || '—' }}</td>
                    <td class="muted">{{ row.login_hint_zh || '—' }}</td>
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
              {{ gapsScanned ? '跨域三端账号已齐。' : '点顶栏「检查待补」扫描缺口。' }}
            </div>
          </div>
          <template v-else>
            <div class="da-table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>域</th>
                    <th>岗位</th>
                    <th>说明</th>
                    <th style="width:100px"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="(g, idx) in pagedGaps"
                    :key="`${g.domain_id}-${g.role}-${idx}`"
                  >
                    <td class="muted">{{ domainLabel(g.domain_id) }}</td>
                    <td>{{ roleLabel(g.role) }}</td>
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
      <n-drawer-content :title="editingId ? '改账号' : '登记账号'" closable>
        <div class="da-drawer-form">
          <n-form-item label="域" :show-feedback="false">
            <n-select
              v-model:value="form.domain_id"
              size="small"
              filterable
              :disabled="identityLocked"
              :options="formDomainOptions"
            />
          </n-form-item>
          <n-form-item label="岗位" :show-feedback="false">
            <n-select
              v-model:value="form.role"
              size="small"
              :disabled="identityLocked"
              :options="roleOptions"
            />
          </n-form-item>
          <n-form-item label="用户名" :show-feedback="false">
            <n-input v-model:value="form.username" size="small" placeholder="如 admin" />
          </n-form-item>
          <n-form-item label="密码" :show-feedback="false">
            <n-input
              v-model:value="form.password"
              size="small"
              type="password"
              show-password-on="click"
              placeholder="演示用明文密码"
            />
          </n-form-item>
          <n-form-item label="昵称" :show-feedback="false">
            <n-input
              v-model:value="form.nickname_zh"
              size="small"
              :maxlength="64"
              show-count
              placeholder="展示名"
            />
          </n-form-item>
          <n-form-item label="登录提示" :show-feedback="false">
            <n-input
              v-model:value="form.login_hint_zh"
              size="small"
              type="textarea"
              :rows="2"
              :maxlength="256"
              show-count
              placeholder="登录页/README 一句提示"
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
const domain = ref(null)
const role = ref(null)
const q = ref('')

const gaps = ref([])
const gapCount = ref(0)
const gapsScanned = ref(false)
const gapPage = ref(1)
const gapPageSize = ref(20)

const meta = reactive({
  domains: [],
  role_options: [
    { value: 'admin', label: '管理端' },
    { value: 'staff', label: '受理端' },
    { value: 'user', label: '用户端' },
  ],
})

const form = reactive({
  domain_id: '*',
  role: 'admin',
  username: '',
  password: '',
  nickname_zh: '',
  login_hint_zh: '',
  sort: 0,
})

const identityLocked = computed(() => !!editingId.value || fromGap.value)

const formHint = computed(() => {
  if (identityLocked.value) {
    return editingId.value
      ? '域与岗位已锁定，可改用户名、密码与提示。更换键请删除后重新登记。'
      : '待补项标识已锁定，请补全用户名与密码后保存。'
  }
  return '具名域优先生效。口令按该端角色说话；演示密码写进学生包 README，勿用真实密钥。'
})

const domainFilterOptions = computed(() =>
  meta.domains.map((d) => ({
    label: domainSelectLabel(d.id),
    value: d.id,
  })),
)

const formDomainOptions = computed(() => domainFilterOptions.value)

const roleOptions = computed(() =>
  meta.role_options.length
    ? meta.role_options
    : [
        { value: 'admin', label: '管理端' },
        { value: 'staff', label: '受理端' },
        { value: 'user', label: '用户端' },
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

function domainLabel(dom) {
  if (!dom || dom === '*') return '跨域壳默认'
  const hit = meta.domains.find((d) => d.id === dom)
  return hit ? hit.name || dom : dom
}

function domainSelectLabel(dom) {
  if (!dom || dom === '*') return '跨域壳默认（*）'
  return `${domainLabel(dom)}（${dom}）`
}

function roleLabel(r) {
  const hit = roleOptions.value.find((o) => o.value === r)
  return hit ? hit.label : r || '—'
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

function resetForm() {
  form.domain_id = '*'
  form.role = 'admin'
  form.username = ''
  form.password = ''
  form.nickname_zh = ''
  form.login_hint_zh = ''
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
  form.domain_id = row.domain_id || '*'
  form.role = row.role || 'admin'
  form.username = row.username || ''
  form.password = row.password || ''
  form.nickname_zh = row.nickname_zh || ''
  form.login_hint_zh = row.login_hint_zh || ''
  form.sort = row.sort ?? 0
  drawerOpen.value = true
}

function fillFromGap(g) {
  editingId.value = 0
  fromGap.value = true
  form.domain_id = g.domain_id || '*'
  form.role = g.role || 'admin'
  form.username = g.role || 'admin'
  form.password = `${g.role || 'admin'}123`
  form.nickname_zh = roleLabel(g.role)
  form.login_hint_zh = ''
  form.sort = 0
  drawerOpen.value = true
}

async function loadMeta() {
  try {
    const res = await api.demoAccountsMeta()
    meta.domains = res.domains || []
    meta.role_options = res.role_options || meta.role_options
  } catch (e) {
    message.error(e?.message || '加载选项失败')
  }
}

async function load() {
  try {
    const params = {}
    if (domain.value !== null && domain.value !== undefined) params.domain_id = domain.value
    if (role.value) params.role = role.value
    if (q.value) params.q = q.value
    const res = await api.demoAccounts(params)
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
    const res = await api.demoAccountsMigrate()
    domain.value = null
    role.value = null
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
    const res = await api.demoAccountsGaps()
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
  if (!form.role || !form.username?.trim() || !form.password?.trim()) {
    message.warning('岗位、用户名与密码都要填')
    return
  }
  saving.value = true
  try {
    await api.demoAccountsUpsert({
      domain_id: form.domain_id || '*',
      role: form.role,
      username: form.username.trim(),
      password: form.password.trim(),
      nickname_zh: (form.nickname_zh || '').trim(),
      login_hint_zh: (form.login_hint_zh || '').trim(),
      sort: form.sort ?? 0,
      source: 'manual',
    })
    message.success(editingId.value ? '已保存修改' : '已保存')
    drawerOpen.value = false
    resetForm()
    await loadMeta()
    await load()
    if (gapsScanned.value) {
      const gapRes = await api.demoAccountsGaps()
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
  const ok = await confirm(`删除「${roleLabel(row.role)} · ${row.username}」？`, {
    title: '删除账号',
    positiveText: '删除',
  })
  if (!ok) return
  deletingId.value = row.id
  try {
    await api.demoAccountsDelete(row.id)
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
.da-table-wrap {
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
.da-filter-row {
  gap: 8px;
  flex-wrap: wrap;
}
.da-drawer-form :deep(.n-form-item) {
  margin-bottom: 10px;
}
</style>
