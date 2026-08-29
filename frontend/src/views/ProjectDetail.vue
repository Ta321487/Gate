<template>
  <div v-if="p">
    <button class="back" @click="$router.push('/')">← 返回项目列表</button>
    <div class="proj-head">
      <div>
        <div class="proj-title">{{ p.title }}</div>
        <div class="proj-meta">
          <span class="pill" :class="statusPill">{{ statusLabel }}</span>
          <span>ID <span class="mono">{{ p.id }}</span><CopyIconButton :text="p.id" tip="复制项目 ID" /></span>
          <span>{{ p.archetype }} · {{ p.domain }}</span>
          <span class="mono">{{ p.db_name }}</span><CopyIconButton v-if="p.db_name" :text="p.db_name" tip="复制库名" />
        </div>
      </div>
      <div class="proj-actions">
        <n-button
          v-if="canDownloadAndDeliver"
          size="small"
          type="primary"
          :loading="deliveryBusy"
          @click="downloadAndDeliver"
        >下载并发出</n-button>
        <n-button
          v-else-if="canMarkDelivered"
          size="small"
          type="primary"
          :loading="deliveryBusy"
          @click="markDelivery('delivered')"
        >标记已发出</n-button>
        <n-button
          v-if="canMarkReady"
          size="small"
          :type="canMarkDelivered ? 'default' : 'primary'"
          :secondary="!!canMarkDelivered"
          :loading="deliveryBusy"
          @click="markDelivery('ready')"
        >{{ canMarkDelivered ? '暂存待发' : '标记已审待发' }}</n-button>
        <n-button
          v-if="canUndoDelivery"
          size="small"
          secondary
          :loading="deliveryBusy"
          @click="undoDelivery"
        >{{ undoDeliveryLabel }}</n-button>
        <n-button
          v-if="!canDownloadAndDeliver"
          size="small"
          :disabled="!canDownload"
          :title="downloadBlockedReason"
          @click="downloadZip"
        >
          {{ downloadZipLabel }}
        </n-button>
        <n-button type="error" secondary size="small" :disabled="deleteBlocked" :title="deleteBlockedReason" @click="onDelete">删除</n-button>
      </div>
    </div>

    <n-tabs v-model:value="tab" type="line" animated>
      <n-tab-pane name="match" tab="匹配确认">
        <MatchTab />
      </n-tab-pane>
      <n-tab-pane name="generate" tab="一键生成">
        <GenerateTab />
      </n-tab-pane>
      <n-tab-pane name="runtime" tab="运行">
        <RuntimeTab />
      </n-tab-pane>
      <n-tab-pane name="logs" tab="日志">
        <LogsTab />
      </n-tab-pane>
      <n-tab-pane name="artifacts" tab="产物 / 对照">
        <ArtifactsTab />
      </n-tab-pane>
    </n-tabs>

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
import { provide, reactive } from 'vue'
import ErrorPage from './ErrorPage.vue'
import PageSkeleton from '../components/PageSkeleton.vue'
import CopyIconButton from '../components/CopyIconButton.vue'
import { PD_KEY } from './projectDetail/context'
import { useProjectDetail } from './projectDetail/useProjectDetail'
import MatchTab from './projectDetail/MatchTab.vue'
import GenerateTab from './projectDetail/GenerateTab.vue'
import RuntimeTab from './projectDetail/RuntimeTab.vue'
import LogsTab from './projectDetail/LogsTab.vue'
import ArtifactsTab from './projectDetail/ArtifactsTab.vue'
import DetailModals from './projectDetail/DetailModals.vue'

const detail = useProjectDetail()
provide(PD_KEY, reactive(detail))

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
  canDownload,
  deliveryBusy,
  downloadBlockedReason,
  downloadZipLabel,
  undoDeliveryLabel,
  deleteBlocked,
  deleteBlockedReason,
  downloadAndDeliver,
  markDelivery,
  undoDelivery,
  downloadZip,
  onDelete,
  reload,
} = detail
</script>
