<template>
  <div>
    <div v-if="genState === 'running'" class="panel mb-16">
      <div class="panel-bd">
        <div class="row-between" style="margin-bottom:10px">
          <div style="font-weight:600">{{ jobInFlight && p.status !== 'generating' ? '正在启动生成…' : '正在生成…' }}</div>
          <div class="small muted">任务 #{{ currentJob?.id }} · {{ currentJob?.progress || 0 }}%</div>
        </div>
        <div class="progress" style="height:8px"><i :style="{ width: (currentJob?.progress || 0) + '%' }" /></div>
        <p v-if="pollSyncHint" class="small muted mt-12">{{ pollSyncHint }}</p>
        <p v-if="fillLiveSummary" class="small muted mt-8">{{ fillLiveSummary }}</p>
        <div v-if="fillLiveVisible" class="mt-12">
          <n-data-table
            size="small"
            :columns="fillLiveCols"
            :data="fillLiveRows"
            :bordered="false"
            :max-height="220"
            :pagination="false"
          />
        </div>
        <div class="row mt-12">
          <n-button size="small" type="error" secondary :loading="jobActing === 'cancel'" @click="cancelCurrent">取消任务</n-button>
          <n-button size="small" @click="tab = 'logs'">打开日志</n-button>
        </div>
      </div>
    </div>

    <template v-if="genState !== 'running'">
      <div v-if="(genState === 'success' || genState === 'live') && canDownload" class="banner success mb-16">
        <h4>{{ genSuccessBannerTitle }}</h4>
        <p class="small muted">{{ genSuccessBannerHint }}</p>
        <div class="row mt-12">
          <n-button size="small" @click="goArtifacts('gates')">查看质量检查</n-button>
          <n-button size="small" secondary @click="tab = 'runtime'">前往运行</n-button>
        </div>
      </div>
      <div v-else-if="genState === 'success' || genState === 'live'" class="banner fail mb-16">
        <h4>已生成，但质量检查未通过，暂不可下载</h4>
        <p class="small muted">工程与当前验收规则不一致（常见于基线升级后）。可调整下方选项后重新生成，或到「产物」查看未通过项。</p>
        <div class="row mt-12">
          <n-button size="small" @click="goArtifacts('gates')">查看质量检查</n-button>
          <n-button size="small" @click="tab = 'runtime'">前往运行</n-button>
        </div>
      </div>
      <div v-else-if="genState === 'failed'" class="banner fail mb-16">
        <h4>{{ failedBannerTitle }}</h4>
        <p class="small muted">{{ currentJob?.error || '生成未完成 · 暂不可下载交付包。可从失败步骤重试或查看日志。' }}</p>
        <div class="row mt-12">
          <n-button type="primary" size="small" :loading="jobActing === 'retry'" @click="retryCurrent">从失败步骤重试</n-button>
          <n-button size="small" @click="goArtifacts('gates')">查看质量检查</n-button>
          <n-button size="small" @click="tab = 'logs'">查看日志</n-button>
        </div>
      </div>
    </template>

    <div v-if="showJobSteps" class="panel mb-16">
      <div class="panel-hd">
        <h3>流水线进度</h3>
        <span class="small muted">{{ genState === 'running' ? ((currentJob?.progress || 0) + '%') : ('任务 #' + (currentJob?.id || '—')) }}</span>
      </div>
      <div class="panel-bd">
        <ol class="step-rail">
          <li
            v-for="s in (currentJob?.steps || [])"
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

    <div v-if="genState !== 'running' && showSoftBakePanel" class="panel mb-16">
        <div class="panel-hd">
          <h3 class="soft-label-with-tip">
            视觉与生成选项
            <n-tooltip trigger="hover" placement="bottom-start" :delay="120">
              <template #trigger>
                <button type="button" class="soft-tip-btn" aria-label="当前视觉示意">
                  <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
                    <path
                      fill="currentColor"
                      d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm0 15a1.1 1.1 0 1 1 0-2.2A1.1 1.1 0 0 1 12 17zm1.2-4.4h-2.4V7h2.4v5.6z"
                    />
                  </svg>
                </button>
              </template>
              <div class="soft-visual-tip">
                <div class="soft-visual-tip-title">当前选项示意</div>
                <div
                  class="layout-shell-wire soft-visual-wire"
                  :data-layout="form.layout || 'topbar'"
                  :data-chrome="form.chrome || 'soft'"
                  :data-home="form.portalHomeStyle || 'cards'"
                  :data-typeface="form.typeface || 'clean'"
                  :style="softVisualWireStyle"
                >
                  <div class="lsw-chrome">
                    <span class="lsw-brand" />
                    <span class="lsw-nav"><i /><i /><i /></span>
                  </div>
                  <div class="lsw-body">
                    <template v-if="(form.portalHomeStyle || 'cards') === 'editorial'">
                      <div class="lsw-editorial">
                        <div class="lsw-main">
                          <span class="lsw-card" />
                          <span class="lsw-card short" />
                        </div>
                        <div class="lsw-side">
                          <span class="lsw-card" />
                          <span class="lsw-card" />
                        </div>
                      </div>
                    </template>
                    <template v-else-if="(form.portalHomeStyle || 'cards') === 'mall'">
                      <div class="lsw-mall">
                        <div class="lsw-mall-rail">
                          <span class="lsw-card" />
                          <span class="lsw-card short" />
                          <span class="lsw-card" />
                        </div>
                        <div class="lsw-mall-main">
                          <span class="lsw-card lsw-mall-banner" />
                          <div class="lsw-mall-grid">
                            <span class="lsw-card" />
                            <span class="lsw-card" />
                            <span class="lsw-card" />
                            <span class="lsw-card" />
                          </div>
                        </div>
                      </div>
                    </template>
                    <template v-else>
                      <div class="lsw-cards">
                        <span class="lsw-card" />
                        <span class="lsw-card" />
                        <span class="lsw-card" />
                      </div>
                    </template>
                  </div>
                  <div class="lsw-type">标题 Aa · 正文示意</div>
                </div>
              </div>
            </n-tooltip>
          </h3>
          <span class="small muted">{{ softBakeHint }}</span>
        </div>
        <div class="panel-bd">
          <div class="grid-2">
            <n-form-item label="行业配色">
              <n-select v-model:value="form.theme" :options="themeOptions" :loading="softSaving" :disabled="softSaving" @update:value="saveSoft" />
            </n-form-item>
            <n-form-item label="界面质感">
              <n-select v-model:value="form.chrome" :options="chromeOptions" :loading="softSaving" :disabled="softSaving" @update:value="saveSoft" />
            </n-form-item>
            <n-form-item label="门户布局">
              <n-select v-model:value="form.layout" :options="layoutOptions" :loading="softSaving" :disabled="softSaving" @update:value="saveSoft" />
            </n-form-item>
            <n-form-item label="字体配对">
              <n-select v-model:value="form.typeface" :options="typefaceOptions" :loading="softSaving" :disabled="softSaving" @update:value="saveSoft" />
            </n-form-item>
            <n-form-item label="门户首页">
              <n-select
                v-model:value="form.portalHomeStyle"
                :options="portalHomeOptions"
                :loading="softSaving"
                :disabled="softSaving"
                @update:value="saveSoft"
              />
            </n-form-item>
            <n-form-item label="智能业务填充">
              <n-select v-model:value="form.llm" :options="llmOptions" :loading="softSaving" :disabled="softSaving" @update:value="saveSoft" />
            </n-form-item>
            <n-form-item label="密码">
              <n-select v-model:value="form.passwordHash" :options="passwordHashOptions" :loading="softSaving" :disabled="softSaving" @update:value="saveSoft" />
            </n-form-item>
          </div>
          <div v-if="genState !== 'idle'" class="row mt-16">
            <n-button
              type="primary"
              :loading="softApplying"
              title="按当前选项重写工程与交付包；履约标记会清掉"
              @click="startGenerate"
            >按当前选项重新生成</n-button>
          </div>
        </div>
      </div>

      <div v-if="genState === 'idle'">
        <div class="panel mb-16">
          <div class="panel-bd">
            <div class="row-between">
              <div>
                <div style="font-weight:600;margin-bottom:4px">{{ p.match_confirmed ? '匹配已确认 · 可以生成' : '请先完成匹配确认' }}</div>
                <div class="small muted">以基线工程生成为主，AI 仅补业务配置；质量检查未通过前不可下载交付包</div>
              </div>
              <span
                class="btn-tip-wrap"
                :title="p.match_confirmed ? '按匹配结果落地工程；AI 只填业务配置' : '请先完成匹配确认后再生成'"
              >
                <n-button type="primary" size="large" :disabled="!p.match_confirmed" :loading="softApplying" @click="startGenerate">一键生成</n-button>
              </span>
            </div>
          </div>
        </div>
        <div class="panel">
          <div class="panel-hd">
            <h3>生成流水线</h3>
            <span class="small muted">{{ planSteps.length }} 步 · 顺序执行</span>
          </div>
          <div class="panel-bd">
            <ol class="step-rail">
              <li v-for="(s, i) in planSteps" :key="i" class="pending">
                <div class="step-rail-track" aria-hidden="true">
                  <span class="step-ico">{{ i + 1 }}</span>
                </div>
                <div class="step-body">
                  <div class="step-title">{{ s.t }}</div>
                  <div class="meta">{{ s.m }}</div>
                </div>
              </li>
            </ol>
          </div>
        </div>
      </div>

  <!-- 答辩 PPT：一键生成下半截（唯一开跑入口；程序流水线不含 PPT） -->
  <DefensePptLaunchPanel />
  </div>
</template>

<script setup>
import DefensePptLaunchPanel from '../../components/defensePpt/DefensePptLaunchPanel.vue'
import { bindPd } from './bindPd'
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
