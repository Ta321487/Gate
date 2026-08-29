<template>
  <div class="pd-modals">
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
      <p style="margin:0 0 12px">将永久删除本机工程目录与交付包，此操作不可撤销。</p>
      <p v-if="p.db_name" class="small muted" style="margin:0 0 12px">
        学生库 <span class="mono">{{ p.db_name }}</span>
        {{ keepDb ? '将被保留' : '将一并删除' }}
      </p>
      <n-checkbox v-if="p.db_name" v-model:checked="keepDb">保留学生数据库</n-checkbox>
    </n-modal>
    <n-modal
      v-model:show="showPreGenerate"
      preset="card"
      title="生成前 · 开题措辞核对"
      class="pre-gen-modal"
      style="width:min(640px,96vw)"
    >
      <p class="small muted" style="margin-top:0;margin-bottom:8px">
        核对开题主流程是否由已选领域覆盖；下方为措辞对照，不阻断生成。
      </p>
      <div
        v-if="proposalDiff"
        class="pre-gen-status"
        :class="{
          'pre-gen-ready': preGenReady,
          'pre-gen-review': proposalDiff && !preGenReady && proposalDiff.needs_review,
          'pre-gen-check': proposalDiff && !preGenReady && !proposalDiff.needs_review,
        }"
      >
        <div class="pre-gen-coverage">{{ proposalDiff.coverage_label || '—' }}</div>
        <div class="pre-gen-summary">{{ proposalDiff.summary }}</div>
        <p v-if="proposalDiff.operator_hint" class="small pre-gen-hint">{{ proposalDiff.operator_hint }}</p>
      </div>
      <div class="pre-gen-scroll">
        <n-alert v-if="preGenStackWarnings.length" type="warning" :bordered="false" style="margin-bottom:12px;margin-top:12px">
          <div class="parse-sec-hd" style="margin:0 0 4px">技术栈 · 开题与拟选</div>
          <div v-for="(w, i) in preGenStackWarnings" :key="'sw' + i" class="small">{{ w }}</div>
          <div v-if="preGenTechDual" class="small muted" style="margin-top:6px">{{ preGenTechDual }}</div>
        </n-alert>
        <div v-if="proposalDiff?.matched?.length" class="parse-sec-hd mt-12">已对照 · {{ proposalDiff.matched.length }} 项</div>
        <ul v-if="proposalDiff?.matched?.length" class="zone-list pre-gen-line-list">
          <li v-for="(line, i) in proposalDiff.matched" :key="'m'+i" :title="line">{{ line }}</li>
        </ul>
        <div v-if="proposalDiff?.review_proposal?.length" class="parse-sec-hd mt-12">措辞弱匹配 · 已纳入覆盖</div>
        <ul v-if="proposalDiff?.review_proposal?.length" class="zone-list pre-gen-line-list">
          <li v-for="(line, i) in proposalDiff.review_proposal" :key="'r'+i" :title="line">{{ line }}</li>
        </ul>
        <div v-if="proposalDiff?.unmatched_proposal?.length" class="parse-sec-hd mt-12">措辞待核 · 请确认领域是否正确</div>
        <ul v-if="proposalDiff?.unmatched_proposal?.length" class="zone-list pre-gen-warn-list pre-gen-line-list">
          <li v-for="(line, i) in proposalDiff.unmatched_proposal" :key="'u'+i" :title="line">{{ line }}</li>
        </ul>
        <div v-if="proposalDiff?.match_links?.length" class="parse-sec-hd mt-12 row-between" style="align-items:center">
          <span>对照解释 · {{ proposalDiff.match_links.length }} 条</span>
          <n-button text size="tiny" @click="preGenLinksOpen = !preGenLinksOpen">
            {{ preGenLinksOpen ? '收起' : '展开' }}
          </n-button>
        </div>
        <ul v-if="proposalDiff?.match_links?.length && preGenLinksOpen" class="zone-list match-link-list">
          <li v-for="(row, i) in proposalDiff.match_links" :key="'ml' + i">
            <div class="match-link-line muted" :title="row.line">{{ shortenLine(row.line) }}</div>
            <div class="match-link-hits">
              <span
                v-for="(hit, j) in row.hits || []"
                :key="j"
                class="hit-chip"
                :title="hit.reason || hit.feature"
              >{{ hit.feature }}</span>
            </div>
          </li>
        </ul>
        <div v-if="proposalDiff?.extra_checklist?.length" class="parse-sec-hd mt-12">工厂实现模块</div>
        <p v-if="proposalDiff?.extra_checklist?.length" class="small muted" style="margin:0 0 6px">
          开题合并表述会拆成下列可交付模块，通常不是多余功能。
        </p>
        <ul v-if="proposalDiff?.extra_checklist?.length" class="zone-list">
          <li v-for="(line, i) in proposalDiff.extra_checklist" :key="'e' + i">{{ line }}</li>
        </ul>
      </div>
      <div class="row pre-gen-actions" style="justify-content:flex-end;margin-top:12px;gap:8px">
        <n-button @click="showPreGenerate = false">取消</n-button>
        <n-button type="primary" :loading="preGenBusy || softApplying" @click="confirmPreGenerate">
          {{ preGenReady ? '确认并启动生成' : '仍要启动生成' }}
        </n-button>
      </div>
    </n-modal>
    <n-modal v-model:show="showFillPlan" preset="card" title="填岛拆解计划" style="width:min(960px,96vw)">
      <p class="small muted" style="margin-top:0">
        与一键生成 step「业务配置填充」同源；生成前为预估，生成后可对照 <span class="mono">islands/unit_flow/plan.json</span>。
      </p>
      <n-data-table
        size="small"
        :columns="fillPlanCols"
        :data="fillPlanRows"
        :bordered="false"
        :max-height="420"
        :loading="fillPlanLoading"
      />
      <div class="row" style="justify-content:flex-end;margin-top:16px;gap:8px">
        <n-button @click="showFillPlan = false">关闭</n-button>
        <n-button type="primary" :loading="fillPlanAckBusy" @click="confirmFillPlan">
          确认计划
        </n-button>
      </div>
    </n-modal>
    <n-modal v-model:show="showSpec" preset="card" title="生成配置" style="width:640px">
      <div class="row" style="justify-content:flex-end;margin:0 0 8px">
        <CopyIconButton :text="specText" tip="复制配置" />
      </div>
      <pre class="spec-preview" style="max-height:60vh">{{ specText }}</pre>
    </n-modal>
    <n-modal v-model:show="showEr" preset="card" title="E-R 图（线框）" style="width:min(1280px,96vw)">
      <ErDiagramViewer
        v-if="showEr"
        :key="erLayoutKey"
        :svg-source="erSvgSource"
        :download-name="erDownloadBase"
        :mode="erMode"
        :entity="erEntity"
        :entity-options="erEntityOptions"
        :loading="erLoading"
        @update:mode="onErMode"
        @update:entity="onErEntity"
        @reload="reloadErSvg"
      />
    </n-modal>
    <n-modal v-model:show="showModules" preset="card" title="功能模块图" style="width:min(1280px,96vw)">
      <ModuleDiagramViewer
        v-if="showModules"
        :key="modLayoutKey"
        :svg-source="modSvgSource"
        :download-name="modDownloadBase"
        :layout="modulesLayout"
        :loading="modLoading"
        @update:layout="onModulesLayout"
        @reload="reloadModSvg"
      />
    </n-modal>
    <n-modal v-model:show="showTestcases" preset="card" title="软件测试用例" style="width:min(1280px,96vw)">
      <TestcaseViewer
        v-if="showTestcases"
        :columns="tcColumns"
        :rows="tcRows"
        :markdown="tcMarkdown"
        :fields="tcFields"
        :count="tcCount"
        :download-name="tcDownloadBase"
        :loading="tcLoading"
        @update:fields="onTcFields"
        @reload="reloadTestcases"
      />
    </n-modal>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { bindPd } from './bindPd'
import CopyIconButton from '../../components/CopyIconButton.vue'
import ErDiagramViewer from '../../components/ErDiagramViewer.vue'
import ModuleDiagramViewer from '../../components/ModuleDiagramViewer.vue'
import TestcaseViewer from '../../components/TestcaseViewer.vue'

const preGenLinksOpen = ref(false)

function shortenLine(s, max = 42) {
  const t = String(s || '').trim()
  if (t.length <= max) return t
  return `${t.slice(0, max)}…`
}

const {
  FILL_UNIT_KIND_ZH, FILL_UNIT_STATUS_ZH, PORTAL_HOME_FALLBACK, TYPE_PAREN_KEY, _runtimeSettled, _tailLines, ack, ackMainPath,
  alreadyBaked, apiCopyText, apiGroupCopyText, apiQuery, apiSmokeBusy, apiSmokeFactoryHint, apiSmokeResult, apiSurface,
  apis, applyFillSnapshot, archDomainDeviant, archOptions, artifactLoading, artifactView, artifactsFrozen, artifactsFrozenReason,
  authEntryDisplay, backendAddr, canDownload, canDownloadAndDeliver, canMarkDelivered, canMarkReady, canUndoDelivery, cancelCurrent,
  catalog, checkCols, checkRows, chromeOptions, collapsedApis, collapsedTables, commitColZh, commitRelZh,
  commitTableZh, confirmDelete, confirmFillPlan, confirmHint, confirmMatch, confirmPreGenerate, currentJob, deleteBlocked,
  deleteBlockedReason, deleting, deliveryBusy, deliveryMark, deviant, displayConf, domCascaderOptions, downloadAndDeliver,
  downloadBlockedReason, downloadZip, downloadZipLabel, entryOptions, erDownloadBase, erEntity, erEntityOptions, erLabelSaving,
  erLayoutKey, erLoading, erMode, erSvgSource, failedBannerTitle, fetchErSvg, fetchModSvg, fillEventSource,
  fillLiveCols, fillLiveRows, fillLiveSnap, fillLiveSummary, fillLiveVisible, fillPlanAckBusy, fillPlanCols, fillPlanHint,
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

watch(showPreGenerate, (open) => {
  if (!open) return
  const d = proposalDiff.value
  // 有待核/弱匹配时默认展开解释；全覆盖时收起，避免弹窗被长文撑爆
  preGenLinksOpen.value = !!(d?.unmatched_proposal?.length || d?.review_proposal?.length)
})
</script>
