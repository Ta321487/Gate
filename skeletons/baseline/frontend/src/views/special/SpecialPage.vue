<template>
  <div class="sp" :data-kind="copy.kind">
    <div class="sp-glow" aria-hidden="true" />
    <div class="sp-card">
      <div class="sp-brand">{{ copy.appName }}</div>
      <p class="sp-domain">{{ copy.domainLabel }} · {{ themeLabel }}</p>

      <SpecialMotif :name="copy.motif" />

      <p v-if="copy.code" class="sp-code">{{ copy.code }}</p>
      <div v-else class="sp-pulse" aria-hidden="true">
        <span /><span /><span />
      </div>

      <h1 class="sp-title">{{ copy.title }}</h1>
      <p class="sp-lead">{{ copy.lead }}</p>
      <p v-if="copy.hint" class="sp-hint">{{ copy.hint }}</p>

      <div v-if="copy.kind === 'loading'" class="sp-skel" aria-hidden="true">
        <div class="bar w80" />
        <div class="bar w60" />
        <div class="bar w90" />
        <div class="cards">
          <div class="card" /><div class="card" /><div class="card" />
        </div>
      </div>

      <div class="sp-actions">
        <button type="button" class="btn primary" @click="goHome">{{ copy.homeLabel }}</button>
        <button v-if="copy.retryLabel" type="button" class="btn ghost" @click="reload">
          {{ copy.retryLabel }}
        </button>
        <button v-if="copy.kind === '404' && canBack" type="button" class="btn ghost" @click="goBack">
          返回上一页
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import SpecialMotif from '../../components/SpecialMotif.vue'
import { specialPageCopy } from '../../utils/domainFlavor.js'
import { getDelivered } from '../../utils/domainSchema.js'

const props = defineProps({
  /** @type {'404'|'500'|'loading'} */
  kind: { type: String, default: '404' },
})

const router = useRouter()
const copy = computed(() => specialPageCopy(props.kind))
const themeLabel = computed(() => getDelivered().theme || 'default')
const canBack = computed(() => typeof window !== 'undefined' && window.history.length > 1)

function goHome() {
  const role = localStorage.getItem('role')
  if (role === 'admin') router.push('/admin/dashboard')
  else if (localStorage.getItem('token')) router.push('/')
  else router.push('/login')
}

function goBack() {
  router.back()
}

function reload() {
  window.location.reload()
}
</script>

<style scoped>
.sp {
  min-height: 100%;
  display: grid;
  place-items: center;
  padding: 32px 20px 48px;
  position: relative;
  overflow: hidden;
  background: var(--portal-bg, #eef3f5);
}
.sp-glow {
  position: absolute;
  inset: -20% auto auto 50%;
  width: min(720px, 120vw);
  height: min(720px, 120vw);
  transform: translateX(-50%);
  background: radial-gradient(circle, var(--portal-bg-glow, rgba(11, 110, 117, 0.12)), transparent 65%);
  pointer-events: none;
}
.sp-card {
  position: relative;
  width: min(440px, 100%);
  padding: 28px 28px 26px;
  border-radius: var(--portal-radius-lg, 20px);
  background: var(--portal-surface, #fff);
  border: var(--portal-border-width, 1px) solid var(--portal-line, #d5dde3);
  box-shadow: var(--portal-shadow, 0 8px 24px rgba(0, 0, 0, 0.06));
  text-align: center;
}
.sp-brand {
  font-family: var(--portal-font-display, "Noto Serif SC", "Songti SC", serif);
  font-size: 22px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--portal-brand, #08545a);
  margin-bottom: 4px;
}
.sp-domain {
  margin: 0 0 20px;
  font-size: 12px;
  letter-spacing: 0.04em;
  color: var(--portal-muted, #6b7c8a);
}
.sp-code {
  margin: 18px 0 6px;
  font-family: var(--portal-font-ui, "Plus Jakarta Sans", "Noto Sans SC", sans-serif);
  font-size: 40px;
  font-weight: 700;
  letter-spacing: -0.04em;
  line-height: 1;
  background: var(--portal-cover, linear-gradient(160deg, #0b6e75, #08545a));
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.sp-pulse {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin: 20px 0 8px;
}
.sp-pulse span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--portal-accent, #0b6e75);
  animation: pulse 1.2s ease-in-out infinite;
}
.sp-pulse span:nth-child(2) { animation-delay: 0.15s; }
.sp-pulse span:nth-child(3) { animation-delay: 0.3s; }
@keyframes pulse {
  0%, 100% { opacity: 0.35; transform: translateY(0); }
  50% { opacity: 1; transform: translateY(-4px); }
}
.sp-title {
  margin: 0 0 10px;
  font-family: var(--portal-font-display, "Noto Serif SC", "Songti SC", serif);
  font-size: 24px;
  line-height: 1.3;
  color: var(--portal-ink, #15202b);
}
.sp-lead {
  margin: 0 0 8px;
  font-size: 14px;
  line-height: 1.6;
  color: var(--portal-ink, #15202b);
}
.sp-hint {
  margin: 0 0 4px;
  font-size: 13px;
  line-height: 1.55;
  color: var(--portal-muted, #6b7c8a);
}
.sp-skel {
  margin: 18px 0 4px;
  text-align: left;
}
.sp-skel .bar {
  height: 10px;
  border-radius: var(--portal-radius-sm, 6px);
  margin-bottom: 10px;
  background: linear-gradient(
    90deg,
    var(--portal-accent-soft, #d7eef0) 0%,
    var(--portal-line, #d5dde3) 45%,
    var(--portal-accent-soft, #d7eef0) 100%
  );
  background-size: 200% 100%;
  animation: shimmer 1.4s ease-in-out infinite;
}
.sp-skel .w80 { width: 80%; }
.sp-skel .w60 { width: 60%; }
.sp-skel .w90 { width: 90%; }
.sp-skel .cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-top: 14px;
}
.sp-skel .card {
  height: 56px;
  border-radius: var(--portal-radius, 10px);
  background: var(--portal-accent-soft, #d7eef0);
  animation: shimmer 1.4s ease-in-out infinite;
  background-image: linear-gradient(
    90deg,
    var(--portal-accent-soft, #d7eef0) 0%,
    var(--portal-line, #d5dde3) 45%,
    var(--portal-accent-soft, #d7eef0) 100%
  );
  background-size: 200% 100%;
}
@keyframes shimmer {
  0% { background-position: 100% 0; }
  100% { background-position: -100% 0; }
}
.sp-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: center;
  margin-top: 22px;
}
.btn {
  appearance: none;
  border: var(--portal-border-width, 1px) solid transparent;
  border-radius: var(--portal-btn-radius, 10px);
  padding: 10px 16px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
}
.btn.primary {
  background: var(--portal-accent, #0b6e75);
  color: #fff;
}
.btn.primary:hover {
  filter: brightness(1.05);
}
.btn.ghost {
  background: transparent;
  border-color: var(--portal-line, #d5dde3);
  color: var(--portal-ink, #15202b);
}
.btn.ghost:hover {
  border-color: var(--portal-accent, #0b6e75);
  color: var(--portal-accent, #0b6e75);
}
@media (max-width: 480px) {
  .sp-card { padding: 22px 18px 20px; }
  .sp-title { font-size: 20px; }
  .sp-code { font-size: 34px; }
}
</style>
