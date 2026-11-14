<template>
  <div id="delivery-workbench" class="delivery-workbench stack">
    <div class="wb-head row-between" style="align-items:flex-start;gap:12px">
      <div>
        <h2 class="wb-title">
          质检交付
          <span class="pill" :class="canDownload ? 'pill-green' : 'pill-red'" style="margin-left:8px;font-weight:600">
            {{ canDownload ? '可下载' : '暂不可下载' }}
          </span>
        </h2>
        <p v-if="downloadBlockedReason" class="small" style="margin:6px 0 0">
          <strong>阻断：</strong>{{ downloadBlockedReason }}
        </p>
        <p v-else class="small muted" style="margin:6px 0 0">
          下载 ZIP 用上方就绪条主操作；本页只做清洗、验收与重打包。
        </p>
      </div>
      <n-button
        v-if="showScrubCopy"
        size="small"
        secondary
        :disabled="disabled || scrubBusy"
        :loading="scrubBusy"
        @click="emit('scrub')"
      >
        清洗文案
      </n-button>
    </div>

    <div class="wb-summary row" style="gap:8px;flex-wrap:wrap;margin:0">
      <span class="pill" :class="gateFailCount ? 'pill-amber' : 'pill-green'">
        门禁 {{ gatePassCount }}/{{ gateRows.length || 0 }}
      </span>
      <span class="pill" :class="checkFailCount ? 'pill-amber' : 'pill-green'">
        清单 {{ checkPassCount }}/{{ checkRows.length || 0 }}
      </span>
      <span v-if="copyGateHits.length" class="pill pill-amber">
        工厂用语 {{ copyGateHits.length }} 处
      </span>
    </div>

    <n-collapse class="wb-details" :default-expanded-names="detailDefaultOpen">
      <n-collapse-item
        :title="gateFailCount || checkFailCount
          ? `门禁与清单明细 · 门禁未过 ${gateFailCount} · 清单未覆盖 ${checkFailCount}`
          : '门禁与清单明细'"
        name="gates"
      >
        <div class="workbench-gates">
          <div class="parse-sec-hd" style="margin:0">质量门禁</div>
          <n-data-table
            class="mt-8"
            :columns="gateCols"
            :data="gateRows"
            :bordered="false"
            size="small"
          />
          <div v-if="showScrubCopy || copyGateHits.length" class="mt-12">
            <div class="parse-sec-hd">不宜出现的工厂用语 · {{ copyGateHits.length || '—' }} 处</div>
            <ul v-if="copyGateHits.length" class="zone-list" style="margin:0">
              <li v-for="(h, i) in copyGateHits" :key="i">
                <strong>{{ h.bad }}</strong>
                <span class="muted"> · {{ h.path }}</span>
                <div class="small muted" style="margin-top:2px">{{ h.snippet }}</div>
              </li>
            </ul>
            <p v-else class="small muted" style="margin:0">
              门禁未过但未带回命中明细时，仍可直接清洗后验收。
            </p>
          </div>
          <div class="parse-sec-hd mt-12">清单实装验收</div>
          <n-data-table
            class="mt-8"
            :columns="checkCols"
            :data="checkRows"
            :bordered="false"
            size="small"
          />
        </div>
      </n-collapse-item>
    </n-collapse>

    <DeliveryReviewPane
      :project-id="projectId"
      :delivery-review="deliveryReview"
      :disabled="disabled"
      :reload="reload"
      :apply-review="applyReview"
      :show-scrub-copy="showScrubCopy"
      :scrub-busy="scrubBusy"
      :scrub-copy="scrubCopy"
      :go-generate="goGenerate"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import DeliveryReviewPane from './DeliveryReviewPane.vue'

const props = defineProps({
  projectId: { type: [String, Number], required: true },
  deliveryReview: { type: Object, default: () => ({}) },
  disabled: { type: Boolean, default: false },
  canDownload: { type: Boolean, default: false },
  downloadBlockedReason: { type: String, default: '' },
  gateCols: { type: Array, default: () => [] },
  gateRows: { type: Array, default: () => [] },
  checkCols: { type: Array, default: () => [] },
  checkRows: { type: Array, default: () => [] },
  copyGateHits: { type: Array, default: () => [] },
  showScrubCopy: { type: Boolean, default: false },
  scrubBusy: { type: Boolean, default: false },
  scrubCopy: { type: Function, default: null },
  reload: { type: Function, default: null },
  applyReview: { type: Function, default: null },
  goGenerate: { type: Function, default: null },
})

const emit = defineEmits(['scrub'])

const gatePassCount = computed(() => (props.gateRows || []).filter((r) => r?.ok).length)
const gateFailCount = computed(() => (props.gateRows || []).filter((r) => r && !r.ok).length)
const checkPassCount = computed(() =>
  (props.checkRows || []).filter((r) => r && (r.result === 'done' || r.result === 'out_of_mvp')).length,
)
const checkFailCount = computed(() =>
  (props.checkRows || []).filter((r) => r && r.result === 'pending').length,
)

/** 失败时也不自动撑开全表——摘要 pill + 下方阻断卡已够；明细按需点开 */
const detailDefaultOpen = computed(() => [])
</script>

<style scoped>
.delivery-workbench {
  gap: 10px;
}
.wb-title {
  margin: 0;
  font-size: 14px;
  font-weight: 650;
}
.wb-summary {
  padding: 2px 0 0;
}
.wb-details {
  margin-top: 2px;
}
.workbench-gates {
  padding: 4px 0 0;
}
.zone-list {
  padding-left: 1.1em;
  margin: 0;
  font-size: 13px;
  line-height: 1.45;
}
</style>
