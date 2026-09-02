<template>
  <div class="file-row ppt-artifact-row" style="margin:0">
    <div class="file-row-main">
      <strong>答辩 PPT</strong>
      <span class="small muted">
        <template v-if="pptHasDeck">
          {{ pptDeckSummary || '已生成' }} · {{ pptFingerprintHint }}
        </template>
        <template v-else-if="pptPhase === 'generating'">
          生成中 · {{ pptJob?.progress || 0 }}%
        </template>
        <template v-else-if="pptPhase === 'locked'">
          工程通过质量检查后可生成
        </template>
        <template v-else>
          尚未生成 · 在「一键生成」页填写封面后开跑
        </template>
      </span>
      <span
        v-if="pptHasDeck"
        class="pill"
        :class="pptBizDirty ? 'pill-amber' : 'pill-green'"
        style="margin-left:8px"
      >
        {{ pptBizDirty ? '⚠ 业务可能不一致' : '与工程一致' }}
      </span>
    </div>
    <div class="row" style="margin:0;gap:6px;flex-wrap:wrap">
      <n-button size="small" :disabled="!pptHasDeck" @click="openPptCompare">打开对照</n-button>
      <n-button size="small" :disabled="!pptHasDeck" :loading="pptActing === 'check'" @click="runPptCheck">检查</n-button>
      <n-button
        size="small"
        :disabled="!pptHasDeck || pptBizDirty"
        :loading="pptActing === 'export'"
        :title="pptBizDirty ? '业务指纹脏 · 禁止导出' : '导出 PPTX（不进 ZIP）'"
        @click="exportPptx"
      >
        导出 PPTX
      </n-button>
    </div>
  </div>
</template>

<script setup>
import { bindPd } from '../../views/projectDetail/bindPd'

const {
  pptHasDeck,
  pptDeckSummary,
  pptFingerprintHint,
  pptPhase,
  pptJob,
  pptBizDirty,
  pptActing,
  openPptCompare,
  runPptCheck,
  exportPptx,
} = bindPd()
</script>
