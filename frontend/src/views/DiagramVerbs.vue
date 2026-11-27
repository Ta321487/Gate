<template>
  <div class="page-fill surface-page">
    <div class="surface-toolbar">
      <div>
        <h1 class="page-title">实体动作词</h1>
        <p class="page-desc" style="margin-bottom:0">
          域 × 实体 × 动作 → 中文动作。论文图内业务动词的唯一词源：材料 entities.verbs 优先，本台为缺省与跨域默认；图内不再自带业务词。
        </p>
      </div>
      <AssetDeskActions
        :gap-loading="gapLoading"
        :migrating="migrating"
        create-label="登记动作词"
        @check="scanGaps"
        @migrate="migrate"
        @create="openCreate"
      />
    </div>

    <template v-if="booted">
      <div class="stats mb-12" style="grid-template-columns:repeat(2,1fr);max-width:360px">
        <div class="stat">
          <div class="label">动作词</div>
          <div class="value">{{ total }}</div>
        </div>
        <div class="stat">
          <div class="label">待补</div>
          <div class="value" :class="{ bad: gapsScanned && gapCount > 0 }">{{ gapStatDisplay(gapsScanned, gapCount) }}</div>
        </div>
      </div>

      <n-tabs v-model:value="mainTab" type="line" size="small" class="mb-12">
        <n-tab-pane name="entries" tab="动作词" />
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
              :options="domainOptions"
              style="width:220px"
              :consistent-menu-width="false"
              :menu-props="{ style: { minWidth: '320px' } }"
              @update:value="reloadFromTop"
            />
            <n-select
              v-model:value="verbKey"
              size="small"
              clearable
              placeholder="全部动作"
              :options="verbOptions"
              style="width:180px"
              @update:value="reloadFromTop"
            />
            <n-input
              v-model:value="q"
              size="small"
              clearable
              placeholder="实体 / 中文动作"
              style="width:180px"
              @keyup.enter="reloadFromTop"
            />
            <n-button size="small" @click="reloadFromTop">查询</n-button>
          </div>
        </div>
        <div class="panel-bd">
          <div v-if="!items.length" class="empty-hint">
            <div class="empty-title">还没有动作词</div>
            <div class="empty-desc">顶栏「导入种子」会按 67 个域的材料补齐。</div>
          </div>
          <template v-else>
            <div class="asset-desk-table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>域</th>
                    <th>实体</th>
                    <th>动作键</th>
                    <th>中文动作</th>
                    <th style="width:100px"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in pagedItems" :key="row.id" :class="{ 'is-editing': editingId === row.id && drawerOpen }">
                    <td class="muted">{{ domainLabel(row.domain_id) }}</td>
                    <td>{{ row.entity_key }}</td>
                    <td class="muted">{{ row.verb_key }}</td>
                    <td>{{ row.action_zh }}</td>
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
        <div class="panel-hd row" style="justify-content:space-between">
          <span class="small muted">材料与工厂都没有该动作词 → 图内只能出骨架句。</span>
          <n-button size="small" :loading="gapLoading" @click="scanGaps">重扫</n-button>
        </div>
        <div class="panel-bd">
          <div v-if="gapsScanned && !gaps.length" class="empty-hint">
            <div class="empty-title">没有待补</div>
            <div class="empty-desc">已知实体都齐了。</div>
          </div>
          <div v-else-if="!gapsScanned" class="empty-hint">
            <div class="empty-desc">点「重扫」查看缺词。</div>
          </div>
          <div v-else class="asset-desk-table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <th>域</th>
                  <th>实体</th>
                  <th>动作键</th>
                  <th>说明</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(g, i) in pagedGaps" :key="i">
                  <td class="muted">{{ domainLabel(g.domain_id) }}</td>
                  <td>{{ g.entity_key }}</td>
                  <td class="muted">{{ g.verb_key }}</td>
                  <td class="small muted">{{ g.reason }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-if="gaps.length > gapPageSize" class="pager-row">
            <span class="small muted">共 {{ gaps.length }} 条</span>
            <n-pagination
              v-model:page="gapPage"
              v-model:page-size="gapPageSize"
              :item-count="gaps.length"
              :page-sizes="[10, 20, 50]"
              show-size-picker
              size="small"
            />
          </div>
        </div>
      </div>
    </template>

    <n-drawer v-model:show="drawerOpen" :width="420" placement="right">
      <n-drawer-content :title="editingId ? '修改动作词' : '登记动作词'" closable>
        <n-form label-placement="top" size="small">
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
          <n-form-item label="实体键" :show-feedback="false">
            <n-input v-model:value="form.entity_key" size="small" :disabled="identityLocked" placeholder="order / ticket / review" />
          </n-form-item>
          <n-form-item label="动作键" :show-feedback="false">
            <n-input
              v-model:value="form.verb_key"
              size="small"
              :disabled="identityLocked"
              placeholder="ship / complete / apply"
            />
          </n-form-item>
          <n-form-item label="中文动作" :show-feedback="false">
            <n-input v-model:value="form.action_zh" size="small" :maxlength="32" show-count placeholder="出票 / 确认观演 / 送达" />
          </n-form-item>
          <p class="small muted">{{ formHint }}</p>
          <div class="row" style="gap:8px;justify-content:flex-end;margin-top:12px">
            <n-button size="small" @click="closeDrawer">退出编辑</n-button>
            <n-button size="small" type="primary" :loading="saving" @click="save">保存</n-button>
          </div>
        </n-form>
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { api, message, toastApiError } from '../api'
import { gapStatDisplay } from '../utils/assetDesk'
import AssetDeskActions from '../components/AssetDeskActions.vue'
import { confirm } from '../ui'

const booted = ref(false)
const migrating = ref(false)
const gapLoading = ref(false)
const saving = ref(false)
const deletingId = ref(0)
const editingId = ref(0)
const drawerOpen = ref(false)
const mainTab = ref('entries')
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const domain = ref(null)
const verbKey = ref(null)
const q = ref('')
const gaps = ref([])
const gapCount = ref(0)
const gapsScanned = ref(false)
const gapPage = ref(1)
const gapPageSize = ref(20)

const meta = reactive({ domains: [], verb_keys: [], flow: [] })
const form = reactive({ domain_id: '*', entity_key: '', verb_key: '', action_zh: '' })

const identityLocked = computed(() => !!editingId.value)

const formHint = computed(() => {
  if (identityLocked.value) return '域 / 实体 / 动作键已锁定，可改中文动作。更换请删除后重新登记。'
  return '材料 entities.verbs 有词时优先生效；此表只在该域材料缺词时兜底。'
})

const domainOptions = computed(() =>
  meta.domains.map((d) => ({
    label: d.id === '*' ? '跨域壳默认' : `${d.name || d.id}（${d.id}）`,
    value: d.id,
  })),
)

const verbOptions = computed(() => meta.verb_keys.map((v) => ({ label: `${v.label_zh}（${v.verb_key}）`, value: v.verb_key })))

const pagedItems = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return items.value.slice(start, start + pageSize.value)
})

const pagedGaps = computed(() => {
  const start = (gapPage.value - 1) * gapPageSize.value
  return gaps.value.slice(start, start + gapPageSize.value)
})

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

async function reload() {
  const params = {}
  if (domain.value) params.domain_id = domain.value
  if (verbKey.value) params.verb_key = verbKey.value
  if (q.value) params.q = q.value
  const res = await api.diagramVerbs(params)
  items.value = res.items || []
  total.value = res.total || 0
}

async function loadMeta() {
  const res = await api.diagramVerbsMeta()
  meta.domains = res.domains || []
  meta.verb_keys = res.verb_keys || []
  meta.flow = res.flow || []
}

async function migrate() {
  migrating.value = true
  try {
    const res = await api.diagramVerbsMigrate()
    message.success(`补齐 ${res.inserted} 条，共 ${res.total} 条`)
    await reload()
  } finally {
    migrating.value = false
  }
}

async function scanGaps() {
  gapLoading.value = true
  try {
    const res = await api.diagramVerbsGaps()
    const reports = res.reports || []
    gaps.value = reports.flatMap((r) => (r.gaps || []).map((g) => ({ ...g, domain_id: r.domain_id })))
    gapCount.value = gaps.value.length
    gapsScanned.value = true
  } finally {
    gapLoading.value = false
  }
}

function openCreate() {
  editingId.value = 0
  form.domain_id = '*'
  form.entity_key = ''
  form.verb_key = ''
  form.action_zh = ''
  drawerOpen.value = true
}

function editRow(row) {
  editingId.value = row.id
  form.domain_id = row.domain_id
  form.entity_key = row.entity_key
  form.verb_key = row.verb_key
  form.action_zh = row.action_zh
  drawerOpen.value = true
}

function closeDrawer() {
  drawerOpen.value = false
  editingId.value = 0
}

async function save() {
  if (!form.entity_key.trim()) return message.warning('实体键必填')
  if (!form.verb_key.trim()) return message.warning('动作键必填')
  if (!form.action_zh.trim()) return message.warning('中文动作必填')
  saving.value = true
  try {
    await api.diagramVerbsUpsert({
      domain_id: form.domain_id || '*',
      entity_key: form.entity_key.trim(),
      verb_key: form.verb_key.trim(),
      action_zh: form.action_zh.trim(),
      source: 'manual',
    })
    message.success('已保存')
    closeDrawer()
    await reload()
  } catch (e) {
    toastApiError(e, '保存失败')
  } finally {
    saving.value = false
  }
}

async function remove(row) {
  const ok = await confirm(`删除「${row.entity_key}.${row.verb_key}」？`, {
    title: '删除动作词',
    positiveText: '删除',
  })
  if (!ok) return
  deletingId.value = row.id
  try {
    await api.diagramVerbsDelete(row.id)
    message.success('已删除')
    await reload()
  } finally {
    deletingId.value = 0
  }
}

onMounted(async () => {
  await loadMeta()
  await reload()
  booted.value = true
})
</script>

