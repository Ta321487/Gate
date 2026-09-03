<template>
  <div class="defense-ppt-launch">
    <!-- 生成中 -->
    <template v-if="pptPhase === 'generating'">
      <div class="panel mb-16 mt-16">
        <div class="panel-bd">
          <div class="row-between" style="margin-bottom:10px">
            <div style="font-weight:600">正在生成答辩 PPT…</div>
            <div class="small muted">
              任务 #{{ pptJob?.id || '—' }} · {{ pptJob?.progress || 0 }}%
            </div>
          </div>
          <div class="progress" style="height:8px">
            <i :style="{ width: (pptJob?.progress || 0) + '%' }" />
          </div>
          <div class="row mt-12" style="gap:8px">
            <n-button
              size="small"
              type="error"
              secondary
              :loading="pptActing === 'cancel'"
              @click="cancelPptGenerate"
            >
              取消
            </n-button>
            <n-button size="small" @click="tab = 'logs'">日志</n-button>
          </div>
        </div>
      </div>

      <div v-if="pptJob?.steps?.length" class="panel mb-16">
        <div class="panel-hd">
          <h3>生成进度</h3>
        </div>
        <div class="panel-bd">
          <ol class="step-rail">
            <li
              v-for="s in pptJob.steps"
              :key="s.key"
              :class="normalizeStepStatus(s.status)"
            >
              <div class="step-rail-track" aria-hidden="true">
                <span class="step-ico">{{ stepStatusMark(s.status) }}</span>
              </div>
              <div class="step-body">
                <div class="step-title">{{ s.title }}</div>
                <div class="meta">{{ s.meta || stepStatusLabel(s.status) }}</div>
              </div>
            </li>
          </ol>
        </div>
      </div>

      <div v-if="pptJob?.units?.length" class="panel mb-16">
        <div class="panel-hd"><h3>页面单元</h3></div>
        <div class="panel-bd">
          <ul class="ppt-unit-list">
            <li v-for="u in pptJob.units" :key="u.key">
              <span>{{ u.title || u.key }}</span>
              <span class="pill" :class="unitPill(u.status)">{{ unitLabel(u.status) }}</span>
            </li>
          </ul>
        </div>
      </div>
    </template>

    <!-- 未解锁 -->
    <div v-else-if="pptPhase === 'locked'" class="panel mt-16">
      <div class="panel-hd">
        <h3 class="soft-label-with-tip">
          答辩 PPT
          <n-tooltip trigger="hover" placement="bottom-start" :delay="120">
            <template #trigger>
              <button type="button" class="soft-tip-btn" aria-label="功能说明">
                <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
                  <path
                    fill="currentColor"
                    d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm0 15a1.1 1.1 0 1 1 0-2.2A1.1 1.1 0 0 1 12 17zm1.2-4.4h-2.4V7h2.4v5.6z"
                  />
                </svg>
              </button>
            </template>
            <div class="ppt-help-tip">
              <div class="soft-visual-tip-title">终期答辩幻灯片</div>
              <p class="small muted" style="margin:0">
                在程序通过质量检查后，单独生成可编辑的 .pptx。内容只整理开题与实包已有材料，不编造能力。
              </p>
            </div>
          </n-tooltip>
        </h3>
        <span class="pill pill-neutral">暂不可用</span>
      </div>
      <div class="panel-bd">
        <p class="small muted" style="margin:0 0 12px">
          请先完成工程生成并通过质量检查（与下载 ZIP 同一标准）。通过后可在此填写封面并生成答辩稿。
        </p>
        <n-button type="primary" disabled>生成答辩 PPT</n-button>
      </div>
    </div>

    <!-- 可生成 -->
    <div v-else-if="pptPhase === 'ready'" class="panel mt-16">
      <div class="panel-hd">
        <h3 class="soft-label-with-tip">
          答辩 PPT
          <n-tooltip trigger="hover" placement="bottom-start" :delay="120">
            <template #trigger>
              <button type="button" class="soft-tip-btn" aria-label="预览当前样式">
                <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
                  <path
                    fill="currentColor"
                    d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm0 15a1.1 1.1 0 1 1 0-2.2A1.1 1.1 0 0 1 12 17zm1.2-4.4h-2.4V7h2.4v5.6z"
                  />
                </svg>
              </button>
            </template>
            <div class="ppt-style-tip">
              <div class="soft-visual-tip-title">当前样式示意</div>
              <div
                class="ppt-style-wire"
                :data-layout="pptSkin.layout_family || 'band'"
                :style="styleWireVars"
              >
                <div class="ppt-style-wire-band" aria-hidden="true" />
                <div class="ppt-style-wire-body">
                  <div class="ppt-style-wire-kicker">学校 · 学院</div>
                  <div class="ppt-style-wire-title">毕业设计答辩</div>
                  <div class="ppt-style-wire-meta">班级 · 姓名 · 学号</div>
                  <div class="ppt-style-wire-lines">
                    <i /><i /><i class="short" />
                  </div>
                </div>
              </div>
              <p class="small muted" style="margin:8px 0 0">
                {{ themeLabel }} · {{ layoutLabel }}
              </p>
              <p class="small muted" style="margin:4px 0 0">
                换主题/版式只改外观，不标为与工程不一致。
              </p>
            </div>
          </n-tooltip>
        </h3>
        <span class="pill pill-green">可生成</span>
      </div>
      <div class="panel-bd">
        <p class="small muted" style="margin:0 0 12px">
          为终期答辩生成可编辑的 PPTX。大纲固定，业务文案跟开题与实包，图从产物嵌入。
        </p>

        <div class="ppt-evidence mb-12">
          <span class="pill" :class="pptEvidence.proposal ? 'pill-green' : 'pill-red'">开题{{ pptEvidence.proposal ? '✓' : '✕' }}</span>
          <span class="pill" :class="pptEvidence.modules ? 'pill-green' : 'pill-red'">模块图{{ pptEvidence.modules ? '✓' : '✕' }}</span>
          <span class="pill" :class="pptEvidence.er ? 'pill-green' : 'pill-red'">E-R{{ pptEvidence.er ? '✓' : '✕' }}</span>
          <span class="pill" :class="pptEvidence.testcases ? 'pill-green' : 'pill-red'">用例{{ pptEvidence.testcases ? '✓' : '✕' }}</span>
          <span class="pill" :class="pptEvidence.gates_overall ? 'pill-green' : 'pill-red'">质量检查{{ pptEvidence.gates_overall ? '✓' : '✕' }}</span>
        </div>

        <div class="grid-3 mb-12" style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px">
          <div>
            <label class="field-label soft-label-with-tip">
              主题包
              <n-tooltip trigger="hover" placement="top" :delay="100">
                <template #trigger>
                  <button type="button" class="soft-tip-btn" aria-label="预览主题">
                    <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
                      <path
                        fill="currentColor"
                        d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm0 15a1.1 1.1 0 1 1 0-2.2A1.1 1.1 0 0 1 12 17zm1.2-4.4h-2.4V7h2.4v5.6z"
                      />
                    </svg>
                  </button>
                </template>
                <div class="ppt-style-tip">
                  <div class="soft-visual-tip-title">主题色板</div>
                  <div class="ppt-swatch-row">
                    <span class="ppt-swatch" :style="{ background: styleWireVars['--ppt-accent'] }" />
                    <span class="ppt-swatch" :style="{ background: styleWireVars['--ppt-soft'] }" />
                    <span class="ppt-swatch" :style="{ background: styleWireVars['--ppt-ink'] }" />
                  </div>
                  <p class="small muted" style="margin:8px 0 0">{{ themeLabel }}</p>
                </div>
              </n-tooltip>
            </label>
            <n-select v-model:value="pptSkin.theme" :options="themeSelectOpts" />
          </div>
          <div>
            <label class="field-label soft-label-with-tip">
              版式族
              <n-tooltip trigger="hover" placement="top" :delay="100">
                <template #trigger>
                  <button type="button" class="soft-tip-btn" aria-label="预览版式">
                    <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
                      <path
                        fill="currentColor"
                        d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm0 15a1.1 1.1 0 1 1 0-2.2A1.1 1.1 0 0 1 12 17zm1.2-4.4h-2.4V7h2.4v5.6z"
                      />
                    </svg>
                  </button>
                </template>
                <div class="ppt-style-tip">
                  <div class="soft-visual-tip-title">版式示意</div>
                  <div
                    class="ppt-style-wire"
                    :data-layout="pptSkin.layout_family || 'band'"
                    :style="styleWireVars"
                  >
                    <div class="ppt-style-wire-band" aria-hidden="true" />
                    <div class="ppt-style-wire-body">
                      <div class="ppt-style-wire-title">标题区</div>
                      <div class="ppt-style-wire-lines"><i /><i class="short" /></div>
                    </div>
                  </div>
                  <p class="small muted" style="margin:8px 0 0">{{ layoutLabel }}</p>
                </div>
              </n-tooltip>
            </label>
            <n-select v-model:value="pptSkin.layout_family" :options="layoutSelectOpts" />
          </div>
          <div>
            <label class="field-label">学院母版</label>
            <n-select v-model:value="pptSkin.master" :options="masterSelectOpts" />
          </div>
        </div>

        <p class="small muted mb-12">
          封面页会写入下列身份信息；缺任一项时无法开始生成。
        </p>

        <DefensePptCoverFields v-model="pptCover" />

        <p class="small muted mb-12" style="margin-top:12px">
          {{ pptCoverComplete ? '封面已齐，可以生成。' : '请补全学校、学院、班级、姓名、学号、导师与校徽。' }}
        </p>

        <div class="row" style="justify-content:flex-end;gap:8px;flex-wrap:wrap">
          <n-button
            type="primary"
            size="large"
            :disabled="!pptCanGenerate"
            :loading="pptActing === 'generate'"
            @click="startPptGenerate"
          >
            生成答辩 PPT
          </n-button>
        </div>
      </div>
    </div>

    <!-- 已有 deck -->
    <div v-else-if="pptHasDeck" class="panel mt-16">
      <div class="panel-hd">
        <h3 class="soft-label-with-tip">
          答辩 PPT
          <n-tooltip trigger="hover" placement="bottom-start" :delay="120">
            <template #trigger>
              <button type="button" class="soft-tip-btn" aria-label="预览当前样式">
                <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
                  <path
                    fill="currentColor"
                    d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm0 15a1.1 1.1 0 1 1 0-2.2A1.1 1.1 0 0 1 12 17zm1.2-4.4h-2.4V7h2.4v5.6z"
                  />
                </svg>
              </button>
            </template>
            <div class="ppt-style-tip">
              <div class="soft-visual-tip-title">当前样式示意</div>
              <div
                class="ppt-style-wire"
                :data-layout="pptSkin.layout_family || 'band'"
                :style="styleWireVars"
              >
                <div class="ppt-style-wire-band" aria-hidden="true" />
                <div class="ppt-style-wire-body">
                  <div class="ppt-style-wire-kicker">学校 · 学院</div>
                  <div class="ppt-style-wire-title">毕业设计答辩</div>
                  <div class="ppt-style-wire-lines"><i /><i /><i class="short" /></div>
                </div>
              </div>
              <p class="small muted" style="margin:8px 0 0">{{ themeLabel }} · {{ layoutLabel }}</p>
            </div>
          </n-tooltip>
        </h3>
        <span class="pill" :class="pptBizDirty ? 'pill-amber' : 'pill-green'">
          {{ pptBizDirty ? '需与工程对齐' : '已生成' }}
        </span>
      </div>
      <div class="panel-bd">
        <p class="small muted" style="margin:0 0 12px">
          {{ pptDeckSummary || '已生成' }} · {{ pptFingerprintHint }}。
          可在对照里改要点、换皮；导出前请通过检查。
        </p>
        <div class="row" style="gap:8px;flex-wrap:wrap">
          <n-button size="small" type="primary" @click="openPptCompare">打开对照</n-button>
          <n-button size="small" :loading="pptActing === 'check'" @click="runPptCheck">检查</n-button>
          <n-button
            size="small"
            :disabled="!pptCanExport && pptBizDirty"
            :loading="pptActing === 'export'"
            @click="exportPptx"
          >
            导出 PPTX
          </n-button>
          <n-button
            size="small"
            secondary
            :disabled="!pptCanGenerate"
            :loading="pptActing === 'generate'"
            @click="startPptGenerate"
          >
            重新生成
          </n-button>
        </div>
      </div>
    </div>

    <DefensePptCheckModal
      v-model:show="showPptCheck"
      :result="pptCheckResult"
      :exporting="pptActing === 'export'"
      :can-export="pptCanExport"
      @export="exportPptx"
    />
  </div>
</template>

<script setup>
import { computed, unref } from 'vue'
import { bindPd } from '../../views/projectDetail/bindPd'
import {
  PPT_THEME_OPTIONS,
  PPT_LAYOUT_OPTIONS,
  PPT_MASTER_OPTIONS,
  pptThemeMeta,
  pptLayoutMeta,
} from '../../ppt/deckDefaults.js'
import DefensePptCoverFields from './DefensePptCoverFields.vue'
import DefensePptCheckModal from './DefensePptCheckModal.vue'

const {
  tab,
  pptPhase,
  pptJob,
  pptActing,
  pptEvidence,
  pptSkin,
  pptCover,
  pptCoverComplete,
  pptCanGenerate,
  pptHasDeck,
  pptBizDirty,
  pptDeckSummary,
  pptFingerprintHint,
  pptCanExport,
  pptCheckResult,
  showPptCheck,
  normalizeStepStatus,
  stepStatusMark,
  stepStatusLabel,
  cancelPptGenerate,
  startPptGenerate,
  openPptCompare,
  runPptCheck,
  exportPptx,
} = bindPd()

const themeSelectOpts = computed(() =>
  PPT_THEME_OPTIONS.map((o) => ({ label: o.label, value: o.value })),
)
const layoutSelectOpts = computed(() =>
  PPT_LAYOUT_OPTIONS.map((o) => ({ label: o.label, value: o.value })),
)
const masterSelectOpts = computed(() =>
  PPT_MASTER_OPTIONS.map((o) => ({ label: o.label, value: o.value })),
)

const themeMeta = computed(() => pptThemeMeta(unref(pptSkin)?.theme))
const layoutMeta = computed(() => pptLayoutMeta(unref(pptSkin)?.layout_family))
const themeLabel = computed(() => themeMeta.value.label)
const layoutLabel = computed(() => layoutMeta.value.label)

const styleWireVars = computed(() => {
  const t = themeMeta.value
  return {
    '--ppt-accent': t.accent,
    '--ppt-soft': t.soft,
    '--ppt-ink': t.ink,
  }
})

function unitPill(status) {
  if (status === 'done') return 'pill-green'
  if (status === 'generating' || status === 'running') return 'pill-teal'
  if (status === 'failed') return 'pill-red'
  return 'pill-neutral'
}

function unitLabel(status) {
  if (status === 'done') return '完成'
  if (status === 'generating' || status === 'running') return '生成中'
  if (status === 'failed') return '失败'
  if (status === 'queued') return '排队'
  return status || '—'
}
</script>

<style scoped>
.field-label {
  display: block;
  font-size: 13px;
  margin-bottom: 6px;
  color: var(--ink-2);
}
@media (max-width: 900px) {
  .grid-3 { grid-template-columns: 1fr !important; }
}
</style>
