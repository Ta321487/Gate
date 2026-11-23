<template>
  <div class="page-fill surface-page">
    <div class="surface-toolbar">
      <div>
        <h1 class="page-title">论文图题</h1>
        <p class="page-desc" style="margin-bottom:0">
          图种 × 域 → 标题模板（占位符 name）；出包写入 schema.diagramTitleTemplates。几何排版仍归论文图债，不在本台。
        </p>
      </div>
      <div class="row" style="gap:8px;flex-wrap:wrap">
        <n-button size="small" :loading="gapLoading" @click="scanGaps">检查待补</n-button>
        <n-button
          size="small"
          :loading="migrating"
          title="仅追加缺失项，不覆盖已有记录"
          @click="migrate"
        >导入种子</n-button>
        <n-button size="small" type="primary" @click="openCreate">登记图题</n-button>
      </div>
    </div>

    <PageSkeleton v-if="!booted" variant="dashboard" :rows="4" />
    <template v-else>
      <div class="stats mb-12" style="grid-template-columns:repeat(2,1fr);max-width:360px">
        <div class="stat">
          <div class="label">模板</div>
          <div class="value">{{ total }}</div>
        </div>
        <div class="stat">
          <div class="label">待补</div>
          <div class="value" :class="{ bad: gapCount > 0 }">{{ gapCount }}</div>
        </div>
      </div>

      <n-tabs v-model:value="mainTab" type="line" size="small" class="mb-12">
        <n-tab-pane name="entries" tab="模板" />
        <n-tab-pane name="gaps" tab="待补" />
      </n-tabs>

      <div v-show="mainTab === 'entries'" class="panel panel-quiet">
        <div class="panel-hd">
          <div class="row" style="gap:8px;flex-wrap:wrap">
            <n-select
              v-model:value="kind"
              size="small"
              clearable
              placeholder="全部图种"
              :options="kindOptions"
              style="width:160px"
              @update:value="reload"
            />
            <n-select
              v-model:value="domain"
              size="small"
              clearable
              placeholder="全部域"
              :options="domainOptions"
              style="width:200px"
              @update:value="reload"
            />
            <n-input
              v-model:value="q"
              size="small"
              clearable
              placeholder="模板 / 图种"
              style="width:180px"
              @keyup.enter="reload"
            />
            <n-button size="small" @click="reload">查询</n-button>
          </div>
        </div>
        <div class="panel-bd">
          <div v-if="!items.length" class="empty-hint">
            <div class="empty-title">还没有模板</div>
            <div class="empty-desc">用顶栏导入或登记一条。</div>
          </div>
          <table v-else class="data-table">
            <thead>
              <tr>
                <th>图种</th>
                <th>域</th>
                <th>标题模板</th>
                <th style="width:100px"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in items" :key="row.id">
                <td>{{ kindLabel(row.diagram_kind) }}</td>
                <td class="muted">{{ domainLabel(row.domain_id) }}</td>
                <td class="mono">{{ row.title_tpl }}</td>
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
      </div>

      <div v-show="mainTab === 'gaps'" class="panel panel-quiet">
        <div class="panel-bd">
          <div v-if="!gaps.length" class="empty-hint">
            <div class="empty-title">{{ gapsScanned ? '没有待补项' : '还没检查过' }}</div>
          </div>
          <table v-else class="data-table">
            <thead>
              <tr>
                <th>图种</th>
                <th>域</th>
                <th>说明</th>
                <th style="width:80px"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(g, idx) in gaps" :key="`${g.diagram_kind}-${g.domain_id}-${idx}`">
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
      </div>
    </template>

    <n-drawer v-model:show="drawerOpen" :width="420" placement="right">
      <n-drawer-content :title="editingId ? '改图题' : '登记图题'" closable>
        <n-form-item label="图种" :show-feedback="false">
          <n-select
            v-model:value="form.diagram_kind"
            size="small"
            :disabled="!!editingId"
            :options="kindOptions"
          />
        </n-form-item>
        <n-form-item label="域" :show-feedback="false">
          <n-select
            v-model:value="form.domain_id"
            size="small"
            filterable
            :disabled="!!editingId"
            :options="domainOptions"
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
        <p class="small muted">占位符 name（花括号包裹）= 系统名或功能名；具名域覆盖 *。</p>
        <div class="row" style="gap:8px;justify-content:flex-end;margin-top:12px">
          <n-button size="small" @click="drawerOpen = false">取消</n-button>
          <n-button size="small" type="primary" :loading="saving" @click="save">保存</n-button>
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
const drawerOpen = ref(false)
const mainTab = ref('entries')
const items = ref([])
const total = ref(0)
const kind = ref(null)
const domain = ref(null)
const q = ref('')
const gaps = ref([])
const gapCount = ref(0)
const gapsScanned = ref(false)

const meta = reactive({ domains: [], kind_options: [] })
const form = reactive({
  diagram_kind: 'class',
  domain_id: '*',
  title_tpl: '',
  sort: 0,
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

function kindLabel(k) {
  const hit = kindOptions.value.find((o) => o.value === k)
  return hit ? hit.label : k
}

function domainLabel(id) {
  if (!id || id === '*') return '跨域壳默认'
  const hit = meta.domains.find((d) => d.id === id)
  return hit ? hit.name || id : id
}

async function loadMeta() {
  const res = await api.diagramTitlesMeta()
  meta.domains = res.domains || []
  meta.kind_options = res.kind_options || []
}

async function reload() {
  const params = {}
  if (kind.value) params.diagram_kind = kind.value
  if (domain.value != null) params.domain_id = domain.value
  if (q.value) params.q = q.value
  const res = await api.diagramTitles(params)
  items.value = res.items || []
  total.value = res.total || 0
}

async function scanGaps() {
  gapLoading.value = true
  try {
    const res = await api.diagramTitlesGaps()
    gaps.value = res.gaps || []
    gapCount.value = res.gap_count || 0
    gapsScanned.value = true
    mainTab.value = 'gaps'
  } catch (e) {
    message.error(e?.message || '检查失败')
  } finally {
    gapLoading.value = false
  }
}

async function migrate() {
  migrating.value = true
  try {
    const res = await api.diagramTitlesMigrate()
    message.success(`已补 ${res.inserted || 0} 条，合计 ${res.total || 0}`)
    await reload()
  } catch (e) {
    message.error(e?.message || '导入失败')
  } finally {
    migrating.value = false
  }
}

function openCreate() {
  editingId.value = 0
  form.diagram_kind = 'class'
  form.domain_id = '*'
  form.title_tpl = '{name}类图'
  form.sort = 0
  drawerOpen.value = true
}

function editRow(row) {
  editingId.value = row.id
  form.diagram_kind = row.diagram_kind
  form.domain_id = row.domain_id
  form.title_tpl = row.title_tpl
  form.sort = row.sort || 0
  drawerOpen.value = true
}

function fillFromGap(g) {
  editingId.value = 0
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
    message.success('已保存')
    drawerOpen.value = false
    await reload()
  } catch (e) {
    message.error(e?.response?.data?.detail || e?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function remove(row) {
  const ok = await confirm({ title: '删除模板', content: `删除「${row.title_tpl}」？` })
  if (!ok) return
  deletingId.value = row.id
  try {
    await api.diagramTitlesDelete(row.id)
    message.success('已删除')
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
