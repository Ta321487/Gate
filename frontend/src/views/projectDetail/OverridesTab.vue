<template>
  <div class="overrides-tab">
    <div class="banner">
      <h4>出包微调</h4>
      <p class="small muted">
        此处只改展示文字与材料勾选。结构大改请回匹配并重 bake；重 bake 后本页补丁会自动叠回。
      </p>
    </div>

    <div class="toolbar">
      <span class="small muted">
        <template v-if="loaded">已保存 · v{{ version }}</template>
        <template v-else>加载中…</template>
        <template v-if="dirty"> · <span class="dirty-dot">未保存更改</span></template>
        <template v-if="staleCount">
          ·
          <a href="#" class="stale-link" @click.prevent="selectSection('stale')">
            {{ staleCount }} 条失效
          </a>
        </template>
      </span>
      <div class="toolbar-actions">
        <n-button size="small" quaternary :loading="loading" @click="reload">刷新</n-button>
        <n-button
          size="small"
          :loading="saving"
          :disabled="!dirty"
          @click="saveOnly"
        >
          保存
        </n-button>
        <n-button
          type="primary"
          size="small"
          :loading="saving"
          :disabled="!dirty && !loaded"
          @click="saveAndPreview"
        >
          保存并预览
        </n-button>
      </div>
    </div>

    <n-alert v-if="!p?.workspace_path" type="warning" :bordered="false" style="margin-bottom:12px">
      尚无工作区：可先改草稿；生成工程后才会叠到材料图。
    </n-alert>

    <div class="grid-overrides">
      <aside class="ov-nav">
        <button
          v-for="item in navItems"
          :key="item.id"
          type="button"
          class="ov-nav-item"
          :class="{ active: section === item.id, warn: item.id === 'stale' && staleCount }"
          @click="selectSection(item.id)"
        >
          {{ item.label }}
          <span v-if="item.id === 'stale' && staleCount" class="nav-badge">{{ staleCount }}</span>
        </button>
      </aside>

      <section v-if="section === 'modules'" class="ov-main panel">
        <div class="panel-hd">
          <h3>功能模块图 · 短签</h3>
          <n-button text size="small" :disabled="!p?.workspace_path" @click="openModulesPreview">
            预览
          </n-button>
        </div>
        <div class="panel-bd">
          <div class="table-tools">
            <n-input
              v-model:value="moduleQuery"
              size="small"
              clearable
              placeholder="搜索位置 / 原词 / 手调…"
              style="max-width: 240px"
            />
            <n-select
              v-model:value="moduleBranch"
              size="small"
              clearable
              placeholder="按枝筛选"
              :options="moduleBranchOptions"
              style="width: 140px"
            />
            <n-checkbox v-model:checked="moduleLeavesOnly">只看叶子</n-checkbox>
            <span class="small muted">{{ filteredModuleRows.length }} / {{ moduleRows.length }}</span>
          </div>
          <p class="small muted tip-line">
            {{ handEditTip }}「图上隐藏」只藏论文图，不影响包内菜单。
          </p>
          <n-data-table
            size="small"
            :columns="moduleColumns"
            :data="filteredModuleRows"
            :bordered="false"
            :single-line="false"
            :loading="loading"
            :max-height="480"
            :row-class-name="moduleRowClass"
          />
        </div>
      </section>

      <section v-else-if="section === 'sequence' || section === 'activity'" class="ov-main panel">
        <div class="panel-hd">
          <h3>{{ section === 'sequence' ? '系统序列图' : '系统活动图' }}</h3>
          <n-button text size="small" :disabled="!p?.workspace_path" @click="openDiagramPreview">
            打开图（改勾选）
          </n-button>
        </div>
        <div class="panel-bd">
          <div class="table-tools">
            <n-input
              v-model:value="labelQuery"
              size="small"
              clearable
              placeholder="搜索短签…"
              style="max-width: 220px"
            />
            <span class="small muted">
              已勾选 {{ diagramSelected.length || 0 }} 张
              <template v-if="diagramSelected.length">
                ·
                <code v-for="id in diagramSelected" :key="id" class="sel-chip">{{ id }}</code>
              </template>
            </span>
          </div>
          <p class="small muted tip-line">
            {{ handEditTip }}本表改消息 / 角色短签；换哪几张请点右上角打开图勾选（松手自动写入）。
          </p>
          <n-data-table
            size="small"
            :columns="labelColumns"
            :data="filteredLabelRows"
            :bordered="false"
            :single-line="false"
            :loading="diagLoading"
            :max-height="420"
          />
        </div>
      </section>

      <section v-else-if="section === 'architecture'" class="ov-main panel">
        <div class="panel-hd">
          <h3>系统逻辑架构图 · 显示名</h3>
          <n-button text size="small" :disabled="!p?.workspace_path" :loading="archLoading" @click="loadArchitectureRows">
            重新拉取
          </n-button>
        </div>
        <div class="panel-bd">
          <p class="small muted tip-line">{{ handEditTip }}改角色框 / 层名显示。</p>
          <n-data-table
            size="small"
            :columns="archColumns"
            :data="archRows"
            :bordered="false"
            :loading="archLoading"
            :max-height="420"
          />
        </div>
      </section>

      <section v-else-if="section === 'classes'" class="ov-main panel">
        <div class="panel-hd">
          <h3>系统类图</h3>
          <n-button text size="small" :disabled="!p?.workspace_path" @click="openClassesPreview">
            打开类图调位置
          </n-button>
        </div>
        <div class="panel-bd">
          <div class="table-tools">
            <n-input
              v-model:value="classQuery"
              size="small"
              clearable
              placeholder="搜索类名…"
              style="max-width: 220px"
            />
            <n-button size="tiny" quaternary :loading="classLoading" @click="loadClassRows">重新拉取</n-button>
          </div>
          <p class="small muted tip-line">{{ handEditTip }}拖框请用现有类图画布；本表只改中文显示名。</p>
          <n-data-table
            size="small"
            :columns="classColumns"
            :data="filteredClassRows"
            :bordered="false"
            :loading="classLoading"
            :max-height="420"
          />
        </div>
      </section>

      <section v-else-if="section === 'usecase'" class="ov-main panel">
        <div class="panel-hd">
          <h3>用例图 · 短签与隐藏</h3>
          <n-button text size="small" :disabled="!p?.workspace_path" :loading="ucDiagramLoading" @click="loadUsecaseRows">
            重新拉取
          </n-button>
        </div>
        <div class="panel-bd">
          <p class="small muted tip-line">{{ handEditTip }}图面隐藏不影响菜单。</p>
          <n-data-table
            size="small"
            :columns="ucDiagramColumns"
            :data="ucDiagramRows"
            :bordered="false"
            :loading="ucDiagramLoading"
            :max-height="420"
          />
        </div>
      </section>

      <section v-else-if="section === 'testcases'" class="ov-main panel">
        <div class="panel-hd">
          <h3>软件测试用例</h3>
          <n-button text size="small" :disabled="!p?.workspace_path" :loading="tcLoading" @click="loadTestcaseRows">
            重新拉取
          </n-button>
        </div>
        <div class="panel-bd">
          <p class="small muted tip-line">{{ handEditTip }}藏行只影响论文测例表。</p>
          <n-data-table
            size="small"
            :columns="tcColumns"
            :data="tcRows"
            :bordered="false"
            :loading="tcLoading"
            :max-height="420"
          />
        </div>
      </section>

      <section v-else-if="section === 'menus'" class="ov-main panel">
        <div class="panel-hd">
          <h3>菜单 / 界面显示名</h3>
          <n-button text size="small" :disabled="!p?.workspace_path" :loading="menuLoading" @click="loadMenuRows">
            重新拉取
          </n-button>
        </div>
        <div class="panel-bd">
          <p class="small muted tip-line">{{ handEditTip }}只改显示名，不改菜单 key / 路由 path。</p>
          <n-data-table
            size="small"
            :columns="menuColumns"
            :data="menuRows"
            :bordered="false"
            :loading="menuLoading"
            :max-height="420"
          />
        </div>
      </section>

      <section v-else-if="section === 'usecase_desc'" class="ov-main panel">
        <div class="panel-hd">
          <h3>用例描述表</h3>
          <n-button text size="small" :disabled="!p?.workspace_path" :loading="ucLoading" @click="loadUsecaseDesc">
            重新拉取
          </n-button>
        </div>
        <div class="panel-bd">
          <p class="small muted tip-line">{{ handEditTip }}最多勾选 4 条主路径；下方改名称 / 说明 / 步骤。</p>
          <div v-if="ucCandidates.length" class="uc-pick">
            <label v-for="c in ucCandidates" :key="c.stable_id" class="uc-pick-item">
              <n-checkbox
                :checked="!!ucPick[c.stable_id]"
                :disabled="!ucPick[c.stable_id] && ucPickCount >= 4"
                @update:checked="(v) => toggleUcPick(c.stable_id, v)"
              />
              <span>{{ c.name || c.stable_id }}</span>
            </label>
          </div>
          <n-empty v-else-if="!ucLoading" description="暂无候选，请先生成工程" size="small" />
          <n-data-table
            size="small"
            :columns="ucCellColumns"
            :data="ucCellRows"
            :bordered="false"
            :single-line="false"
            :loading="ucLoading"
            :max-height="420"
            style="margin-top:12px"
          />
        </div>
      </section>

      <section v-else class="ov-main panel">
        <div class="panel-hd">
          <h3>失效补丁</h3>
          <n-button
            size="small"
            type="warning"
            secondary
            :disabled="!staleCount || saving"
            @click="clearStale"
          >
            一键清理
          </n-button>
        </div>
        <div class="panel-bd">
          <p class="small muted tip-line">重 bake 后键已不存在的补丁；清理不会改 SQL / 菜单。</p>
          <n-empty v-if="!staleList.length" description="没有失效项" size="small" />
          <ul v-else class="stale-list">
            <li v-for="(s, i) in staleList" :key="i">
              <code>{{ s.key || s.node_id }}</code>
              <span v-if="s.label"> · {{ s.label }}</span>
              <span class="small muted" v-if="s.kind"> · {{ s.kind }}</span>
            </li>
          </ul>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, h, inject, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { NInput, NButton, NCheckbox, NSelect, NEmpty, NTag } from 'naive-ui'
import { api, message } from '../../api'
import { PD_KEY } from './context'

const pd = inject(PD_KEY)
const p = computed(() => pd.p)

const section = ref('modules')
const navItems = [
  { id: 'modules', label: '功能模块图' },
  { id: 'architecture', label: '逻辑架构图' },
  { id: 'classes', label: '系统类图' },
  { id: 'sequence', label: '序列图' },
  { id: 'activity', label: '活动图' },
  { id: 'usecase', label: '用例图' },
  { id: 'usecase_desc', label: '用例描述表' },
  { id: 'testcases', label: '测试用例' },
  { id: 'menus', label: '菜单显示名' },
  { id: 'stale', label: '失效补丁' },
]

/** 各材料表同一句：清空 / 还原 = 跟机器原文 */
const handEditTip = '留空或点还原 = 跟机器名。'

const loading = ref(false)
const saving = ref(false)
const loaded = ref(false)
const version = ref(0)
const payload = ref({
  module_labels: {},
  module_hide: [],
  sequence: { selected_ids: [], labels: {} },
  activity: { selected_ids: [], labels: {} },
  usecase_desc: { selected_ids: [], cell_overrides: {} },
  _stale: [],
})
const moduleNodes = ref([])
const edits = ref({})
const baseline = ref({})
const hideSet = ref({})
const hideBaseline = ref({})

const diagLoading = ref(false)
const labelEdits = ref({})
const labelBaseline = ref({})
const labelMachine = ref({})

const ucLoading = ref(false)
const ucCandidates = ref([])
const ucCases = ref([])
const ucPick = ref({})
const ucPickBaseline = ref({})
const ucCellEdits = ref({})
const ucCellBaseline = ref({})

const archLoading = ref(false)
const archMachine = ref({})
const archEdits = ref({})
const archBaseline = ref({})

const ucDiagramLoading = ref(false)
const ucDiagramMachine = ref({})
const ucDiagramEdits = ref({})
const ucDiagramBaseline = ref({})
const ucHideSet = ref({})
const ucHideBaseline = ref({})

const tcLoading = ref(false)
const tcMachine = ref({})
const tcEdits = ref({})
const tcBaseline = ref({})
const tcHideSet = ref({})
const tcHideBaseline = ref({})

const menuLoading = ref(false)
const menuMachine = ref({})
const menuEdits = ref({})
const menuBaseline = ref({})
const schemaMachine = ref({})
const schemaEdits = ref({})
const schemaBaseline = ref({})

const classLoading = ref(false)
const classMachine = ref({})
const classEdits = ref({})
const classBaseline = ref({})
const classKeys = ref([])

const moduleQuery = ref('')
const moduleBranch = ref(null)
const moduleLeavesOnly = ref(true)
const labelQuery = ref('')
const classQuery = ref('')

const staleList = computed(() => {
  const s = payload.value?._stale
  return Array.isArray(s) ? s : []
})
const staleCount = computed(() => staleList.value.length)
const staleNodeIds = computed(() => {
  const ids = new Set()
  for (const s of staleList.value) {
    const nid = String(s?.node_id || '').trim()
    if (nid) ids.add(nid)
    const key = String(s?.key || '')
    const m = key.match(/^module_labels\.(.+)$/)
    if (m) ids.add(m[1])
  }
  return ids
})

const moduleRows = computed(() => {
  const labels = payload.value?.module_labels || {}
  return (moduleNodes.value || []).map((n) => {
    const id = n.id
    const machine = n.label || ''
    const edited = edits.value[id]
    const saved = labels[id]
    const draft = edited !== undefined ? edited : (saved ?? '')
    const hidden =
      hideSet.value[id] !== undefined
        ? !!hideSet.value[id]
        : !!(payload.value?.module_hide || []).includes(id)
    const path = n.path || id
    const parts = String(path).split('/').filter(Boolean)
    // 路径已从身份枝起（无系统标题）；按枝 = 第一段
    const branch = parts[0] || ''
    const isLeaf =
      n.is_leaf === '1' || n.is_leaf === true
        ? true
        : n.is_leaf === '0' || n.is_leaf === false
          ? false
          : parts.length >= 2
    return {
      id,
      path,
      branch,
      isLeaf,
      machine,
      draft,
      hidden,
      unstable: String(id).startsWith('identity:'),
      stale: staleNodeIds.value.has(id),
    }
  })
})

const moduleBranchOptions = computed(() => {
  const set = new Set()
  for (const r of moduleRows.value) {
    if (r.branch) set.add(r.branch)
  }
  return [...set].map((b) => ({ label: b, value: b }))
})

const filteredModuleRows = computed(() => {
  const q = String(moduleQuery.value || '').trim().toLowerCase()
  const br = moduleBranch.value
  return moduleRows.value.filter((r) => {
    if (moduleLeavesOnly.value && !r.isLeaf) return false
    if (br && r.branch !== br) return false
    if (!q) return true
    const hay = `${r.path} ${r.machine} ${r.draft} ${r.id}`.toLowerCase()
    return hay.includes(q)
  })
})

function moduleRowClass(row) {
  return row?.stale ? 'row-stale' : ''
}

const diagramSelected = computed(() => {
  const block = payload.value?.[section.value] || {}
  const ids = block.selected_ids
  return Array.isArray(ids) ? ids : []
})

const labelRows = computed(() => {
  const keys = Object.keys(labelMachine.value || {})
  return keys.map((key) => {
    const machine = labelMachine.value[key] || ''
    const draft =
      labelEdits.value[key] !== undefined
        ? labelEdits.value[key]
        : (payload.value?.[section.value]?.labels || {})[key] || ''
    return { key, machine, draft }
  })
})

const filteredLabelRows = computed(() => {
  const q = String(labelQuery.value || '').trim().toLowerCase()
  if (!q) return labelRows.value
  return labelRows.value.filter((r) =>
    `${r.key} ${r.machine} ${r.draft}`.toLowerCase().includes(q),
  )
})

const ucPickCount = computed(() => Object.values(ucPick.value).filter(Boolean).length)

const archRows = computed(() =>
  Object.keys(archMachine.value || {}).map((key) => ({
    key,
    machine: archMachine.value[key] || '',
    draft:
      archEdits.value[key] !== undefined
        ? archEdits.value[key]
        : (payload.value?.architecture_labels || {})[key] || '',
  })),
)

const classRows = computed(() => {
  const keys = classKeys.value.length
    ? classKeys.value
    : Object.keys({
        ...(classMachine.value || {}),
        ...(payload.value?.class_labels || {}),
        ...(classEdits.value || {}),
      })
  return keys.map((key) => ({
    key,
    machine: classMachine.value[key] || '',
    draft:
      classEdits.value[key] !== undefined
        ? classEdits.value[key]
        : (payload.value?.class_labels || {})[key] || '',
  }))
})

const filteredClassRows = computed(() => {
  const q = String(classQuery.value || '').trim().toLowerCase()
  if (!q) return classRows.value
  return classRows.value.filter((r) =>
    `${r.key} ${r.machine} ${r.draft}`.toLowerCase().includes(q),
  )
})

const ucDiagramRows = computed(() =>
  Object.keys(ucDiagramMachine.value || {}).map((key) => {
    const hidden =
      ucHideSet.value[key] !== undefined
        ? !!ucHideSet.value[key]
        : !!(payload.value?.usecase?.hide || []).includes(key)
    return {
      key,
      machine: ucDiagramMachine.value[key] || '',
      draft:
        ucDiagramEdits.value[key] !== undefined
          ? ucDiagramEdits.value[key]
          : (payload.value?.usecase?.labels || {})[key] || '',
      hidden: key.startsWith('actor:') ? false : hidden,
      isActor: key.startsWith('actor:'),
    }
  }),
)

const tcRows = computed(() => {
  const keys = Object.keys(tcMachine.value || {})
  return keys.map((key) => {
    const cid = key.split('.')[0]
    const hidden =
      tcHideSet.value[cid] !== undefined
        ? !!tcHideSet.value[cid]
        : !!(payload.value?.testcases?.hide || []).includes(cid)
    return {
      key,
      cid,
      machine: tcMachine.value[key] || '',
      draft:
        tcEdits.value[key] !== undefined
          ? tcEdits.value[key]
          : (payload.value?.testcases?.cell_overrides || {})[key] || '',
      hidden,
    }
  })
})

const menuRows = computed(() => {
  const rows = []
  for (const [key, machine] of Object.entries(menuMachine.value || {})) {
    rows.push({
      kind: 'menu',
      key,
      path: `菜单 ${key}`,
      machine,
      draft:
        menuEdits.value[key] !== undefined
          ? menuEdits.value[key]
          : (payload.value?.menu_labels || {})[key] || '',
    })
  }
  for (const [key, machine] of Object.entries(schemaMachine.value || {})) {
    rows.push({
      kind: 'schema',
      key,
      path: `labels.${key}`,
      machine,
      draft:
        schemaEdits.value[key] !== undefined
          ? schemaEdits.value[key]
          : (payload.value?.schema_labels || {})[key] || '',
    })
  }
  return rows
})

const ucCellRows = computed(() => {
  const rows = []
  for (const c of ucCases.value || []) {
    const sid = c.stable_id || c.id
    for (const field of ['name', 'actor', 'summary']) {
      const key = `${sid}.${field}`
      const machine = c[field] || ''
      const draft =
        ucCellEdits.value[key] !== undefined
          ? ucCellEdits.value[key]
          : (payload.value?.usecase_desc?.cell_overrides || {})[key] || ''
      rows.push({ key, path: `${c.name || sid} · ${field}`, machine, draft })
    }
    const flow = Array.isArray(c.flow) ? c.flow : []
    flow.forEach((step, i) => {
      const key = `${sid}.flow.${i}`
      const draft =
        ucCellEdits.value[key] !== undefined
          ? ucCellEdits.value[key]
          : (payload.value?.usecase_desc?.cell_overrides || {})[key] || ''
      rows.push({ key, path: `${c.name || sid} · 步骤${i + 1}`, machine: step, draft })
    })
  }
  return rows
})

const dirty = computed(() => {
  const cur = {}
  for (const r of moduleRows.value) {
    const v = String(r.draft || '').trim()
    if (v) cur[r.id] = v
  }
  const base = baseline.value || {}
  const keys = new Set([...Object.keys(cur), ...Object.keys(base)])
  for (const k of keys) {
    if ((cur[k] || '') !== (base[k] || '')) return true
  }
  const hideCur = {}
  for (const r of moduleRows.value) {
    if (r.hidden) hideCur[r.id] = true
  }
  const hideBase = hideBaseline.value || {}
  for (const k of new Set([...Object.keys(hideCur), ...Object.keys(hideBase)])) {
    if (!!hideCur[k] !== !!hideBase[k]) return true
  }
  for (const sect of ['sequence', 'activity']) {
    const editsMap = sect === section.value ? labelEdits.value : {}
    const saved = payload.value?.[sect]?.labels || {}
    const baseL = sect === section.value ? labelBaseline.value : saved
    const allKeys = new Set([
      ...Object.keys(editsMap),
      ...Object.keys(baseL || {}),
      ...Object.keys(saved),
    ])
    for (const k of allKeys) {
      const a = String(
        editsMap[k] !== undefined ? editsMap[k] : saved[k] || '',
      ).trim()
      const b = String((baseL || {})[k] || '').trim()
      if (a !== b && sect === section.value) return true
    }
  }
  const pickCur = { ...ucPick.value }
  const pickBase = ucPickBaseline.value || {}
  for (const k of new Set([...Object.keys(pickCur), ...Object.keys(pickBase)])) {
    if (!!pickCur[k] !== !!pickBase[k]) return true
  }
  const cellSaved = payload.value?.usecase_desc?.cell_overrides || {}
  for (const k of new Set([
    ...Object.keys(ucCellEdits.value),
    ...Object.keys(ucCellBaseline.value || {}),
  ])) {
    const a = String(
      ucCellEdits.value[k] !== undefined ? ucCellEdits.value[k] : cellSaved[k] || '',
    ).trim()
    const b = String((ucCellBaseline.value || {})[k] || '').trim()
    if (a !== b) return true
  }
  const maps = [
    [archEdits.value, archBaseline.value],
    [classEdits.value, classBaseline.value],
    [ucDiagramEdits.value, ucDiagramBaseline.value],
    [tcEdits.value, tcBaseline.value],
    [menuEdits.value, menuBaseline.value],
    [schemaEdits.value, schemaBaseline.value],
  ]
  for (const [cur, base] of maps) {
    for (const k of new Set([...Object.keys(cur || {}), ...Object.keys(base || {})])) {
      if (String((cur || {})[k] || '').trim() !== String((base || {})[k] || '').trim()) return true
    }
  }
  for (const [cur, base] of [
    [ucHideSet.value, ucHideBaseline.value],
    [tcHideSet.value, tcHideBaseline.value],
  ]) {
    for (const k of new Set([...Object.keys(cur || {}), ...Object.keys(base || {})])) {
      if (!!cur[k] !== !!base[k]) return true
    }
  }
  return false
})

/** 各材料表同一套：手调输入（可清空）+ 还原=跟机器 */
function handEditDraftColumn({
  title = '手调文案',
  width = 200,
  maxlength,
  textarea = false,
  getValue,
  setValue,
}) {
  return {
    title,
    key: 'draft',
    width,
    render: (row) => {
      const props = {
        value: getValue(row),
        size: 'small',
        clearable: true,
        placeholder: '空=跟机器',
        onUpdateValue: (v) => setValue(row, v == null ? '' : String(v)),
      }
      if (maxlength != null) props.maxlength = maxlength
      if (textarea) {
        props.type = 'textarea'
        props.autosize = { minRows: 1, maxRows: 3 }
      }
      return h(NInput, props)
    },
  }
}

function handEditRestoreColumn({ getValue, clearValue }) {
  return {
    title: '',
    key: 'restore',
    width: 64,
    render: (row) =>
      h(
        NButton,
        {
          text: true,
          size: 'tiny',
          disabled: !String(getValue(row) || '').trim(),
          onClick: () => clearValue(row),
        },
        { default: () => '还原' },
      ),
  }
}

const moduleColumns = [
  {
    title: '位置 / 原词',
    key: 'path',
    ellipsis: { tooltip: true },
    render: (row) =>
      h('div', { class: 'cell-path' }, [
        h('div', { class: 'path-line' }, [
          h('span', row.path),
          row.stale
            ? h(
                NTag,
                { size: 'tiny', type: 'warning', bordered: false, style: 'margin-left:6px' },
                { default: () => '失效' },
              )
            : null,
          row.unstable && !row.stale
            ? h('span', { class: 'small muted', style: 'margin-left:6px' }, '易失效')
            : null,
        ]),
        h('div', { class: 'small muted' }, `原词：${row.machine || '—'}`),
      ]),
  },
  handEditDraftColumn({
    width: 180,
    maxlength: 16,
    getValue: (row) => row.draft,
    setValue: (row, v) => {
      edits.value = { ...edits.value, [row.id]: v }
    },
  }),
  {
    title: '图上隐藏',
    key: 'hidden',
    width: 88,
    render: (row) =>
      h(NCheckbox, {
        checked: row.hidden,
        onUpdateChecked: (v) => {
          hideSet.value = { ...hideSet.value, [row.id]: !!v }
        },
      }),
  },
  handEditRestoreColumn({
    getValue: (row) => row.draft,
    clearValue: (row) => {
      edits.value = { ...edits.value, [row.id]: '' }
    },
  }),
]

const archColumns = [
  {
    title: '槽位 / 原文',
    key: 'key',
    render: (row) =>
      h('div', { class: 'cell-path' }, [
        h('code', row.key),
        h('div', { class: 'small muted' }, row.machine),
      ]),
  },
  handEditDraftColumn({
    maxlength: 32,
    getValue: (row) => row.draft,
    setValue: (row, v) => {
      archEdits.value = { ...archEdits.value, [row.key]: v }
    },
  }),
  handEditRestoreColumn({
    getValue: (row) => row.draft,
    clearValue: (row) => {
      archEdits.value = { ...archEdits.value, [row.key]: '' }
    },
  }),
]

const classColumns = [
  {
    title: '类名 / 原文',
    key: 'key',
    render: (row) =>
      h('div', { class: 'cell-path' }, [
        h('code', row.key),
        h('div', { class: 'small muted' }, row.machine),
      ]),
  },
  handEditDraftColumn({
    title: '中文显示名',
    maxlength: 32,
    getValue: (row) => row.draft,
    setValue: (row, v) => {
      classEdits.value = { ...classEdits.value, [row.key]: v }
    },
  }),
  handEditRestoreColumn({
    getValue: (row) => row.draft,
    clearValue: (row) => {
      classEdits.value = { ...classEdits.value, [row.key]: '' }
    },
  }),
]

const ucDiagramColumns = [
  {
    title: '用例 / 原文',
    key: 'key',
    render: (row) =>
      h('div', { class: 'cell-path' }, [
        h('code', row.key),
        h('div', { class: 'small muted' }, row.machine),
      ]),
  },
  handEditDraftColumn({
    width: 180,
    maxlength: 32,
    getValue: (row) => row.draft,
    setValue: (row, v) => {
      ucDiagramEdits.value = { ...ucDiagramEdits.value, [row.key]: v }
    },
  }),
  {
    title: '图上隐藏',
    key: 'hidden',
    width: 96,
    render: (row) =>
      row.isActor
        ? h('span', { class: 'small muted' }, '—')
        : h(NCheckbox, {
            checked: row.hidden,
            onUpdateChecked: (v) => {
              ucHideSet.value = { ...ucHideSet.value, [row.key]: !!v }
            },
          }),
  },
  handEditRestoreColumn({
    getValue: (row) => row.draft,
    clearValue: (row) => {
      ucDiagramEdits.value = { ...ucDiagramEdits.value, [row.key]: '' }
    },
  }),
]

const tcColumns = [
  {
    title: '单元格 / 原文',
    key: 'key',
    render: (row) =>
      h('div', { class: 'cell-path' }, [
        h('code', row.key),
        h('div', { class: 'small muted' }, row.machine),
      ]),
  },
  handEditDraftColumn({
    width: 180,
    getValue: (row) => row.draft,
    setValue: (row, v) => {
      tcEdits.value = { ...tcEdits.value, [row.key]: v }
    },
  }),
  {
    title: '藏行',
    key: 'hidden',
    width: 72,
    render: (row) =>
      h(NCheckbox, {
        checked: row.hidden,
        onUpdateChecked: (v) => {
          tcHideSet.value = { ...tcHideSet.value, [row.cid]: !!v }
        },
      }),
  },
  handEditRestoreColumn({
    getValue: (row) => row.draft,
    clearValue: (row) => {
      tcEdits.value = { ...tcEdits.value, [row.key]: '' }
    },
  }),
]

const menuColumns = [
  {
    title: '键 / 原文',
    key: 'path',
    render: (row) =>
      h('div', { class: 'cell-path' }, [
        h('div', row.path),
        h('div', { class: 'small muted' }, row.machine),
      ]),
  },
  handEditDraftColumn({
    title: '显示名',
    maxlength: 64,
    getValue: (row) => row.draft,
    setValue: (row, v) => {
      if (row.kind === 'menu') menuEdits.value = { ...menuEdits.value, [row.key]: v }
      else schemaEdits.value = { ...schemaEdits.value, [row.key]: v }
    },
  }),
  handEditRestoreColumn({
    getValue: (row) => row.draft,
    clearValue: (row) => {
      if (row.kind === 'menu') menuEdits.value = { ...menuEdits.value, [row.key]: '' }
      else schemaEdits.value = { ...schemaEdits.value, [row.key]: '' }
    },
  }),
]

const labelColumns = [
  {
    title: '键 / 机器原文',
    key: 'key',
    ellipsis: { tooltip: true },
    render: (row) =>
      h('div', { class: 'cell-path' }, [
        h('code', row.key),
        h('div', { class: 'small muted' }, row.machine),
      ]),
  },
  handEditDraftColumn({
    maxlength: 48,
    getValue: (row) => row.draft,
    setValue: (row, v) => {
      labelEdits.value = { ...labelEdits.value, [row.key]: v }
    },
  }),
  handEditRestoreColumn({
    getValue: (row) => row.draft,
    clearValue: (row) => {
      labelEdits.value = { ...labelEdits.value, [row.key]: '' }
    },
  }),
]

const ucCellColumns = [
  {
    title: '位置 / 原文',
    key: 'path',
    ellipsis: { tooltip: true },
    render: (row) =>
      h('div', { class: 'cell-path' }, [
        h('div', row.path),
        h('div', { class: 'small muted' }, row.machine),
      ]),
  },
  handEditDraftColumn({
    width: 220,
    textarea: true,
    getValue: (row) => row.draft,
    setValue: (row, v) => {
      ucCellEdits.value = { ...ucCellEdits.value, [row.key]: v }
    },
  }),
  handEditRestoreColumn({
    getValue: (row) => row.draft,
    clearValue: (row) => {
      ucCellEdits.value = { ...ucCellEdits.value, [row.key]: '' }
    },
  }),
]

function hideMapFromPayload(pl) {
  const out = {}
  for (const id of pl?.module_hide || []) {
    if (id) out[id] = true
  }
  return out
}

function syncLocalFromPayload(pl, nodes) {
  payload.value = pl || {
    module_labels: {},
    module_hide: [],
    sequence: { selected_ids: [], labels: {} },
    activity: { selected_ids: [], labels: {} },
    usecase_desc: { selected_ids: [], cell_overrides: {} },
    _stale: [],
  }
  moduleNodes.value = nodes || []
  const ml = { ...(payload.value.module_labels || {}) }
  baseline.value = { ...ml }
  edits.value = { ...ml }
  const hm = hideMapFromPayload(payload.value)
  hideBaseline.value = { ...hm }
  hideSet.value = { ...hm }
  const seqL = { ...(payload.value.sequence?.labels || {}) }
  const actL = { ...(payload.value.activity?.labels || {}) }
  if (section.value === 'sequence') {
    labelBaseline.value = { ...seqL }
    labelEdits.value = { ...seqL }
  } else if (section.value === 'activity') {
    labelBaseline.value = { ...actL }
    labelEdits.value = { ...actL }
  }
  const pick = {}
  for (const id of payload.value.usecase_desc?.selected_ids || []) {
    if (id) pick[id] = true
  }
  ucPick.value = { ...pick }
  ucPickBaseline.value = { ...pick }
  const cells = { ...(payload.value.usecase_desc?.cell_overrides || {}) }
  ucCellBaseline.value = { ...cells }
  ucCellEdits.value = { ...cells }

  const archL = { ...(payload.value.architecture_labels || {}) }
  archBaseline.value = { ...archL }
  archEdits.value = { ...archL }
  const ucL = { ...(payload.value.usecase?.labels || {}) }
  ucDiagramBaseline.value = { ...ucL }
  ucDiagramEdits.value = { ...ucL }
  const ucH = {}
  for (const id of payload.value.usecase?.hide || []) if (id) ucH[id] = true
  ucHideBaseline.value = { ...ucH }
  ucHideSet.value = { ...ucH }
  const tcL = { ...(payload.value.testcases?.cell_overrides || {}) }
  tcBaseline.value = { ...tcL }
  tcEdits.value = { ...tcL }
  const tcH = {}
  for (const id of payload.value.testcases?.hide || []) if (id) tcH[id] = true
  tcHideBaseline.value = { ...tcH }
  tcHideSet.value = { ...tcH }
  const menuL = { ...(payload.value.menu_labels || {}) }
  menuBaseline.value = { ...menuL }
  menuEdits.value = { ...menuL }
  const sl = { ...(payload.value.schema_labels || {}) }
  schemaBaseline.value = { ...sl }
  schemaEdits.value = { ...sl }
  const cl = { ...(payload.value.class_labels || {}) }
  classBaseline.value = { ...cl }
  classEdits.value = { ...cl }
}

function buildPayloadFromEdits() {
  const next = {
    ...(payload.value || {}),
    schema_version: 1,
    module_labels: {},
    module_hide: [],
  }
  for (const r of moduleRows.value) {
    const v = String(edits.value[r.id] !== undefined ? edits.value[r.id] : r.draft || '').trim()
    if (v) next.module_labels[r.id] = v
    const hid = hideSet.value[r.id] !== undefined ? !!hideSet.value[r.id] : !!r.hidden
    if (hid) next.module_hide.push(r.id)
  }
  for (const sect of ['sequence', 'activity']) {
    const prev = next[sect] && typeof next[sect] === 'object' ? next[sect] : {}
    const labels = { ...(prev.labels || {}) }
    if (sect === section.value) {
      for (const [k, v] of Object.entries(labelEdits.value || {})) {
        const t = String(v || '').trim()
        if (t) labels[k] = t
        else delete labels[k]
      }
    }
    next[sect] = {
      selected_ids: Array.isArray(prev.selected_ids) ? prev.selected_ids : [],
      labels,
    }
  }
  const ucPrev =
    next.usecase_desc && typeof next.usecase_desc === 'object' ? next.usecase_desc : {}
  const selected_ids = Object.keys(ucPick.value).filter((k) => ucPick.value[k])
  const cell_overrides = { ...(ucPrev.cell_overrides || {}) }
  for (const [k, v] of Object.entries(ucCellEdits.value || {})) {
    const t = String(v || '').trim()
    if (t) cell_overrides[k] = t
    else delete cell_overrides[k]
  }
  next.usecase_desc = { selected_ids, cell_overrides }

  const archLabels = { ...(next.architecture_labels || {}) }
  for (const [k, v] of Object.entries(archEdits.value || {})) {
    const t = String(v || '').trim()
    if (t) archLabels[k] = t
    else delete archLabels[k]
  }
  next.architecture_labels = archLabels

  const ucLabels = { ...(next.usecase?.labels || {}) }
  for (const [k, v] of Object.entries(ucDiagramEdits.value || {})) {
    const t = String(v || '').trim()
    if (t) ucLabels[k] = t
    else delete ucLabels[k]
  }
  const ucHide = Object.keys(ucHideSet.value).filter((k) => ucHideSet.value[k])
  next.usecase = { labels: ucLabels, hide: ucHide }

  const tcCells = { ...(next.testcases?.cell_overrides || {}) }
  for (const [k, v] of Object.entries(tcEdits.value || {})) {
    const t = String(v || '').trim()
    if (t) tcCells[k] = t
    else delete tcCells[k]
  }
  next.testcases = {
    hide: Object.keys(tcHideSet.value).filter((k) => tcHideSet.value[k]),
    cell_overrides: tcCells,
  }

  const menuLabels = {}
  for (const [k, v] of Object.entries(menuEdits.value || {})) {
    const t = String(v || '').trim()
    if (t) menuLabels[k] = t
  }
  next.menu_labels = menuLabels
  const schemaLabels = {}
  for (const [k, v] of Object.entries(schemaEdits.value || {})) {
    const t = String(v || '').trim()
    if (t) schemaLabels[k] = t
  }
  next.schema_labels = schemaLabels
  const classLabels = { ...(next.class_labels || {}) }
  for (const [k, v] of Object.entries(classEdits.value || {})) {
    const t = String(v || '').trim()
    if (t) classLabels[k] = t
    else delete classLabels[k]
  }
  next.class_labels = classLabels
  return next
}

async function reload() {
  if (!p.value?.id) return
  loading.value = true
  try {
    const body = await api.getOverrides(p.value.id)
    version.value = body.version || 0
    syncLocalFromPayload(body.payload, body.module_nodes)
    loaded.value = true
  } catch {
    /* api toast */
  } finally {
    loading.value = false
  }
}

async function defSave(apply) {
  if (!p.value?.id) return
  saving.value = true
  try {
    const body = await api.putOverrides(p.value.id, {
      payload: buildPayloadFromEdits(),
      version: version.value,
      apply,
    })
    version.value = body.version || 0
    syncLocalFromPayload(body.payload, body.module_nodes || moduleNodes.value)
    loaded.value = true
    message.success(apply ? '已保存并叠到材料' : '已保存草稿')
    return body
  } catch (e) {
    if (e?.response?.status === 409) {
      message.error('有人改过了，已刷新，请再改一次')
      try {
        await reload()
      } catch {
        /* ignore */
      }
    }
    throw e
  } finally {
    saving.value = false
  }
}

async function saveOnly() {
  await defSave(true)
}

async function saveAndPreview() {
  // defSave 已用响应体对齐草稿；预览另开 loading，勿把 saving 拖到图接口结束
  await defSave(true)
  if (section.value === 'modules') await openModulesPreview()
  else if (section.value === 'sequence' || section.value === 'activity') await openDiagramPreview()
  else if (section.value === 'classes') await openClassesPreview()
  else if (section.value === 'usecase_desc') await loadUsecaseDesc()
  else if (section.value === 'architecture' && typeof pd.openArchitecture === 'function')
    await pd.openArchitecture()
  else if (section.value === 'usecase' && typeof pd.openUsecases === 'function') await pd.openUsecases()
  else if (section.value === 'testcases' && typeof pd.openTestcases === 'function')
    await pd.openTestcases()
  else if (section.value === 'menus') message.success('菜单显示名已写入 schema，刷新学生端预览可见')
}

async function clearStale() {
  if (!p.value?.id) return
  saving.value = true
  try {
    const body = await api.clearOverridesStale(p.value.id)
    version.value = body.version || 0
    syncLocalFromPayload(body.payload, body.module_nodes || moduleNodes.value)
    message.success('已清理失效补丁')
  } finally {
    saving.value = false
  }
}

async function openModulesPreview() {
  if (typeof pd.openModules === 'function') {
    if (typeof pd.ensureModulesMeta === 'function') {
      await pd.ensureModulesMeta({ force: true })
    }
    await pd.openModules()
  } else {
    message.info('请到「产物 / 对照 → 论文材料」打开功能模块图')
  }
}

async function openDiagramPreview() {
  if (section.value === 'sequence' && typeof pd.openSequences === 'function') {
    await pd.openSequences()
  } else if (section.value === 'activity' && typeof pd.openActivities === 'function') {
    await pd.openActivities()
  } else {
    message.info('请到论文材料打开对应图')
  }
}

async function loadDiagramLabelRows() {
  if (!p.value?.id || (section.value !== 'sequence' && section.value !== 'activity')) return
  diagLoading.value = true
  try {
    const body =
      section.value === 'sequence'
        ? await api.getSequences(p.value.id, {})
        : await api.getActivities(p.value.id, {})
    const machine = {}
    for (const d of body?.diagrams || []) {
      const did = d.id
      if (!did) continue
      if (section.value === 'sequence') {
        for (const part of d.participants || []) {
          machine[`${did}::p:${part.id}`] = part.label || ''
        }
        for (const m of d.messages || []) {
          machine[`${did}::m:${m.seq}`] = m.text || ''
        }
      } else {
        for (const n of d.nodes || []) {
          if (n.text) machine[`${did}::n:${n.id}`] = n.text
        }
        for (const e of d.edges || []) {
          if (e.guard) machine[`${did}::g:${e.from}_${e.to}`] = e.guard
        }
      }
    }
    labelMachine.value = machine
    const saved = { ...(payload.value?.[section.value]?.labels || {}) }
    labelBaseline.value = { ...saved }
    labelEdits.value = { ...saved }
    if (Array.isArray(body?.selected)) {
      const prev = payload.value?.[section.value] || {}
      payload.value = {
        ...payload.value,
        [section.value]: { ...prev, selected_ids: [...body.selected] },
      }
    }
  } catch {
    message.error('无法加载图短签')
  } finally {
    diagLoading.value = false
  }
}

async function loadUsecaseDesc() {
  if (!p.value?.id) return
  ucLoading.value = true
  try {
    const body = await api.getUsecaseDescriptions(p.value.id, {})
    ucCandidates.value = body.candidates || []
    ucCases.value = body.cases || []
    if (Array.isArray(body.selected_ids) && body.selected_ids.length) {
      const pick = {}
      for (const id of body.selected_ids) pick[id] = true
      if (!Object.keys(ucPick.value).length) {
        ucPick.value = { ...pick }
        ucPickBaseline.value = { ...pick }
      }
    }
  } catch {
    message.error('无法加载用例描述')
  } finally {
    ucLoading.value = false
  }
}

function toggleUcPick(id, v) {
  const next = { ...ucPick.value }
  if (v) next[id] = true
  else delete next[id]
  ucPick.value = next
}

async function loadArchitectureRows() {
  if (!p.value?.id) return
  archLoading.value = true
  try {
    const body = await api.getArchitecture(p.value.id)
    const machine = {}
    for (const r of body?.roles || []) if (r?.id) machine[r.id] = r.label || ''
    for (const layer of body?.layers || []) if (layer?.id) machine[layer.id] = layer.label || ''
    if (body?.protocol_label) machine.protocol_label = body.protocol_label
    if (body?.action_label) machine.action_label = body.action_label
    archMachine.value = machine
  } catch {
    message.error('无法加载架构图槽位')
  } finally {
    archLoading.value = false
  }
}

async function loadUsecaseRows() {
  if (!p.value?.id) return
  ucDiagramLoading.value = true
  try {
    const body = await api.getUsecases(p.value.id, { actor: 'user' })
    const machine = {}
    const actor = body?.actor
    if (actor?.id) machine[`actor:${actor.id}`] = actor.label || ''
    const walk = (n) => {
      if (!n?.id) return
      machine[n.id] = n.label || ''
      for (const c of n.includes || []) walk(c)
    }
    for (const n of body?.level1 || []) walk(n)
    ucDiagramMachine.value = machine
  } catch {
    message.error('无法加载用例图')
  } finally {
    ucDiagramLoading.value = false
  }
}

async function loadTestcaseRows() {
  if (!p.value?.id) return
  tcLoading.value = true
  try {
    const body = await api.getTestcases(p.value.id, {})
    const machine = {}
    for (const r of body?.rows || []) {
      const cid = r.id
      if (!cid) continue
      for (const [k, v] of Object.entries(r)) {
        if (k === 'id') continue
        if (v == null || v === '') continue
        machine[`${cid}.${k}`] = String(v)
      }
    }
    tcMachine.value = machine
  } catch {
    message.error('无法加载测试用例')
  } finally {
    tcLoading.value = false
  }
}

async function loadMenuRows() {
  if (!p.value?.id) return
  menuLoading.value = true
  try {
    const body = await api.getSchema(p.value.id)
    const menus = body?.menus || {}
    const machine = {}
    for (const items of Object.values(menus)) {
      if (!Array.isArray(items)) continue
      for (const it of items) {
        const key = it?.key
        if (key) machine[key] = it.label || it.title || ''
      }
    }
    menuMachine.value = machine
    const labels = body?.labels || {}
    const sm = {}
    for (const [k, v] of Object.entries(labels)) {
      if (typeof v === 'string') sm[k] = v
    }
    schemaMachine.value = sm
  } catch {
    message.error('无法加载菜单 / labels')
  } finally {
    menuLoading.value = false
  }
}

async function loadClassRows() {
  if (!p.value?.id) return
  classLoading.value = true
  try {
    const body = await api.getClasses(p.value.id, { display: 'sample' })
    const machine = {}
    const keys = []
    for (const c of body?.classes || []) {
      const name = String(c?.name || '').trim()
      if (!name) continue
      keys.push(name)
      machine[name] = String(c?.label || name)
    }
    classKeys.value = keys
    classMachine.value = machine
  } catch {
    message.error('无法加载类图')
  } finally {
    classLoading.value = false
  }
}

async function openClassesPreview() {
  if (typeof pd.openClasses === 'function') {
    await pd.openClasses()
  } else {
    message.info('请到「产物 / 对照 → 论文材料」打开系统类图')
  }
}

async function selectSection(id) {
  section.value = id
  if (id === 'sequence' || id === 'activity') {
    const saved = { ...(payload.value?.[id]?.labels || {}) }
    labelBaseline.value = { ...saved }
    labelEdits.value = { ...saved }
    labelMachine.value = {}
    await loadDiagramLabelRows()
  }
  if (id === 'usecase_desc') await loadUsecaseDesc()
  if (id === 'architecture') await loadArchitectureRows()
  if (id === 'classes') await loadClassRows()
  if (id === 'usecase') await loadUsecaseRows()
  if (id === 'testcases') await loadTestcaseRows()
  if (id === 'menus') await loadMenuRows()
}

function onBeforeUnload(e) {
  if (!dirty.value) return
  e.preventDefault()
  e.returnValue = ''
}

onMounted(() => {
  reload()
  window.addEventListener('beforeunload', onBeforeUnload)
})
onBeforeUnmount(() => {
  window.removeEventListener('beforeunload', onBeforeUnload)
})
watch(
  () => p.value?.id,
  () => reload(),
)
</script>

<style scoped>
.overrides-tab {
  padding: 4px 0 24px;
}
.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 12px;
}
.toolbar-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.dirty-dot {
  color: var(--amber);
  font-weight: 600;
}
.stale-link {
  color: var(--amber);
  text-decoration: none;
}
.stale-link:hover {
  text-decoration: underline;
}
.grid-overrides {
  display: grid;
  grid-template-columns: 168px 1fr;
  gap: 12px;
}
@media (max-width: 800px) {
  .grid-overrides {
    grid-template-columns: 1fr;
  }
}
.ov-nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.ov-nav-item {
  text-align: left;
  border: 1px solid var(--line);
  background: var(--surface);
  color: var(--ink);
  padding: 8px 10px;
  border-radius: 6px;
  cursor: pointer;
  font: inherit;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}
.ov-nav-item:hover {
  border-color: color-mix(in srgb, var(--teal) 45%, var(--line));
  background: var(--surface-2);
}
.ov-nav-item.active {
  border-color: var(--teal);
  color: var(--teal);
  background: color-mix(in srgb, var(--teal) 12%, var(--surface));
}
.ov-nav-item.warn {
  border-color: color-mix(in srgb, var(--amber) 55%, var(--line));
}
.nav-badge {
  min-width: 18px;
  padding: 0 5px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--amber) 28%, var(--surface));
  color: var(--amber);
  font-size: 11px;
  text-align: center;
}
.table-tools {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.tip-line {
  margin: 0 0 10px;
}
.path-line {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
}
.cell-path .small {
  margin-top: 2px;
}
:deep(.row-stale td) {
  background: color-mix(in srgb, var(--amber) 8%, transparent);
}
.sel-chip {
  margin-right: 4px;
  font-size: 11px;
}
.stale-list {
  margin: 0;
  padding-left: 1.2em;
  color: var(--ink);
}
.uc-pick {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 200px;
  overflow: auto;
}
.uc-pick-item {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: var(--ink);
}
</style>
