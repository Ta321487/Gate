<template>
  <div v-if="p" class="surface-detail">
    <button class="back" @click="$router.push('/projects')">← 返回项目列表</button>
    <div class="proj-head">
      <div class="proj-head-main">
        <div class="proj-title">{{ p.title }}</div>
        <div class="proj-meta">
          <span class="pill" :class="statusPill">{{ statusLabel }}</span>
          <span>ID <span class="mono">{{ p.id }}</span><CopyIconButton :text="p.id" tip="复制项目 ID" /></span>
          <span v-if="p.db_name" class="muted">库 {{ p.db_name }}</span>
          <n-button text size="tiny" class="meta-tech-toggle" @click="showTechIds = !showTechIds">
            {{ showTechIds ? '收起标识' : '技术标识' }}
          </n-button>
        </div>
        <div v-if="showTechIds" class="proj-tech-extra">
          <span class="mono muted">{{ p.archetype }} · {{ p.domain }}</span>
          <span v-if="p.workspace_path" class="meta-ws">
            <span class="muted">工程</span>
            <span class="mono muted file-path" :title="p.workspace_path">{{ p.workspace_path }}</span>
            <CopyIconButton :text="p.workspace_path" tip="复制工程目录" />
          </span>
        </div>
      </div>
      <div class="proj-actions">
        <!-- 主下载 CTA 在交付就绪指示；页头仅保留履约副操作 + 删除 -->
        <n-button
          v-if="canMarkDelivered && !canDownloadAndDeliver"
          size="small"
          secondary
          :loading="deliveryBusy"
          title="标记为已发出（已交学生）；不重新打包"
          @click="markDelivery('delivered')"
        >标记已发出</n-button>
        <n-button
          v-if="canMarkReady"
          size="small"
          secondary
          :loading="deliveryBusy"
          title="人工审过、暂存待发；尚未视为已交学生"
          @click="markDelivery('ready')"
        >{{ canMarkDelivered ? '暂存待发' : '标记已审待发' }}</n-button>
        <n-button
          v-if="canUndoDelivery"
          size="small"
          secondary
          :loading="deliveryBusy"
          title="只改履约标记，不删工程或 ZIP"
          @click="undoDelivery"
        >{{ undoDeliveryLabel }}</n-button>
        <n-button type="error" secondary size="small" :disabled="deleteBlocked" :title="deleteBlockedReason" @click="onDelete">删除</n-button>
      </div>
    </div>

    <DeliveryReadinessBar
      :project="p"
      :active-tab="tab"
      :scrub-busy="copyScrubBusy"
      :delivery-busy="deliveryBusy"
      :job-acting="jobActing"
      @match="onReadyMatch"
      @generate="onReadyGenerate"
      @retry="retryCurrent"
      @scrub="scrubStudentCopy"
      @gates="goArtifacts('delivery')"
      @review="goArtifacts('delivery')"
      @download="downloadZip"
      @download-deliver="downloadAndDeliver"
    />

    <!-- 产品形态：阶段轨 = 唯一主导航（不再并列一级 Tabs） -->
    <DeliveryStageRail
      :project="p"
      :active-tab="tab"
      @select="trySetTab"
    />

    <div class="detail-stage-body">
      <MaterialsTab v-show="tab === 'materials'" @next="trySetTab('match')" />
      <MatchTab v-show="tab === 'match'" />
      <GenerateTab v-show="tab === 'generate'" />
      <ArtifactsTab v-show="tab === 'thesis'" pane="thesis" />
      <PptTab v-show="tab === 'ppt'" />
      <ArtifactsTab v-show="tab === 'artifacts'" pane="delivery" />
      <RuntimeTab v-show="tab === 'runtime'" />
      <div v-show="tab === 'tools'" class="tools-pane">
        <LogsTab />
      </div>
    </div>

    <DetailModals />
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
import { provide, reactive, ref } from 'vue'
import ErrorPage from './ErrorPage.vue'
import PageSkeleton from '../components/PageSkeleton.vue'
import CopyIconButton from '../components/CopyIconButton.vue'
import DeliveryReadinessBar from '../components/DeliveryReadinessBar.vue'
import DeliveryStageRail from '../components/DeliveryStageRail.vue'
import { message } from '../api'
import { canEnterDetailTab } from '../deliveryStages'
import { PD_KEY } from './projectDetail/context'
import { useProjectDetail } from './projectDetail/useProjectDetail'
import MaterialsTab from './projectDetail/MaterialsTab.vue'
import MatchTab from './projectDetail/MatchTab.vue'
import GenerateTab from './projectDetail/GenerateTab.vue'
import RuntimeTab from './projectDetail/RuntimeTab.vue'
import LogsTab from './projectDetail/LogsTab.vue'
import ArtifactsTab from './projectDetail/ArtifactsTab.vue'
import PptTab from './projectDetail/PptTab.vue'
import DetailModals from './projectDetail/DetailModals.vue'

const detail = useProjectDetail()
provide(PD_KEY, reactive(detail))

const showTechIds = ref(false)

const {
  p,
  loadError,
  loadErrorCode,
  tab,
  statusPill,
  statusLabel,
  canDownloadAndDeliver,
  canMarkDelivered,
  canMarkReady,
  canUndoDelivery,
  deliveryBusy,
  undoDeliveryLabel,
  deleteBlocked,
  deleteBlockedReason,
  downloadAndDeliver,
  markDelivery,
  undoDelivery,
  downloadZip,
  onDelete,
  reload,
  copyScrubBusy,
  scrubStudentCopy,
  goArtifacts,
  jobActing,
  retryCurrent,
} = detail

function trySetTab(name) {
  const gate = canEnterDetailTab(p.value, name)
  if (!gate.ok) {
    message.warning(gate.reason || '当前阶段尚未完成，暂不能进入')
    return
  }
  if (name === 'thesis') {
    goArtifacts('thesis')
    return
  }
  if (name === 'ppt') {
    goArtifacts('ppt')
    return
  }
  tab.value = name
}

function onReadyMatch() {
  trySetTab('match')
}

function onReadyGenerate() {
  trySetTab('generate')
}
</script>

<style scoped>
.proj-head-main {
  flex: 1;
  min-width: 0;
}
.proj-tech-extra {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 6px;
  font-size: 12px;
}
.meta-tech-toggle {
  opacity: 0.75;
}
.meta-ws {
  display: inline-flex;
  align-items: flex-start;
  gap: 4px;
  max-width: 100%;
}
.meta-ws .file-path {
  min-width: 0;
  overflow-wrap: anywhere;
  word-break: break-all;
}
</style>
