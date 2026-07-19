<template>
  <div v-if="p">
    <button class="back" @click="$router.push('/')">← 返回项目列表</button>
    <div class="proj-head">
      <div>
        <div class="proj-title">{{ p.title }}</div>
        <div class="proj-meta">
          <span class="pill" :class="statusPill">{{ statusLabel }}</span>
          <span>ID <span class="mono">{{ p.id }}</span></span>
          <span>{{ p.archetype }} · {{ p.domain }}</span>
          <span class="mono">{{ p.db_name }}</span>
        </div>
      </div>
      <div class="proj-actions">
        <n-button :disabled="!canDownload" @click="downloadZip">下载 ZIP</n-button>
        <n-button type="error" secondary size="small" :disabled="deleteBlocked" :title="deleteBlockedReason" @click="onDelete">删除</n-button>
      </div>
    </div>

    <n-tabs v-model:value="tab" type="line" animated>
      <!-- Match -->
      <n-tab-pane name="match" tab="匹配确认">
        <div class="file-row">
          <span>开题报告：<strong>{{ p.source_filename }}</strong> · {{ formatSize(p.source_size) }}</span>
          <n-button text size="small" @click="$router.push('/')">另建项目</n-button>
        </div>
        <div class="banner success">
          <h4>推荐匹配已给出</h4>
          <p class="small muted">确认后开始生成。骨架 / 领域改动需先解锁。</p>
        </div>
        <div class="grid-2">
          <div class="panel">
            <div class="panel-hd">
              <h3>推荐匹配</h3>
              <span class="pill" :class="matchPillClass">{{ matchPillText }}</span>
            </div>
            <div class="panel-bd">
              <div class="rec-box">
                <div class="rec-title">系统推荐（置信度 {{ p.confidence.toFixed(2) }}）</div>
                <div class="rec-main">{{ p.recommended_arch }} × {{ p.recommended_domain }}</div>
                <div class="rec-sub" v-if="p.spec?.hits?.length">命中：{{ p.spec.hits.join(' / ') }}</div>
                <div class="rec-sub" v-if="p.spec?.out_of_mvp?.length">砍项：{{ p.spec.out_of_mvp.join('、') }}</div>
              </div>
              <div class="lock-row">
                <span class="small muted">{{ unlocked ? '骨架 / 领域可改' : '骨架 / 领域已锁定' }}</span>
                <div class="row">
                  <n-button size="small" @click="toggleUnlock">{{ unlocked ? '重新锁定' : '解锁覆盖' }}</n-button>
                  <n-button v-if="unlocked || deviant" text size="small" @click="resetMatch">恢复推荐</n-button>
                </div>
              </div>
              <div class="grid-2">
                <div class="field" :class="{ locked: !unlocked }">
                  <n-form-item label="骨架">
                    <n-select v-model:value="form.archetype" :options="archOptions" :disabled="!unlocked" @update:value="onArchDomChange" />
                  </n-form-item>
                </div>
                <div class="field" :class="{ locked: !unlocked }">
                  <n-form-item label="领域">
                    <n-select v-model:value="form.domain" :options="domOptions" :disabled="!unlocked" @update:value="onArchDomChange" />
                  </n-form-item>
                </div>
                <n-form-item label="行业配色">
                  <n-select v-model:value="form.theme" :options="themeOptions" @update:value="saveSoft" />
                </n-form-item>
                <n-form-item label="LLM 业务岛">
                  <n-select v-model:value="form.llm" :options="llmOptions" @update:value="saveSoft" />
                </n-form-item>
                <n-form-item label="密码">
                  <n-select v-model:value="form.passwordHash" :options="passwordHashOptions" @update:value="saveSoft" />
                </n-form-item>
              </div>
              <div class="confidence">
                <span class="small muted">置信度</span>
                <div class="bar"><i :style="{ width: displayConf * 100 + '%', background: displayConf >= 0.75 ? 'var(--green)' : '#d97706' }" /></div>
                <strong>{{ displayConf.toFixed(2) }}</strong>
                <span v-if="deviant" class="small muted">覆盖后降级 · 推荐 {{ (p.confidence || 0).toFixed(2) }}</span>
              </div>
              <div class="override-banner" :class="{ show: unlocked || deviant, danger: deviant }">
                {{ deviant ? '当前与推荐不一致，请确认后再生成。' : '骨架 / 领域可改。无把握请恢复推荐。' }}
              </div>
            </div>
          </div>
          <div class="panel">
            <div class="panel-hd">
              <h3>解析摘要 · Spec 预览</h3>
              <n-button text size="small" @click="showSpec = true">JSON</n-button>
            </div>
            <div class="panel-bd parse-panel">
              <div class="parse-block">
                <div class="parse-label">开题解析</div>
                <div class="parse-title">{{ proposal.title || p.title }}</div>
                <p v-if="proposal.background" class="parse-bg">{{ proposal.background }}</p>
                <div v-if="proposal.hits?.length" class="parse-hits">
                  <span v-for="h in proposal.hits" :key="h" class="hit-chip">{{ h }}</span>
                </div>
                <div v-if="proposal.feature_lines?.length" class="parse-sec">
                  <div class="parse-sec-hd">开题功能点</div>
                  <ol class="parse-list">
                    <li v-for="(line, i) in proposal.feature_lines" :key="i">{{ line }}</li>
                  </ol>
                </div>
                <div v-if="proposal.out_scope_lines?.length" class="parse-sec">
                  <div class="parse-sec-hd">开题写明不在本期</div>
                  <ul class="parse-list plain">
                    <li v-for="(line, i) in proposal.out_scope_lines" :key="i">{{ line }}</li>
                  </ul>
                </div>
                <details v-if="proposal.excerpt" class="parse-excerpt">
                  <summary>原文摘录 · {{ proposal.char_count || proposal.excerpt.length }} 字</summary>
                  <pre>{{ proposal.excerpt }}</pre>
                </details>
                <p v-if="!proposal.excerpt && !proposal.feature_lines?.length" class="small muted">暂无开题正文摘要（源文件不可读时可另建项目）</p>
              </div>
              <div class="parse-block">
                <div class="parse-label">生成 Spec</div>
                <dl class="spec-dl">
                  <div><dt>角色</dt><dd>{{ (p.spec?.roles || []).join('、') || '—' }}</dd></div>
                  <div><dt>实体</dt><dd>{{ (p.spec?.entities || []).join('、') || '—' }}</dd></div>
                  <div><dt>主流程</dt><dd>{{ (p.spec?.flows || []).join('；') || '—' }}</dd></div>
                  <div><dt>基线</dt><dd>{{ (p.spec?.baseline || []).join('、') || '—' }}</dd></div>
                  <div v-if="p.spec?.out_of_mvp?.length"><dt>砍项</dt><dd>{{ p.spec.out_of_mvp.join('、') }}</dd></div>
                  <div><dt>配色</dt><dd>{{ p.spec?.theme_label || p.theme }}</dd></div>
                </dl>
              </div>
            </div>
          </div>
        </div>
        <div class="gate" :class="{ ok: ack }">
          <n-checkbox v-model:checked="ack" :disabled="p.match_confirmed">
            {{ confirmHint }}
          </n-checkbox>
        </div>
        <div class="row mt-16">
          <n-button type="primary" size="large" :disabled="!ack || p.match_confirmed" @click="confirmMatch">
            {{ deviant ? '确认覆盖并继续' : '确认并继续' }}
          </n-button>
        </div>
      </n-tab-pane>

      <!-- Generate -->
      <n-tab-pane name="generate" tab="一键生成">
        <div v-if="genState === 'idle'">
          <div class="panel mb-16">
            <div class="panel-bd">
              <div class="row" style="justify-content:space-between">
                <div>
                  <div style="font-weight:600;margin-bottom:4px">{{ p.match_confirmed ? '匹配已确认 · 可以生成' : '请先完成匹配确认' }}</div>
                  <div class="small muted">bake 为主 · LLM 仅填业务岛 · 门禁不过禁止 ZIP</div>
                </div>
                <n-button type="primary" size="large" :disabled="!p.match_confirmed" @click="startGenerate">一键生成</n-button>
              </div>
            </div>
          </div>
          <div class="panel">
            <div class="panel-hd"><h3>将执行的步骤</h3></div>
            <div class="panel-bd">
              <ul class="step-list">
                <li v-for="(s, i) in planSteps" :key="i"><span class="step-ico">{{ i + 1 }}</span><div><div>{{ s.t }}</div><div class="meta">{{ s.m }}</div></div></li>
              </ul>
            </div>
          </div>
        </div>
        <div v-else-if="genState === 'running'">
          <div class="panel mb-16">
            <div class="panel-bd">
              <div class="row" style="justify-content:space-between;margin-bottom:10px">
                <div style="font-weight:600">正在生成…</div>
                <div class="small muted">Job #{{ currentJob?.id }} · {{ currentJob?.progress || 0 }}%</div>
              </div>
              <div class="progress" style="height:8px"><i :style="{ width: (currentJob?.progress || 0) + '%' }" /></div>
              <div class="row mt-12">
                <n-button size="small" type="error" secondary @click="cancelCurrent">取消任务</n-button>
                <n-button size="small" @click="tab = 'logs'">打开日志</n-button>
              </div>
            </div>
          </div>
          <div class="panel">
            <div class="panel-hd"><h3>步骤进度</h3></div>
            <div class="panel-bd">
              <ul class="step-list">
                <li v-for="s in (currentJob?.steps || [])" :key="s.key" :class="s.status">
                  <span class="step-ico">{{ s.status === 'done' ? '✓' : s.status === 'run' ? '…' : s.status === 'fail' ? '!' : '·' }}</span>
                  <div><div>{{ s.title }}</div><div class="meta">{{ s.meta || s.status }}</div></div>
                </li>
              </ul>
            </div>
          </div>
        </div>
        <div v-else-if="genState === 'success' || genState === 'live'" class="banner success">
          <h4>{{ genState === 'live' ? '已生成 · 预览运行中' : '生成完成 · 门禁全过 · 可交付' }}</h4>
          <p class="small muted">{{ genState === 'live' ? '前后端已启动，可打开预览或下载 ZIP。' : 'ZIP 已解锁。请到「运行」预览后再交付。' }}</p>
          <div class="row mt-12">
            <n-button type="primary" @click="tab = 'runtime'">前往运行</n-button>
            <n-button @click="tab = 'artifacts'">查看门禁</n-button>
            <n-button :disabled="!canDownload" @click="downloadZip">下载 ZIP</n-button>
            <n-button @click="startGenerate">重新生成</n-button>
          </div>
        </div>
        <div v-else class="banner fail">
          <h4>门禁未过 · 禁止交付</h4>
          <p class="small muted">{{ currentJob?.error || '主流程 / 功能清单未通过则禁止下载 ZIP。' }}</p>
          <div class="row mt-12">
            <n-button type="primary" @click="retryCurrent">从失败步骤重试</n-button>
            <n-button @click="tab = 'artifacts'">查看门禁</n-button>
            <n-button @click="tab = 'logs'">查看日志</n-button>
          </div>
        </div>
      </n-tab-pane>

      <!-- Runtime -->
      <n-tab-pane name="runtime" tab="运行">
        <div class="row mb-16" style="justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
          <span class="small muted">库 <span class="mono">{{ p.db_name || '—' }}</span></span>
          <div class="row" style="margin:0">
            <n-button type="primary" :disabled="!p.workspace_path || rtAnyBusy" :loading="rtAllBusy && rtPendingAll==='start'" @click="rtAction('all','start')">全部启动</n-button>
            <n-button :disabled="!p.workspace_path || rtAnyBusy" :loading="rtAllBusy && rtPendingAll==='stop'" @click="rtAction('all','stop')">全部关闭</n-button>
            <n-button :disabled="!p.workspace_path || rtAnyBusy" :loading="rtAllBusy && rtPendingAll==='restart'" @click="rtAction('all','restart')">全部重启</n-button>
            <n-button :disabled="rt.frontend_status !== 'healthy' || rtBusyFe" @click="openPreview">打开预览</n-button>
          </div>
        </div>
        <div class="grid-2">
          <div class="panel">
            <div class="panel-hd">
              <h3>后端 · :{{ p.backend_port }}</h3>
              <span class="pill" :class="runtimeStatusPill(rt.backend_status)">{{ runtimeStatusLabel(rt.backend_status) }}</span>
            </div>
            <div class="panel-bd">
              <div class="row" style="justify-content:flex-end">
                <n-button
                  size="small"
                  :disabled="rtBusyBe || rtAllBusy || runtimeTransient(rt.backend_status)"
                  :loading="rtBusyBe || runtimeTransient(rt.backend_status)"
                  @click="rtAction('backend', runtimeCanStop(rt.backend_status) ? 'stop' : 'start')"
                >{{ runtimeCanStop(rt.backend_status) ? '停止' : '启动' }}</n-button>
              </div>
              <pre class="log-box">{{ runtimeLogView(rt.backend_status, rt.backend_log_tail) }}</pre>
            </div>
          </div>
          <div class="panel">
            <div class="panel-hd">
              <h3>前端 · :{{ p.frontend_port }}</h3>
              <span class="pill" :class="runtimeStatusPill(rt.frontend_status)">{{ runtimeStatusLabel(rt.frontend_status) }}</span>
            </div>
            <div class="panel-bd">
              <div class="row" style="justify-content:flex-end">
                <n-button
                  size="small"
                  :disabled="rtBusyFe || rtAllBusy || runtimeTransient(rt.frontend_status)"
                  :loading="rtBusyFe || runtimeTransient(rt.frontend_status)"
                  @click="rtAction('frontend', runtimeCanStop(rt.frontend_status) ? 'stop' : 'start')"
                >{{ runtimeCanStop(rt.frontend_status) ? '停止' : '启动' }}</n-button>
              </div>
              <pre class="log-box">{{ runtimeLogView(rt.frontend_status, rt.frontend_log_tail) }}</pre>
            </div>
          </div>
        </div>
      </n-tab-pane>

      <!-- Logs -->
      <n-tab-pane name="logs" tab="日志">
        <div class="row mb-12" style="justify-content:space-between;gap:12px;flex-wrap:wrap">
          <div class="row" style="gap:10px;flex-wrap:wrap">
            <n-button-group size="small">
              <n-button v-for="s in logSides" :key="s.id" :type="logSide===s.id?'primary':'default'" @click="loadLog(s.id)">{{ s.label }}</n-button>
            </n-button-group>
            <n-input v-model:value="logFilter" clearable placeholder="过滤关键字…" style="width:180px" />
          </div>
          <n-button size="small" @click="loadLog(logSide)">刷新</n-button>
        </div>
        <pre class="log-viewer">{{ filteredLog }}</pre>
      </n-tab-pane>

      <!-- Artifacts -->
      <n-tab-pane name="artifacts" tab="产物 / 数据库">
        <div class="grid-2">
          <div class="panel">
            <div class="panel-hd"><h3>产物</h3></div>
            <div class="panel-bd stack">
              <div class="file-row" style="margin:0">
                <span><strong>thesis-app.zip</strong><br /><span class="small muted">{{ canDownload ? '门禁已过' : '门禁未过 · 锁定' }}</span></span>
                <n-button size="small" :disabled="!canDownload" @click="downloadZip">下载</n-button>
              </div>
              <div class="file-row" style="margin:0">
                <span><strong>workspace/</strong><br /><span class="small muted mono">{{ p.workspace_path || '尚未生成' }}</span></span>
              </div>
              <div class="file-row" style="margin:0">
                <span><strong>spec.json</strong></span>
                <n-button text size="small" @click="showSpec = true">查看</n-button>
              </div>
            </div>
          </div>
          <div class="panel">
            <div class="panel-hd">
              <h3>数据库</h3>
              <span class="pill" :class="schema ? 'pill-green' : 'pill-neutral'">{{ schema ? '已解析' : (p.workspace_path ? '无 SQL' : '未生成') }}</span>
            </div>
            <div class="panel-bd stack">
              <div class="small"><span class="muted">库名</span> · <span class="mono">{{ p.db_name }}</span></div>
              <div class="small muted">SQL · sql/schema.sql · 约束 6~13 张表</div>
              <template v-if="schema?.tables?.length">
                <div class="small">当前 <strong>{{ schema.tables.length }}</strong> 张
                  <span :class="(schema.tables.length >= 6 && schema.tables.length <= 13) ? 'muted' : 'text-danger'">
                    （{{ schema.tables.length >= 6 && schema.tables.length <= 13 ? '符合' : '不符合' }} 6~13）
                  </span>
                </div>
                <div class="table-list">
                  <div v-for="t in schema.tables" :key="t.name" class="table-card">
                    <div class="table-card-hd">{{ t.name }}</div>
                    <ul class="table-cols">
                      <li v-for="c in t.columns" :key="c.name" :class="{ pk: c.pk, fk: c.fk }">
                        <span class="col-name">{{ c.name }}</span>
                        <span class="col-type muted">{{ c.type }}</span>
                        <span v-if="c.pk" class="col-mark">PK</span>
                        <span v-else-if="c.fk" class="col-mark">FK→{{ c.fk_table }}</span>
                      </li>
                    </ul>
                  </div>
                </div>
                <div v-if="schema.relations?.length" class="rel-list">
                  <div class="parse-sec-hd">推断联系</div>
                  <div v-for="(r, i) in schema.relations" :key="i" class="rel-row">
                    <span class="mono">{{ r.left }}</span>
                    <span class="muted">{{ r.card_left }}</span>
                    —〈{{ r.name }}〉—
                    <span class="muted">{{ r.card_right }}</span>
                    <span class="mono">{{ r.right }}</span>
                    <span class="small muted">via {{ r.via }}</span>
                  </div>
                </div>
                <div class="row">
                  <n-button size="small" @click="openEr">查看 E-R 图</n-button>
                  <n-button size="small" secondary @click="downloadEr">下载 SVG</n-button>
                </div>
              </template>
              <p v-else class="small muted">生成工作区后可查看表结构与 E-R 图。</p>
            </div>
          </div>
        </div>
        <div class="panel mt-16">
          <div class="panel-hd">
            <h3>质量门禁 · 交付 DoD</h3>
            <span class="pill" :class="canDownload ? 'pill-green' : 'pill-red'">{{ canDownload ? '可交付' : '禁止交付' }}</span>
          </div>
          <div class="panel-bd">
            <p class="small muted mb-12">P2 主流程或功能清单未过，禁止下载 ZIP。</p>
            <n-data-table :columns="gateCols" :data="gateRows" :bordered="false" size="small" />
          </div>
        </div>
        <div class="panel mt-16">
          <div class="panel-hd"><h3>开题对照清单</h3></div>
          <div class="panel-bd" style="padding:0">
            <n-data-table :columns="checkCols" :data="checkRows" :bordered="false" size="small" />
          </div>
        </div>
      </n-tab-pane>
    </n-tabs>

    <n-modal
      v-model:show="showDelete"
      preset="dialog"
      title="删除项目"
      positive-text="确认删除"
      negative-text="取消"
      type="error"
      :loading="deleting"
      @positive-click="confirmDelete"
      @negative-click="showDelete = false"
    >
      <p style="margin:0 0 12px">将清理工作区与 ZIP，此操作不可恢复。</p>
      <p v-if="p.db_name" class="small muted" style="margin:0 0 12px">
        学生库 <span class="mono">{{ p.db_name }}</span>
        {{ keepDb ? '将被保留' : '将一并删除' }}
      </p>
      <n-checkbox v-if="p.db_name" v-model:checked="keepDb">保留数据库（不执行 DROP）</n-checkbox>
    </n-modal>
    <n-modal v-model:show="showSpec" preset="card" title="spec.json" style="width:640px">
      <pre class="spec-preview" style="max-height:60vh">{{ specText }}</pre>
    </n-modal>
    <n-modal v-model:show="showEr" preset="card" title="E-R 图（线框）" style="width:min(1280px,96vw)">
      <div class="er-toolbar row mb-12">
        <span class="small muted">拖拽平移 · 滚轮缩放 · 菱形联系 · 方框实体 · 椭圆属性</span>
        <div class="er-zoom-btns row">
          <n-button size="small" @click="erZoomOut">缩小</n-button>
          <span class="er-zoom-label">{{ Math.round(erScale * 100) }}%</span>
          <n-button size="small" @click="erZoomIn">放大</n-button>
          <n-button size="small" @click="erZoomReset">重置</n-button>
          <n-button size="small" type="primary" @click="downloadEr">下载 SVG</n-button>
        </div>
      </div>
      <div
        ref="erFrameRef"
        class="er-frame"
        @wheel.prevent="onErWheel"
        @pointerdown="onErPointerDown"
        @pointermove="onErPointerMove"
        @pointerup="onErPointerUp"
        @pointercancel="onErPointerUp"
        @pointerleave="onErPointerUp"
      >
        <div class="er-canvas" :style="erCanvasStyle" v-html="erSvgHtml" />
      </div>
    </n-modal>
  </div>
  <ErrorPage
    v-else-if="loadError"
    :code="loadErrorCode"
    :title="loadErrorCode === 404 ? '项目不存在' : '加载失败'"
    :description="loadErrorCode === 404
      ? '该项目 ID 在本机工作区中找不到，可能已被删除或链接有误。'
      : '拉取项目详情时出错，可重试或返回项目列表。'"
    :detail="loadError"
    retryable
    @retry="reload"
  />
  <PageSkeleton v-else variant="detail" />
</template>

<script setup>
import { computed, h, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NTag } from 'naive-ui'
import { api, message } from '../api'
import ErrorPage from './ErrorPage.vue'
import PageSkeleton from '../components/PageSkeleton.vue'
import {
  CHECKLIST_RESULT,
  LOG_SIDES,
  defaultTabForStatus,
  detailCrumb,
  getCatalog,
  projectStatusLabel,
  projectStatusPill,
} from '../opsShared'

const route = useRoute()
const router = useRouter()
const p = ref(null)
const loadError = ref('')
const loadErrorCode = ref(500)
const tab = ref('match')
const catalog = ref({ archetypes: [], domains: [], themes_by_domain: {} })
const form = reactive({ archetype: '', domain: '', theme: '', llm: 'on', passwordHash: 'none' })
const ack = ref(false)
const unlocked = ref(false)
const currentJob = ref(null)
const rt = reactive({
  backend_status: 'stopped',
  frontend_status: 'stopped',
  preview_url: null,
  backend_url: null,
  backend_log_tail: '',
  frontend_log_tail: '',
})
const rtBusyBe = ref(false)
const rtBusyFe = ref(false)
const rtPendingAll = ref('')
const rtAnyBusy = computed(() => rtBusyBe.value || rtBusyFe.value)
const rtAllBusy = computed(() => rtBusyBe.value && rtBusyFe.value)
const logSide = ref('job')
const logText = ref('')
const logFilter = ref('')
const logSides = LOG_SIDES
const showSpec = ref(false)
const showEr = ref(false)
const showDelete = ref(false)
const keepDb = ref(false)
const deleting = ref(false)
const schema = ref(null)
const erSvgHtml = ref('')
const erFrameRef = ref(null)
const erScale = ref(1)
const erPanX = ref(0)
const erPanY = ref(0)
const erDragging = ref(false)
let erLastX = 0
let erLastY = 0
let pollTimer = null

const erCanvasStyle = computed(() => ({
  transform: `translate(${erPanX.value}px, ${erPanY.value}px) scale(${erScale.value})`,
  transformOrigin: '0 0',
}))

const ER_SCALE_MIN = 0.25
const ER_SCALE_MAX = 4
const ER_SCALE_STEP = 0.15

function erClampScale(s) {
  return Math.min(ER_SCALE_MAX, Math.max(ER_SCALE_MIN, s))
}

function erZoomIn() {
  erScale.value = erClampScale(erScale.value + ER_SCALE_STEP)
}

function erZoomOut() {
  erScale.value = erClampScale(erScale.value - ER_SCALE_STEP)
}

function erZoomReset() {
  erScale.value = 1
  erPanX.value = 0
  erPanY.value = 0
}

function onErWheel(e) {
  const frame = erFrameRef.value
  if (!frame) return
  const rect = frame.getBoundingClientRect()
  const mx = e.clientX - rect.left
  const my = e.clientY - rect.top
  const prev = erScale.value
  const next = erClampScale(prev * (e.deltaY < 0 ? 1.1 : 1 / 1.1))
  if (next === prev) return
  // 以光标为缩放中心
  const wx = (mx - erPanX.value) / prev
  const wy = (my - erPanY.value) / prev
  erScale.value = next
  erPanX.value = mx - wx * next
  erPanY.value = my - wy * next
}

function onErPointerDown(e) {
  if (e.button !== 0) return
  erDragging.value = true
  erLastX = e.clientX
  erLastY = e.clientY
  e.currentTarget.setPointerCapture?.(e.pointerId)
}

function onErPointerMove(e) {
  if (!erDragging.value) return
  erPanX.value += e.clientX - erLastX
  erPanY.value += e.clientY - erLastY
  erLastX = e.clientX
  erLastY = e.clientY
}

function onErPointerUp(e) {
  erDragging.value = false
  try {
    e.currentTarget?.releasePointerCapture?.(e.pointerId)
  } catch {
    /* ignore */
  }
}

const planSteps = [
  { t: '解析开题 → 合并 Spec', m: '匹配阶段' },
  { t: '复制骨架 · 写入领域 SQL', m: '确定性 bake' },
  { t: '业务岛 emit · LLM 填缺口', m: '白名单文件' },
  { t: '构建验证', m: 'P0' },
  { t: '门禁：登录 + 主流程 E2E', m: 'P1 / P2' },
  { t: '开题对照 · 打包 ZIP', m: '仅门禁全过' },
]

const archOptions = computed(() => catalog.value.archetypes.map((x) => ({ label: x.label, value: x.id })))
const domOptions = computed(() => catalog.value.domains.map((x) => ({ label: x.label, value: x.id })))
const themeOptions = computed(() => {
  const list = catalog.value.themes_by_domain?.[form.domain] || []
  return list.map((x) => ({ label: x.label, value: x.id }))
})
const passwordHashOptions = [
  { label: '明文', value: 'none' },
  { label: 'BCrypt', value: 'bcrypt' },
  { label: 'MD5', value: 'md5' },
  { label: 'SHA-256', value: 'sha256' },
]
const llmOptions = [
  { label: '开启 · 白名单插槽填充', value: 'on' },
  { label: '关闭 · 仅确定性 bake', value: 'off' },
]

const deviant = computed(() => {
  if (!p.value) return false
  return form.archetype !== p.value.recommended_arch || form.domain !== p.value.recommended_domain
})
const displayConf = computed(() => (deviant.value ? 0.41 : (p.value?.confidence || 0)))
const matchPillClass = computed(() => {
  if (deviant.value) return 'pill-red'
  if (unlocked.value) return 'pill-amber'
  return 'pill-green'
})
const matchPillText = computed(() => {
  if (deviant.value) return '已偏离推荐'
  if (unlocked.value) return '已解锁'
  return '已锁定推荐'
})
const confirmHint = computed(() => {
  if (deviant.value) return '确认按当前骨架 / 领域生成。'
  return '已核对骨架、领域与砍项，确认后开始生成。'
})
const canDownload = computed(() => !!(p.value?.zip_ready && p.value?.gates?.zip_allowed && p.value?.gates?.overall))

const deleteBlocked = computed(() => {
  if (!p.value) return true
  if (p.value.status === 'running' || p.value.status === 'generating') return true
  if (p.value.backend_running || p.value.frontend_running) return true
  const be = rt.backend_status
  const fe = rt.frontend_status
  if (['starting', 'healthy', 'stopping'].includes(be) || ['starting', 'healthy', 'stopping'].includes(fe)) {
    return true
  }
  return false
})
const deleteBlockedReason = computed(() =>
  deleteBlocked.value ? '项目运行中或正在生成，请先停止后再删除' : '',
)

function runtimeStatusLabel(st) {
  return ({
    stopped: '已停止',
    starting: '启动中',
    stopping: '停止中',
    healthy: '健康',
    error: '异常',
  })[st] || st || '已停止'
}
function runtimeStatusPill(st) {
  return ({
    stopped: 'pill-neutral',
    starting: 'pill-amber',
    stopping: 'pill-amber',
    healthy: 'pill-green',
    error: 'pill-red',
  })[st] || 'pill-neutral'
}
function runtimeCanStop(st) {
  return st === 'healthy' || st === 'starting' || st === 'stopping'
}
function runtimeTransient(st) {
  return st === 'starting' || st === 'stopping'
}
/** 状态只在 pill；这里只展示真实日志，占位文案一律收成 — */
function runtimeLogView(st, tail) {
  if (st === 'stopped' || st === 'stopping') return '—'
  if (!tail || /^(后端|前端)?(启动|停止)中/.test(String(tail).trim())) return '—'
  return _tailLines(tail, st === 'error' ? 12 : 8)
}
function _tailLines(tail, keep) {
  const lines = String(tail).split(/\r?\n/).filter((l) => l.trim())
  return lines.slice(-keep).join('\n') || '—'
}

const statusLabel = computed(() => projectStatusLabel(p.value?.status))
const statusPill = computed(() => projectStatusPill(p.value?.status))

const genState = computed(() => {
  if (!p.value) return 'idle'
  if (p.value.status === 'generating') return 'running'
  if (p.value.status === 'running') return 'live'
  if (p.value.status === 'generated') return 'success'
  if (p.value.status === 'failed') return 'failed'
  return 'idle'
})

const specText = computed(() => JSON.stringify(p.value?.spec || {}, null, 2))
const proposal = computed(() => p.value?.spec?.proposal || {})
const filteredLog = computed(() => {
  const q = logFilter.value.trim().toLowerCase()
  if (!q) return logText.value || '（无日志）'
  return logText.value.split('\n').filter((l) => l.toLowerCase().includes(q)).join('\n') || '（无匹配）'
})

const gateCols = [
  { title: '级别', key: 'level', width: 80, render: (r) => h(NTag, { size: 'small', bordered: false }, { default: () => r.level }) },
  { title: '检查项', key: 'label' },
  { title: '结果', key: 'ok', width: 100, render: (r) => h(NTag, { size: 'small', type: r.ok ? 'success' : 'error', bordered: false }, { default: () => (r.ok ? '通过' : '未通过') }) },
  { title: '说明', key: 'desc' },
]
const gateRows = computed(() => {
  const g = p.value?.gates || {}
  const keys = ['p0a', 'p0b', 'p1', 'p2', 'p3a', 'p3b', 'p3t']
  const levels = { p0a: 'P0', p0b: 'P0', p1: 'P1', p2: 'P2', p3a: 'P3', p3b: 'P3', p3t: 'P3' }
  return keys.map((k) => ({
    key: k,
    level: levels[k],
    label: g[k]?.label || k,
    ok: !!g[k]?.ok,
    desc: g[k]?.desc || '',
  }))
})
const checkCols = [
  { title: '开题功能', key: 'name' },
  {
    title: '实现状态',
    key: 'result',
    render: (r) => {
      const m = CHECKLIST_RESULT[r.result] || CHECKLIST_RESULT.pending
      return h(NTag, { size: 'small', type: m.type, bordered: false }, { default: () => m.label })
    },
  },
  { title: '说明', key: 'status' },
]
const checkRows = computed(() => (p.value?.checklist || []).map((x) => ({
  name: x.name,
  result: x.result || (x.status === 'out_of_mvp' ? 'out_of_mvp' : 'pending'),
  status: x.status,
})))

function formatSize(n) {
  if (!n) return '—'
  if (n < 1024) return n + ' B'
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + ' KB'
  return (n / 1024 / 1024).toFixed(1) + ' MB'
}

async function load({ syncTab = false, lite = false } = {}) {
  const id = route.params.id
  loadError.value = ''
  try {
    if (!lite && !catalog.value.archetypes.length) {
      catalog.value = await getCatalog()
    }
    p.value = await api.getProject(id)
    detailCrumb.value = p.value.title || ''
    if (!lite) {
      form.archetype = p.value.archetype
      form.domain = p.value.domain
      form.theme = p.value.theme
      form.llm = p.value.llm_enabled ? 'on' : 'off'
      form.passwordHash = p.value.password_hash || 'none'
      unlocked.value = !p.value.match_locked
      ack.value = p.value.match_confirmed
    }
    // 仅进入/切项目时同步主 tab；轮询禁止强切，否则无法停在日志页
    if (syncTab) tab.value = defaultTabForStatus(p.value.status)
    if (!lite && p.value.workspace_path && tab.value === 'runtime') await refreshRuntime()
    await refreshJob()
    // schema 只在产物 Tab 拉，避免生成轮询疯狂刷 /schema
    if (!lite && tab.value === 'artifacts') await loadSchema()
  } catch (e) {
    if (!lite) {
      p.value = null
      detailCrumb.value = ''
      const status = e?.response?.status
      loadErrorCode.value = status === 404 ? 404 : 500
      const detail = e?.response?.data?.detail
      loadError.value = (typeof detail === 'string' ? detail : '') || e?.message || '加载失败'
    }
  }
}

async function reload() {
  stopPoll()
  await load({ syncTab: true })
  if (p.value?.status === 'generating') startPoll()
}

async function loadSchema() {
  if (!p.value?.workspace_path) {
    schema.value = null
    return
  }
  try {
    schema.value = await api.getSchema(p.value.id)
  } catch {
    schema.value = null
  }
}

async function openEr() {
  if (!p.value) return
  const res = await fetch(`${api.erSvgUrl(p.value.id)}?t=${Date.now()}`)
  if (!res.ok) {
    message.error('无法加载 E-R 图')
    return
  }
  const raw = await res.text()
  erSvgHtml.value = raw.replace(/^<\?xml[^>]*>\s*/i, '')
  erZoomReset()
  showEr.value = true
}

function downloadEr() {
  if (!p.value) return
  const a = document.createElement('a')
  a.href = `${api.erSvgUrl(p.value.id)}?t=${Date.now()}`
  a.download = `${p.value.id}-er.svg`
  a.click()
}

async function refreshJob() {
  const jobs = await api.listJobs()
  currentJob.value = jobs.find((j) => j.project_id === route.params.id) || null
}

async function refreshRuntime() {
  const data = await api.runtime(route.params.id)
  rt.preview_url = data.preview_url || null
  rt.backend_url = data.backend_url || null
  rt.backend_log_tail = data.backend_log_tail || ''
  rt.frontend_log_tail = data.frontend_log_tail || ''
  const be = data.backend_status || 'stopped'
  const fe = data.frontend_status || 'stopped'
  // 仅忙碌的那一侧保留中间态，另一侧照常刷新
  if (rtBusyBe.value) {
    if (rt.backend_status === 'stopping') {
      rt.backend_status = be === 'stopped' ? 'stopped' : 'stopping'
    } else if (rt.backend_status === 'starting') {
      rt.backend_status = be === 'stopped' ? 'starting' : be
    } else {
      rt.backend_status = be
    }
  } else {
    rt.backend_status = be
  }
  if (rtBusyFe.value) {
    if (rt.frontend_status === 'stopping') {
      rt.frontend_status = fe === 'stopped' ? 'stopped' : 'stopping'
    } else if (rt.frontend_status === 'starting') {
      rt.frontend_status = fe === 'stopped' ? 'starting' : fe
    } else {
      rt.frontend_status = fe
    }
  } else {
    rt.frontend_status = fe
  }
}

async function toggleUnlock() {
  if (!unlocked.value) {
    if (!confirm('解锁后可改骨架/领域。确认解锁？')) return
    await api.patchMatch(p.value.id, { unlock: true })
    unlocked.value = true
    message.success('已解锁')
  } else {
    if (deviant.value) {
      message.warning('已偏离推荐，请先恢复推荐再锁定')
      return
    }
    await api.patchMatch(p.value.id, { unlock: false })
    unlocked.value = false
    message.success('已重新锁定')
  }
  await load()
}

async function resetMatch() {
  p.value = await api.patchMatch(p.value.id, { reset: true })
  form.archetype = p.value.archetype
  form.domain = p.value.domain
  form.theme = p.value.theme
  form.passwordHash = p.value.password_hash || 'none'
  unlocked.value = false
  ack.value = false
  message.success('已恢复推荐')
}

async function onArchDomChange() {
  try {
    p.value = await api.patchMatch(p.value.id, {
      archetype: form.archetype,
      domain: form.domain,
    })
    form.theme = p.value.theme
    ack.value = false
  } catch {
    form.archetype = p.value.archetype
    form.domain = p.value.domain
    form.theme = p.value.theme
  }
}

async function saveSoft() {
  p.value = await api.patchMatch(p.value.id, {
    theme: form.theme,
    llm_enabled: form.llm === 'on',
    password_hash: form.passwordHash,
  })
  message.success('已保存')
}

async function confirmMatch() {
  if (deviant.value && !confirm('当前已偏离系统推荐。确认仍要用这套骨架/领域生成？')) return
  p.value = await api.patchMatch(p.value.id, { confirm: true, ack: true })
  unlocked.value = false
  message.success(deviant.value ? '已按覆盖确认' : '已确认匹配')
  tab.value = 'generate'
}

async function startGenerate() {
  const res = await api.generate(p.value.id)
  message.success(res.message)
  await load()
  tab.value = 'generate'
  startPoll()
}

async function cancelCurrent() {
  if (!currentJob.value) return
  await api.cancelJob(currentJob.value.id)
  message.success('已取消')
  await load()
}

async function retryCurrent() {
  if (!currentJob.value) {
    await startGenerate()
    return
  }
  await api.retryJob(currentJob.value.id)
  message.success('已重试')
  await load()
  startPoll()
}

function downloadZip() {
  if (!canDownload.value) {
    message.error('门禁未过 · 禁止下载 ZIP')
    tab.value = 'artifacts'
    return
  }
  window.open(api.downloadUrl(p.value.id), '_blank')
}

function onDelete() {
  if (deleteBlocked.value) {
    message.warning(deleteBlockedReason.value || '请先停止运行后再删除')
    return
  }
  keepDb.value = false
  showDelete.value = true
}

async function confirmDelete() {
  if (!p.value || deleting.value) return false
  deleting.value = true
  try {
    const res = await api.deleteProject(p.value.id, { keepDb: keepDb.value })
    message.success(res?.message || '已删除')
    showDelete.value = false
    router.push('/')
    return true
  } catch (e) {
    message.error(e?.response?.data?.detail || e?.message || '删除失败')
    return false
  } finally {
    deleting.value = false
  }
}

async function rtAction(side, action) {
  const touchBe = side === 'all' || side === 'backend'
  const touchFe = side === 'all' || side === 'frontend'
  if ((touchBe && rtBusyBe.value) || (touchFe && rtBusyFe.value)) return
  if (touchBe) rtBusyBe.value = true
  if (touchFe) rtBusyFe.value = true
  if (side === 'all') rtPendingAll.value = action

  if (action === 'start' || action === 'restart') {
    if (touchBe) rt.backend_status = 'starting'
    if (touchFe) rt.frontend_status = 'starting'
  } else if (action === 'stop') {
    if (touchBe) rt.backend_status = 'stopping'
    if (touchFe) rt.frontend_status = 'stopping'
  }
  try {
    await api.runtimeAction(p.value.id, side, action)
    await load()
    const deadline = Date.now() + (action === 'stop' ? 8000 : 20000)
    while (Date.now() < deadline && tab.value === 'runtime') {
      await refreshRuntime()
      if (_runtimeSettled(side, action)) break
      await new Promise((r) => setTimeout(r, 700))
    }
  } finally {
    if (touchBe) rtBusyBe.value = false
    if (touchFe) rtBusyFe.value = false
    if (side === 'all') rtPendingAll.value = ''
    if (tab.value === 'runtime') await refreshRuntime()
  }
}

function _runtimeSettled(side, action) {
  const be = rt.backend_status
  const fe = rt.frontend_status
  const beDone = be !== 'starting' && be !== 'stopping'
  const feDone = fe !== 'starting' && fe !== 'stopping'
  if (side === 'backend') return beDone
  if (side === 'frontend') return feDone
  if (action === 'stop') return be === 'stopped' && fe === 'stopped'
  return beDone && feDone
}

function openPreview() {
  if (rt.preview_url) {
    window.open(rt.preview_url, '_blank')
    return
  }
  message.warning('前端未就绪，请先启动并等待健康')
}

let logReqSeq = 0
async function loadLog(side) {
  logSide.value = side
  const seq = ++logReqSeq
  const res = await api.logs(p.value.id, side)
  if (seq !== logReqSeq || logSide.value !== side) return
  logText.value = res.content || ''
}

let pollInFlight = false

function startPoll() {
  stopPoll()
  pollTimer = setInterval(async () => {
    if (pollInFlight) return
    pollInFlight = true
    try {
      // 轻量轮询：只刷项目状态/Job/日志，不拉 catalog/schema
      await load({ syncTab: false, lite: true })
      if (tab.value === 'logs') await loadLog(logSide.value)
      if (!p.value || p.value.status !== 'generating') {
        stopPoll()
        // 结束后补一次完整刷新；人在日志/产物页则不强切 Tab
        if (p.value) {
          const keepTab = tab.value === 'logs' || tab.value === 'artifacts'
          await load({ syncTab: !keepTab, lite: false })
        }
      }
    } finally {
      pollInFlight = false
    }
  }, 1500)
}

function stopPoll() {
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = null
  pollInFlight = false
}

watch(tab, (v) => {
  if (v === 'logs') loadLog(logSide.value)
  if (v === 'runtime') refreshRuntime()
  if (v === 'artifacts') loadSchema()
})

watch(
  () => route.params.id,
  async (id, prev) => {
    if (!id || id === prev) return
    stopPoll()
    p.value = null
    loadError.value = ''
    await reload()
  },
)

onMounted(reload)
onUnmounted(() => {
  stopPoll()
  detailCrumb.value = ''
})
</script>

<style scoped>
.er-toolbar {
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.er-zoom-btns {
  align-items: center;
  gap: 8px;
}
.er-zoom-label {
  min-width: 48px;
  text-align: center;
  font-variant-numeric: tabular-nums;
  font-size: 13px;
  color: #555;
}
.text-danger {
  color: #d03050;
}
.er-frame {
  height: 72vh;
  overflow: hidden;
  border: 1px solid #e5e5e5;
  background: #fafafa;
  cursor: grab;
  touch-action: none;
  user-select: none;
}
.er-frame:active {
  cursor: grabbing;
}
.er-canvas {
  display: inline-block;
  will-change: transform;
}
.er-canvas :deep(svg) {
  display: block;
  max-width: none;
  height: auto;
  pointer-events: none;
}
</style>
