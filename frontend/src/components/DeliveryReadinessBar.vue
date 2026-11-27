<template>
  <div v-if="ready" class="delivery-ready" :class="'tone-' + (ready.primary.tone || 'neutral')">
    <div class="delivery-ready-main">
      <div class="delivery-ready-title-row">
        <span class="pill" :class="pillClass">{{ ready.title }}</span>
        <span class="delivery-ready-impact">{{ ready.downloadImpact }}</span>
      </div>
      <ul v-if="ready.blockers.length" class="delivery-ready-blockers">
        <li v-for="(b, i) in ready.blockers" :key="i">{{ b.text }}</li>
      </ul>
      <p v-if="ready.recoveryHint" class="small muted delivery-ready-ok">{{ ready.recoveryHint }}</p>
      <p
        v-else-if="!ready.blockers.length && sameStageAsPrimary && sameStageHint"
        class="small muted delivery-ready-ok"
      >{{ sameStageHint }}</p>
    </div>
    <div class="delivery-ready-actions">
      <!-- 人已在目标阶段：不放同义 primary，避免与页内主 CTA 打架；下载仍只在质检强调 -->
      <span v-if="sameStageAsPrimary" class="small muted delivery-ready-same">{{ sameStageHint }}</span>
      <n-button
        v-else
        size="medium"
        :type="primaryBtnType"
        :secondary="primarySecondary"
        :loading="primaryLoading"
        :disabled="primaryDisabled"
        @click="onPrimary"
      >
        {{ ready.primary.label }}
      </n-button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { buildDeliveryReadiness } from '../deliveryReadiness'

const props = defineProps({
  project: { type: Object, default: null },
  /** 当前详情阶段：非质检时下载类主按钮降为 secondary，避免与页内 CTA 双 primary */
  activeTab: { type: String, default: '' },
  scrubBusy: { type: Boolean, default: false },
  deliveryBusy: { type: Boolean, default: false },
  jobActing: { type: [String, Boolean], default: '' },
})

const emit = defineEmits([
  'match',
  'generate',
  'retry',
  'scrub',
  'gates',
  'review',
  'download',
  'download-deliver',
])

const ready = computed(() => buildDeliveryReadiness(props.project))

const pillClass = computed(() => {
  const tone = ready.value?.primary?.tone || 'neutral'
  return ({
    ok: 'pill-green',
    warn: 'pill-amber',
    fail: 'pill-red',
    info: 'pill-teal',
    neutral: 'pill-neutral',
  })[tone] || 'pill-neutral'
})

/**
 * 人已在就绪条所指阶段：不放同义跳转钮，改提示「见下方」。
 * 下载/downloadDeliver 不在此列——质检页仍要顶栏主下载。
 */
const sameStageAsPrimary = computed(() => {
  const tab = String(props.activeTab || '')
  const key = ready.value?.primary?.key || ''
  if (!tab || !key) return false
  if (key === 'match' && tab === 'match') return true
  if (key === 'generate' && tab === 'generate') return true
  if (key === 'retry' && tab === 'generate') return true
  if (['gates', 'review', 'scrub'].includes(key) && tab === 'artifacts') return true
  return false
})

const sameStageHint = computed(() => {
  const key = ready.value?.primary?.key || ''
  if (key === 'match') return '请在下方确认匹配'
  if (key === 'generate') return '请在下方一键生成'
  if (key === 'retry') return '请在下方从失败步骤重试'
  if (key === 'scrub') return '请在下方质检工作台清洗文案'
  if (key === 'review' || key === 'gates') return '请在下方质检工作台继续'
  return '请在下方继续当前步骤'
})

/** 非质检阶段：下载类主按钮降为 secondary（人还在匹配/生成等页） */
const demoteDownloadOnTab = computed(() => {
  const tab = String(props.activeTab || '')
  const key = ready.value?.primary?.key
  if (!['download', 'downloadDeliver'].includes(key)) return false
  return tab && tab !== 'artifacts'
})

const primaryBtnType = computed(() => {
  if (demoteDownloadOnTab.value) return 'default'
  const tone = ready.value?.primary?.tone
  if (tone === 'ok') return 'primary'
  if (tone === 'fail') return 'error'
  if (tone === 'warn') return 'warning'
  if (tone === 'info') return 'primary'
  return 'default'
})

const primarySecondary = computed(() => demoteDownloadOnTab.value)

const primaryLoading = computed(() => {
  const key = ready.value?.primary?.key
  if (key === 'scrub') return !!props.scrubBusy
  if (key === 'download' || key === 'downloadDeliver') return !!props.deliveryBusy
  if (key === 'retry') return props.jobActing === 'retry'
  return false
})

const primaryDisabled = computed(() => {
  const key = ready.value?.primary?.key
  if (key === 'scrub') return !!props.scrubBusy
  return false
})

function onPrimary() {
  const key = ready.value?.primary?.key
  if (!key) return
  if (key === 'downloadDeliver') emit('download-deliver')
  else emit(key)
}
</script>

<style scoped>
.delivery-ready {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  justify-content: space-between;
  flex-wrap: wrap;
  padding: 12px 14px;
  margin-bottom: 14px;
  border-radius: 8px;
  border: 1px solid var(--line);
  background: var(--surface-2);
}
.delivery-ready.tone-ok {
  background: var(--banner-ok-bg);
  border-color: var(--banner-ok-line);
}
.delivery-ready.tone-warn {
  background: var(--banner-warn-bg);
  border-color: var(--banner-warn-line);
}
.delivery-ready.tone-fail {
  background: var(--banner-fail-bg);
  border-color: var(--banner-fail-line);
}
.delivery-ready.tone-info {
  background: var(--teal-soft);
  border-color: var(--line);
}
.delivery-ready-main {
  flex: 1 1 240px;
  min-width: 0;
}
.delivery-ready-title-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
  align-items: center;
}
.delivery-ready-impact {
  font-size: 13px;
  color: var(--ink-2);
  font-weight: 600;
}
.delivery-ready-blockers {
  margin: 8px 0 0;
  padding-left: 1.2em;
  font-size: 13px;
  line-height: 1.45;
  color: var(--ink-2);
}
.delivery-ready-blockers li {
  margin: 2px 0;
}
.delivery-ready-ok {
  margin: 8px 0 0;
}
.delivery-ready-actions {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  max-width: 220px;
  text-align: right;
}
.delivery-ready-same {
  line-height: 1.4;
}
</style>
