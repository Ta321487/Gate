<template>
  <div>
    <section class="hero">
      <h1>{{ pageTitle }}</h1>
      <p>{{ pageLead }}</p>
    </section>
    <article class="card">
      <p class="body">{{ pageBody }}</p>
      <ul v-if="bits.length" class="bits">
        <li v-for="(b, i) in bits" :key="i">{{ b }}</li>
      </ul>
    </article>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { getSchema, schemaLabels } from '../../utils/domainSchema.js'

const labels = computed(() => schemaLabels())
const schema = computed(() => getSchema() || {})
const pageTitle = computed(() => labels.value.pointsRulesPageTitle || '积分规则')
const pageLead = computed(
  () => labels.value.pointsRulesPageLead || '说明如何获得与使用积分；具体分值以当前规则为准。',
)
const pageBody = computed(
  () =>
    labels.value.pointsRulesBody
    || '登录奖励、精华奖励与资料下载扣分会记入积分流水。本页仅说明规则，不是支付收银台。',
)
const bits = computed(() => {
  const out = []
  const pts = schema.value.points || {}
  const thicken = schema.value.contentThicken || {}
  if (thicken.pointsCheckIn || pts.checkInEnabled || schema.value.pointsCheckInEnabled) {
    const n = Number(schema.value.pointsCheckInAmount || pts.checkInPoints || 10)
    const name = labels.value.pointsCheckInLabel || '每日登录奖励'
    out.push(`${name}：每天首次登录可获得 ${n} 积分`)
  }
  if (thicken.essencePointsReward) {
    const n = Number(schema.value.essencePointsReward || 20)
    const name = labels.value.essencePointsRewardLabel || '精华奖励积分'
    out.push(`${name}：帖子被标为精华时，作者可获得 ${n} 积分`)
  }
  if (thicken.docPointsDownload || thicken.docPaidDownload) {
    out.push('文库资料若标了所需积分，下载前会先扣分并记入流水')
  }
  return out
})
</script>

<style scoped>
.hero { margin-bottom: 16px; }
.hero h1 { margin: 0 0 6px; font-size: 22px; }
.hero p { margin: 0; color: var(--portal-muted, #64748b); font-size: 13px; }
.card {
  background: var(--portal-surface, #fff);
  border: var(--portal-border-width, 1px) solid var(--portal-line, #e2e8f0);
  border-radius: var(--portal-radius, 12px);
  padding: var(--portal-pad, 14px) 16px;
}
.body { margin: 0; line-height: 1.6; white-space: pre-wrap; }
.bits { margin: 12px 0 0; padding-left: 1.2rem; line-height: 1.7; color: var(--portal-muted, #64748b); }
</style>
