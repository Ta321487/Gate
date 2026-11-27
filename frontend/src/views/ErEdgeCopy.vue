<template>
  <div class="page-fill surface-page">
    <div class="surface-toolbar">
      <div>
        <h1 class="page-title">表关系叙事</h1>
        <p class="page-desc" style="margin-bottom:0">
          为表与表之间维护一句人话旁注，服务论文「数据库设计」；不替代 E-R 结构对账与几何排版。
        </p>
      </div>
      <AssetDeskActions
        :gap-loading="gapLoading"
        :migrating="migrating"
        create-label="登记叙事"
        @check="scanGaps"
        @migrate="migrate"
        @create="openCreate"
      />
    </div>

    <PageSkeleton v-if="!booted" variant="dashboard" :rows="4" />
    <template v-else>
      <div class="stats mb-12" style="grid-template-columns:repeat(2,1fr);max-width:360px">
        <div class="stat">
          <div class="label">叙事</div>
          <div class="value">{{ total }}</div>
        </div>
        <div class="stat">
          <div class="label">待补</div>
          <div class="value" :class="{ bad: gapsScanned && gapCount > 0 }">{{ gapStatDisplay(gapsScanned, gapCount) }}</div>
        </div>
      </div>

      <n-tabs v-model:value="mainTab" type="line" size="small" class="mb-12">
        <n-tab-pane name="entries" tab="叙事" />
        <n-tab-pane name="gaps" tab="待补" />
      </n-tabs>

      <div v-show="mainTab === 'entries'" class="panel panel-quiet">
        <div class="panel-hd">
          <div class="row asset-desk-filter-row">
            <n-input
              v-model:value="q"
              size="small"
              clearable
              placeholder="表名 / 叙事句"
              style="width:240px"
              @keyup.enter="reloadFromTop"
            />
            <n-button size="small" @click="reloadFromTop">查询</n-button>
          </div>
        </div>
        <div class="panel-bd">
          <div v-if="!items.length" class="empty-hint">
            <div class="empty-title">还没有叙事</div>
            <div class="empty-desc">用顶栏导入或登记一条。</div>
          </div>
          <template v-else>
            <div class="asset-desk-table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>表 A</th>
                    <th>表 B</th>
                    <th>叙事句</th>
                    <th style="width:100px"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="row in pagedItems"
                    :key="row.id"
                    :class="{ 'is-editing': editingId === row.id }"
                  >
                    <td class="mono">{{ row.table_a }}</td>
                    <td class="mono">{{ row.table_b }}</td>
                    <td>{{ row.sentence_zh || '—' }}</td>
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
              {{ gapsScanned ? '种子叙事已齐。' : '点顶栏「检查待补」扫描缺口。' }}
            </div>
          </div>
          <template v-else>
            <div class="asset-desk-table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>表 A</th>
                    <th>表 B</th>
                    <th>说明</th>
                    <th style="width:100px"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="(g, idx) in pagedGaps"
                    :key="`${g.table_a}-${g.table_b}-${idx}`"
                  >
                    <td class="mono">{{ g.table_a }}</td>
                    <td class="mono">{{ g.table_b }}</td>
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
      <n-drawer-content :title="editingId ? '改叙事' : '登记叙事'" closable>
        <div class="asset-desk-drawer-form">
          <n-form-item label="表 A" :show-feedback="false">
            <n-select
              v-model:value="form.table_a"
              size="small"
              filterable
              tag
              :disabled="identityLocked"
              :options="tableOptions"
              placeholder="如 biz_order"
            />
          </n-form-item>
          <n-form-item label="表 B" :show-feedback="false">
            <n-select
              v-model:value="form.table_b"
              size="small"
              filterable
              tag
              :disabled="identityLocked"
              :options="tableOptions"
              placeholder="如 biz_order_item"
            />
          </n-form-item>
          <n-form-item label="叙事句" :show-feedback="false">
            <n-input
              v-model:value="form.sentence_zh"
              size="small"
              type="textarea"
              :rows="3"
              :maxlength="sentenceMax"
              show-count
              placeholder="一句人话，如：一笔订单包含多条明细。"
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
const q = ref('')

const gaps = ref([])
const gapCount = ref(0)
const gapsScanned = ref(false)
const gapPage = ref(1)
const gapPageSize = ref(20)

const meta = reactive({
  table_options: [],
  sentence_max: 256,
})

const form = reactive({
  table_a: '',
  table_b: '',
  sentence_zh: '',
  sort: 0,
})

const identityLocked = computed(() => !!editingId.value || fromGap.value)
const sentenceMax = computed(() => meta.sentence_max || 256)

const formHint = computed(() => {
  if (identityLocked.value) {
    return editingId.value
      ? '表对已锁定，可改叙事句。更换表对请删除后重新登记。'
      : '待补项表对已锁定，请补全叙事句后保存。'
  }
  return '出包写入 schema.erEdgeCopy；供论文库设旁注。几何排版仍归论文图债，本台只管人话。'
})

const tableOptions = computed(() => {
  const set = new Set((meta.table_options || []).map((o) => o.value || o))
  if (form.table_a) set.add(form.table_a)
  if (form.table_b) set.add(form.table_b)
  return [...set].sort().map((t) => ({ label: t, value: t }))
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
  form.table_a = ''
  form.table_b = ''
  form.sentence_zh = ''
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
  form.table_a = row.table_a || ''
  form.table_b = row.table_b || ''
  form.sentence_zh = row.sentence_zh || ''
  form.sort = row.sort ?? 0
  drawerOpen.value = true
}

function fillFromGap(g) {
  editingId.value = 0
  fromGap.value = true
  form.table_a = g.table_a || ''
  form.table_b = g.table_b || ''
  form.sentence_zh = ''
  form.sort = 0
  drawerOpen.value = true
}

async function loadMeta() {
  try {
    const res = await api.erEdgeCopyMeta()
    meta.table_options = res.table_options || []
    meta.sentence_max = res.sentence_max || 256
  } catch (e) {
    toastApiError(e, '加载选项失败')
  }
}

async function load() {
  try {
    const params = {}
    if (q.value) params.q = q.value
    const res = await api.erEdgeCopy(params)
    items.value = res.items || []
    total.value = res.total ?? items.value.length
    const maxPage = Math.max(1, Math.ceil((total.value || 0) / pageSize.value) || 1)
    if (page.value > maxPage) page.value = maxPage
  } catch (e) {
    toastApiError(e, '加载失败')
  } finally {
    booted.value = true
  }
}

async function migrate() {
  migrating.value = true
  try {
    const res = await api.erEdgeCopyMigrate()
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
    const res = await api.erEdgeCopyGaps()
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

async function save() {
  if (!form.table_a?.trim() || !form.table_b?.trim() || !form.sentence_zh?.trim()) {
    message.warning('表 A、表 B 与叙事句都要填')
    return
  }
  saving.value = true
  try {
    await api.erEdgeCopyUpsert({
      table_a: form.table_a.trim(),
      table_b: form.table_b.trim(),
      sentence_zh: form.sentence_zh.trim(),
      sort: form.sort ?? 0,
      source: 'manual',
    })
    message.success(editingId.value ? '已保存修改' : '已保存')
    drawerOpen.value = false
    resetForm()
    await loadMeta()
    await load()
    if (gapsScanned.value) {
      const gapRes = await api.erEdgeCopyGaps()
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
  const ok = await confirm(`删除「${row.table_a} → ${row.table_b}」？`, {
    title: '删除叙事',
    positiveText: '删除',
  })
  if (!ok) return
  deletingId.value = row.id
  try {
    await api.erEdgeCopyDelete(row.id)
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

