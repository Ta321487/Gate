<template>
  <div>
    <div v-if="rtSettling || rtAnyBusy" class="panel panel-quiet mb-16">
      <div class="panel-bd">
        <LongOpWait
          :title="rtWaitCopy.title"
          :phases="rtWaitCopy.phases"
          :phase-seconds="[8, 20, 30]"
          :hint="rtWaitCopy.hint"
        />
      </div>
    </div>
    <div class="row-between mb-16">
      <span class="small muted">库 <span class="mono">{{ p.db_name || '—' }}</span><CopyIconButton v-if="p.db_name" :text="p.db_name" tip="复制库名" /></span>
      <div class="row" style="margin:0">
        <n-button
          size="small"
          :type="rtPreviewPrimary ? 'default' : (rtCanStartAll && !rtAnyLive ? 'primary' : 'default')"
          :secondary="rtPreviewPrimary || !(rtCanStartAll && !rtAnyLive)"
          :disabled="!rtCanStartAll"
          :title="rtStartBlockedReason || undefined"
          :loading="rtPendingAll==='start'"
          @click="rtAction('all','start')"
        >全部启动</n-button>
        <n-button
          size="small"
          secondary
          :disabled="!rtCanStopAll"
          :loading="rtPendingAll==='stop'"
          @click="rtAction('all','stop')"
        >全部停止</n-button>
        <n-button
          size="small"
          secondary
          :disabled="!rtCanRestartAll"
          :title="rtGenerating ? '生成中 · 请等待完成后再重启' : undefined"
          :loading="rtPendingAll==='restart'"
          @click="rtAction('all','restart')"
        >全部重启</n-button>
        <n-button
          size="small"
          :type="rtPreviewPrimary ? 'primary' : 'default'"
          :secondary="!rtPreviewPrimary"
          :disabled="!rtPreviewPrimary || rtBusyFe"
          @click="openPreview"
        >打开预览</n-button>
        <CopyIconButton
          v-if="rt.preview_url && rt.frontend_status === 'healthy'"
          :text="rt.preview_url"
          tip="复制预览地址"
        />
      </div>
    </div>
    <div class="grid-2 stage-grid">
      <div class="panel panel-quiet">
        <div class="panel-hd">
          <h3>后端 · :{{ p.backend_port || '—' }}<CopyIconButton v-if="backendAddr" :text="backendAddr" tip="复制后端地址" /></h3>
          <span class="pill" :class="runtimeStatusPill(rt.backend_status)">{{ runtimeStatusLabel(rt.backend_status) }}</span>
        </div>
        <div class="panel-bd">
          <div class="row" style="justify-content:flex-end">
            <n-button
              size="small"
              secondary
              :disabled="rtBusyBe || rtAllBusy || runtimeTransient(rt.backend_status) || (rtGenerating && !runtimeCanStop(rt.backend_status))"
              :loading="rtBusyBe || runtimeTransient(rt.backend_status)"
              @click="rtAction('backend', runtimeCanStop(rt.backend_status) ? 'stop' : 'start')"
            >{{ runtimeCanStop(rt.backend_status) ? '停止' : '启动' }}</n-button>
          </div>
          <n-collapse :default-expanded-names="[]" class="mt-8">
            <n-collapse-item title="后端日志（排障）" name="be-log">
              <pre class="log-box">{{ runtimeLogView(rt.backend_status, rt.backend_log_tail) }}</pre>
            </n-collapse-item>
          </n-collapse>
        </div>
      </div>
      <div class="panel panel-quiet">
        <div class="panel-hd">
          <h3>前端 · :{{ p.frontend_port || '—' }}<CopyIconButton v-if="frontendAddr" :text="frontendAddr" tip="复制前端地址" /></h3>
          <span class="pill" :class="runtimeStatusPill(rt.frontend_status)">{{ runtimeStatusLabel(rt.frontend_status) }}</span>
        </div>
        <div class="panel-bd">
          <div class="row" style="justify-content:flex-end">
            <n-button
              size="small"
              secondary
              :disabled="rtBusyFe || rtAllBusy || runtimeTransient(rt.frontend_status) || (rtGenerating && !runtimeCanStop(rt.frontend_status))"
              :loading="rtBusyFe || runtimeTransient(rt.frontend_status)"
              @click="rtAction('frontend', runtimeCanStop(rt.frontend_status) ? 'stop' : 'start')"
            >{{ runtimeCanStop(rt.frontend_status) ? '停止' : '启动' }}</n-button>
          </div>
          <n-collapse :default-expanded-names="[]" class="mt-8">
            <n-collapse-item title="前端日志（排障）" name="fe-log">
              <pre class="log-box">{{ runtimeLogView(rt.frontend_status, rt.frontend_log_tail) }}</pre>
            </n-collapse-item>
          </n-collapse>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, unref } from 'vue'
import { bindPd } from './bindPd'
import CopyIconButton from '../../components/CopyIconButton.vue'
import LongOpWait from '../../components/LongOpWait.vue'

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
  rtGenerating, rtSettling, rtWaitCopy, rtPendingAll, rtStartBlockedReason, runApiSmoke, runGenerateJob, runtimeCanStop, runtimeLogView, runtimeStatusLabel,
  runtimeStatusPill, runtimeTransient, saveSoft, sceneOptions, schema, schemaErGapCount, securityDeviant, securityLabel,
  securityOn, securityOptions, showDelete, showEr, showFillPlan, showJobSteps, showModules, showPreGenerate,
  showSoftBakePanel, showSpec, showTestcases, smokeDetailFromAxios, smokeDetailText, smokePillClass, smokeRowClass, smokeStatusLabel,
  softApplying, softBakeHint, softSaving, softThemeWireStyle, softVisualWireStyle, specText, startFillEvents, startGenerate,
  startPoll, statusLabel, statusPill, stepStatusLabel, stepStatusMark, stopFillEvents, stopPoll, tab,
  tableCopyText, tcColumns, tcCount, tcDownloadBase, tcFields, tcLoading, tcMarkdown, tcRows,
  themeOptions, toggleApi, toggleTable, toggleUnlock, typeParenMode, typefaceOptions, undoDelivery, undoDeliveryLabel,
  unlocked, viewActive, viewEpoch, warningText, zipFileName, zipLockHint,
} = bindPd()

/** 预览已健康时主 CTA=打开预览；否则主 CTA=全部启动 */
const rtPreviewPrimary = computed(() => unref(rt)?.frontend_status === 'healthy')
</script>
