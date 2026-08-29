<template>
  <div>
    <div class="file-row">
      <span>源材料：<strong>{{ p.source_filename }}</strong> · {{ formatSize(p.source_size) }}</span>
      <n-button text size="small" @click="$router.push('/')">另建项目</n-button>
    </div>
    <div class="banner success">
      <h4>{{ alreadyBaked ? '工程已生成' : '推荐匹配已给出' }}</h4>
      <p class="small muted">
        {{ alreadyBaked
          ? '改骨架 / 领域 / 持久层须先解锁。改配色、布局等视觉选项请到「一键生成」。'
          : '确认后到「一键生成」调整视觉并开跑。如需调整骨架、领域或持久层，请先解锁。' }}
      </p>
    </div>
    <div v-if="matchWarnings.length" class="banner warn">
      <h4>匹配说明</h4>
      <ul class="warn-list">
        <li v-for="(w, i) in matchWarnings" :key="i">{{ warningText(w) }}</li>
      </ul>
    </div>
    <div class="grid-2">
      <div class="panel">
        <div class="panel-hd">
          <h3>推荐匹配</h3>
          <span class="pill" :class="matchPillClass">{{ matchPillText }}</span>
        </div>
        <div class="panel-bd">
          <div class="rec-box">
            <div class="rec-title">
              系统推荐（置信度 {{ p.confidence.toFixed(2) }}）
              <span v-if="matchMeta.source" class="rec-src">· {{ matchSourceLabel }}</span>
            </div>
            <div class="rec-main">{{ p.recommended_arch }} × {{ p.recommended_domain }}</div>
            <div class="rec-sub" v-if="recommendedArchesText">
              能力路径并集：{{ recommendedArchesText }}
            </div>
            <div class="rec-sub" v-if="archDomainDeviant">
              当前出包：{{ form.archetype }} × {{ form.domain }}
            </div>
            <div class="rec-sub">
              推荐持久层：{{ persistenceLabel(p.recommended_persistence || 'jdbc') }}
              <span v-if="persistenceDeviant"> · 当前出包：{{ persistenceLabel(form.persistence) }}</span>
            </div>
            <div class="rec-sub">
              推荐鉴权：{{ securityLabel(p.recommended_spring_security) }}
              <span v-if="securityDeviant"> · 当前出包：{{ securityLabel(form.springSecurity) }}</span>
            </div>
            <div class="rec-sub" v-if="matchPath.recommended_scene_label || matchPath.scene_label">
              推荐身份：{{ matchPath.recommended_scene_label || '—' }}
              <span v-if="pathSceneDeviant"> · 当前出包：{{ matchPath.scene_label }}</span>
            </div>
            <div class="rec-sub" v-if="matchPath.entry_options?.length">
              推荐入口：{{ matchPath.recommended_entry_label || '—' }}
              <span v-if="pathEntryDeviant"> · 当前出包：{{ matchPath.entry_label }}</span>
              <span v-if="matchPath.entry_weak && !pathEntryDeviant" class="path-weak"> · 依据弱，请人工核</span>
            </div>
            <div class="rec-sub" v-if="matchMeta.rationale">理由：{{ matchMeta.rationale }}</div>
            <div class="rec-sub" v-if="narrativeDualText">
              拟选叙事对照：{{ narrativeDualText }}
            </div>
            <div class="rec-sub" v-if="matchAltsText">备选：{{ matchAltsText }}</div>
            <div class="rec-sub" v-if="keywordHits.length">命中：{{ keywordHits.join(' / ') }}</div>
            <div class="rec-sub" v-if="p.spec?.out_of_mvp?.length">本期不做：{{ p.spec.out_of_mvp.join('、') }}</div>
          </div>
          <div class="lock-row">
            <span class="small muted">{{ unlocked ? '骨架 / 领域 / 身份入口 / 持久层 / 鉴权可调整' : '骨架 / 领域 / 身份入口 / 持久层 / 鉴权已锁定' }}</span>
            <div class="row">
              <n-button
                size="small"
                :loading="matchBusy"
                :title="unlocked ? '锁定当前骨架·领域·持久层·鉴权；偏离推荐时可能无法锁定' : '解锁后可改骨架·领域·持久层·鉴权；改完须再确认'"
                @click="toggleUnlock"
              >{{ unlocked ? '重新锁定' : '解锁调整' }}</n-button>
              <n-button
                v-if="unlocked || deviant"
                text
                size="small"
                :loading="matchBusy"
                title="丢掉手改，回到扫描推荐并重新锁定"
                @click="resetMatch"
              >恢复推荐</n-button>
            </div>
          </div>
          <div class="grid-2">
            <div class="field" :class="{ locked: !unlocked }">
              <n-form-item label="骨架">
                <n-select v-model:value="form.archetype" :options="archOptions" :disabled="!unlocked || matchBusy" :loading="matchBusy" @update:value="onArchDomChange" />
              </n-form-item>
            </div>
            <div class="field" :class="{ locked: !unlocked }">
              <n-form-item label="领域">
                <n-cascader
                  v-model:value="form.domain"
                  :options="domCascaderOptions"
                  check-strategy="child"
                  :show-path="true"
                  filterable
                  :disabled="!unlocked || matchBusy"
                  @update:value="onArchDomChange"
                />
              </n-form-item>
            </div>
          </div>
          <div class="grid-2" style="margin-top:10px">
            <div class="field" :class="{ locked: !unlocked }">
              <n-form-item label="身份场景">
                <n-select
                  v-model:value="form.scene"
                  :options="sceneOptions"
                  :disabled="!unlocked || matchBusy"
                  :loading="matchBusy"
                  @update:value="onPathChange"
                />
              </n-form-item>
            </div>
            <div class="field" :class="{ locked: !unlocked }" v-if="entryOptions.length">
              <n-form-item label="主路径入口">
                <n-select
                  v-model:value="form.entry"
                  :options="entryOptions"
                  :disabled="!unlocked || matchBusy"
                  :loading="matchBusy"
                  @update:value="onPathChange"
                />
              </n-form-item>
            </div>
          </div>
          <div class="field" :class="{ locked: !unlocked }" style="margin-top:10px">
            <n-form-item label="持久层">
              <n-select
                v-model:value="form.persistence"
                :options="persistenceOptions"
                :disabled="!unlocked || matchBusy"
                :loading="matchBusy"
                @update:value="onArchDomChange"
              />
            </n-form-item>
          </div>
          <div class="field" :class="{ locked: !unlocked }" style="margin-top:10px">
            <n-form-item label="Spring Security">
              <n-select
                v-model:value="form.springSecurity"
                :options="securityOptions"
                :disabled="!unlocked || matchBusy"
                :loading="matchBusy"
                @update:value="onArchDomChange"
              />
            </n-form-item>
          </div>
          <div class="confidence">
            <span class="small muted">置信度</span>
            <div class="bar"><i :style="{ width: displayConf * 100 + '%', background: displayConf >= 0.75 ? 'var(--green)' : 'var(--amber)' }" /></div>
            <strong>{{ displayConf.toFixed(2) }}</strong>
            <span v-if="deviant" class="small muted">已偏离推荐 · 原置信度 {{ (p.confidence || 0).toFixed(2) }}</span>
          </div>
          <div class="override-banner" :class="{ show: unlocked || deviant || matchPath.needs_path_ack, danger: deviant || matchPath.needs_path_ack }">
            <template v-if="matchPath.needs_path_ack">
              开题未写清「谁怎么用」：请解锁选择主路径入口，或确认时勾选「主路径已核对」。
            </template>
            <template v-else-if="deviant">
              当前与系统推荐不一致，请确认后再生成。
            </template>
            <template v-else>
              骨架 / 领域 / 身份入口 / 持久层 / 鉴权可调整。如无把握，建议恢复推荐。
            </template>
          </div>
        </div>
      </div>
      <div class="panel">
        <div class="panel-hd">
          <h3>解析摘要 · 生成配置</h3>
          <div class="row" style="margin:0;gap:6px">
            <CopyIconButton :text="specText" tip="复制配置" />
            <n-button text size="small" @click="showSpec = true">查看</n-button>
          </div>
        </div>
        <div class="panel-bd parse-panel">
          <div class="parse-block">
            <div class="parse-label">开题解析</div>
            <div class="parse-title">{{ proposal.title || p.title }}</div>
            <p v-if="proposal.background" class="parse-bg">{{ proposal.background }}</p>
            <div v-if="keywordHits.length" class="parse-hits">
              <span v-for="h in keywordHits" :key="h" class="hit-chip">{{ h }}</span>
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
            <div class="parse-label">生成配置</div>
            <dl class="spec-dl">
              <div><dt>角色</dt><dd>{{ roleSpecText }}</dd></div>
              <div><dt>实体</dt><dd>{{ (p.spec?.entities || []).join('、') || '—' }}</dd></div>
              <div><dt>主流程</dt><dd>{{ (p.spec?.flows || []).join('；') || '—' }}</dd></div>
              <div><dt>基线</dt><dd>{{ (p.spec?.baseline || []).join('、') || '—' }}</dd></div>
              <div v-if="p.spec?.out_of_mvp?.length"><dt>本期不做</dt><dd>{{ p.spec.out_of_mvp.join('、') }}</dd></div>
              <div><dt>登录入口</dt><dd>{{ authEntryDisplay }}</dd></div>
              <div v-if="p.spec?.delivery_slug || p.db_name || p.spec?.maven_artifact"><dt>交付标识</dt><dd>
                <span v-if="p.spec?.delivery_slug" class="mono">{{ p.spec.delivery_slug }}</span>
                <template v-if="p.spec?.zip_name"> · {{ p.spec.zip_name }}</template>
                <template v-if="p.spec?.maven_artifact"> · Maven {{ p.spec.maven_artifact }}</template>
                <template v-if="p.spec?.java_package"> · {{ p.spec.java_package }}</template>
                <template v-if="p.db_name"> · 库 {{ p.db_name }}</template>
              </dd></div>
            </dl>
          </div>
        </div>
      </div>
    </div>
    <div class="gate" :class="{ ok: ack }">
      <n-checkbox v-model:checked="ack" :disabled="p.match_confirmed">
        {{ confirmHint }}
      </n-checkbox>
      <n-checkbox
        v-if="matchPath.needs_path_ack || matchPath.entry_options?.length"
        v-model:checked="ackMainPath"
        :disabled="p.match_confirmed"
        style="display:block;margin-top:10px"
      >
        主路径已核对：{{ matchPath.scene_label || '—' }}
        <template v-if="matchPath.entry_label"> · {{ matchPath.entry_label }}</template>
        <span v-if="matchPath.needs_path_ack" class="path-weak">（开题依据弱，必勾）</span>
      </n-checkbox>
    </div>
    <div class="row mt-16">
      <n-button
        type="primary"
        size="large"
        :disabled="!ack || p.match_confirmed || (matchPath.needs_path_ack && !ackMainPath)"
        :loading="matchBusy"
        @click="confirmMatch"
      >
        {{ deviant ? '确认按当前选择继续' : '确认并继续' }}
      </n-button>
    </div>
  </div>
</template>

<script setup>
import { bindPd } from './bindPd'
import CopyIconButton from '../../components/CopyIconButton.vue'
const {
  FILL_UNIT_KIND_ZH, FILL_UNIT_STATUS_ZH, PORTAL_HOME_FALLBACK, TYPE_PAREN_KEY, _runtimeSettled, _tailLines, ack, ackMainPath,
  alreadyBaked, apiCopyText, apiGroupCopyText, apiQuery, apiSmokeBusy, apiSmokeFactoryHint, apiSmokeResult, apiSurface,
  apis, applyFillSnapshot, archDomainDeviant, archOptions, artifactLoading, artifactView, artifactsFrozen, artifactsFrozenReason,
  authEntryDisplay, backendAddr, canDownload, canDownloadAndDeliver, canMarkDelivered, canMarkReady, canUndoDelivery, cancelCurrent,
  catalog, checkCols, checkRows, chromeOptions, collapsedApis, collapsedTables, commitColZh, commitRelZh,
  commitTableZh, confirmDelete, confirmHint, confirmMatch, confirmPreGenerate, currentJob, deleteBlocked,
  deleteBlockedReason, deleting, deliveryBusy, deliveryMark, deviant, displayConf, domCascaderOptions, downloadAndDeliver,
  downloadBlockedReason, downloadZip, downloadZipLabel, entryOptions, erDownloadBase, erEntity, erEntityOptions, erLabelSaving,
  erLayoutKey, erLoading, erMode, erSvgSource, failedBannerTitle, fetchErSvg, fetchModSvg, fillEventSource,
  fillLiveCols, fillLiveRows, fillLiveSnap, fillLiveSummary, fillLiveVisible, fillPlanCols, fillPlanHint,
  fillPlanLoading, fillPlanRows, filteredApiGroups, filteredLog, form, formatSize, frontendAddr, gateCols,
  gateRows, genState, genSuccessBannerHint, genSuccessBannerTitle, goArtifacts, isApiCollapsed, isTableCollapsed, jobActing,
  jobInFlight, keepDb, keywordHits, labelLooksLatin, layoutOptions, llmOptions, load, loadApis,
  loadArtifactView, loadError, loadErrorCode, loadLog, loadSchema, logFilter, logLoading, logReqSeq,
  logSide, logSides, logText, markDelivery, matchAltsText, matchBusy, matchMeta, matchPath,
  matchPillClass, matchPillText, matchSourceLabel, matchWarnings, modDownloadBase, modLayoutKey, modLoading, modSvgSource,
  modulesLayout, modulesMeta, modulesOk, narrativeDualText, normalizeStepStatus, onArchDomChange, onArtifactView, onDelete,
  onErEntity, onErMode, onModulesLayout, onPathChange, onTcFields, openEr, openFillPlan, openModules,
  openPreview, openTestcases, p, parseMysqlType, passwordHashOptions, pathEntryDeviant, pathSceneDeviant, persistenceDeviant,
  persistenceLabel, persistenceOptions, planSteps, pollFailStreak, pollInFlight, pollSyncHint, pollTimer, portalHomeOptions,
  preGenBusy, preGenReady, preGenStackWarnings, preGenTechDual, proposal, proposalDiff, putErLabelPatch, recommendedArchesText,
  refreshJob, refreshRuntime, reload, reloadErSvg, reloadModSvg, reloadTestcases, resetMatch, retryCurrent,
  roleSpecText, route, router, rt, rtAction, rtAllBusy, rtAnyBusy, rtAnyLive,
  rtBeLive, rtBothLive, rtBusyBe, rtBusyFe, rtCanRestartAll, rtCanStartAll, rtCanStopAll, rtFeLive,
  rtGenerating, rtPendingAll, rtStartBlockedReason, runApiSmoke, runGenerateJob, runtimeCanStop, runtimeLogView, runtimeStatusLabel,
  runtimeStatusPill, runtimeTransient, saveSoft, sceneOptions, schema, schemaErGapCount, securityDeviant, securityLabel,
  securityOn, securityOptions, showDelete, showEr, showFillPlan, showJobSteps, showModules, showPreGenerate,
  showSoftBakePanel, showSpec, showTestcases, smokeDetailFromAxios, smokeDetailText, smokePillClass, smokeRowClass, smokeStatusLabel,
  softApplying, softBakeHint, softSaving, softThemeWireStyle, softVisualWireStyle, specText, startFillEvents, startGenerate,
  startPoll, statusLabel, statusPill, stepStatusLabel, stepStatusMark, stopFillEvents, stopPoll, tab,
  tableCopyText, tcColumns, tcCount, tcDownloadBase, tcFields, tcLoading, tcMarkdown, tcRows,
  themeOptions, toggleApi, toggleTable, toggleUnlock, typeParenMode, typefaceOptions, undoDelivery, undoDeliveryLabel,
  unlocked, viewActive, viewEpoch, warningText, zipFileName, zipLockHint,
} = bindPd()
</script>
