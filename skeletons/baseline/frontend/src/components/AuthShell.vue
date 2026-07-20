<template>
  <div
    class="auth"
    :data-auth="template"
    :data-watermark="watermark"
    :data-hero="heroOn ? '1' : '0'"
    :data-wide="wide ? '1' : '0'"
    :style="heroCssVars"
  >
    <div class="stage">
      <aside class="brand">
        <div class="glow" aria-hidden="true" />
        <p class="eyebrow">{{ eyebrow }}</p>
        <h1 class="title">{{ title }}</h1>
        <p class="lead">{{ lead }}</p>
        <ul v-if="points?.length" class="points">
          <li v-for="(p, i) in points" :key="i">{{ p }}</li>
        </ul>
      </aside>

      <section class="panel">
        <header class="panel-hd">
          <h2>{{ heading }}</h2>
          <p v-if="sub">{{ sub }}</p>
        </header>
        <slot />
        <footer v-if="$slots.footer" class="panel-ft">
          <slot name="footer" />
        </footer>
        <p v-if="note" class="note">{{ note }}</p>
      </section>
    </div>
  </div>
</template>

<script setup>
/**
 * 基线鉴权壳：版式由 bake 的 VITE_AUTH_TEMPLATE 固定；氛围图来自 appDelivered.authHero。
 */
import { computed, onMounted, ref } from 'vue'
import { APP_DELIVERED } from '../appDelivered.js'

const props = defineProps({
  template: { type: String, required: true },
  title: { type: String, default: '毕设系统' },
  eyebrow: { type: String, default: '欢迎使用' },
  lead: { type: String, default: '' },
  points: { type: Array, default: () => [] },
  heading: { type: String, default: '' },
  sub: { type: String, default: '' },
  note: { type: String, default: '' },
  watermark: { type: String, default: '' },
  /** 注册等字段多时加宽面板，便于分栏 */
  wide: { type: Boolean, default: false },
})

const heroSrc = computed(() => (APP_DELIVERED?.authHero || '').trim())
const heroOk = ref(!!heroSrc.value)
const heroOn = computed(() => heroOk.value && !!heroSrc.value)
const heroCssVars = computed(() => {
  if (!heroOn.value) return undefined
  return { '--auth-hero': `url('${heroSrc.value}')` }
})

onMounted(() => {
  const src = heroSrc.value
  if (!src) {
    heroOk.value = false
    return
  }
  const img = new Image()
  img.onload = () => { heroOk.value = true }
  img.onerror = () => { heroOk.value = false }
  img.src = src
})
</script>

<style scoped>
.auth {
  --auth-radius: 18px;
  box-sizing: border-box;
  /* 用父级 100% 高度，避免 100vh+padding 撑出整页滚动条 */
  height: 100%;
  min-height: 100%;
  max-height: 100%;
  overflow-x: hidden;
  overflow-y: auto;
  display: grid;
  place-items: center;
  padding: 28px 20px;
  color: var(--portal-ink, #15202b);
  background:
    radial-gradient(900px 420px at 8% -10%, var(--portal-bg-glow, rgba(11, 110, 117, 0.16)), transparent 60%),
    radial-gradient(700px 360px at 100% 100%, color-mix(in srgb, var(--portal-accent, #0b6e75) 10%, transparent), transparent 55%),
    linear-gradient(165deg, var(--portal-bg, #eef3f5) 0%, color-mix(in srgb, var(--portal-bg, #eef3f5) 72%, #fff) 100%);
}

.stage {
  width: min(920px, 100%);
  position: relative;
  display: grid;
  grid-template-columns: 1.05fr 0.95fr;
  border-radius: var(--auth-radius);
  overflow: hidden;
  border: 1px solid var(--portal-line, #d5dde3);
  background: var(--portal-surface, #fff);
  box-shadow: var(--portal-shadow, 0 16px 40px rgba(15, 40, 50, 0.1));
}

.brand {
  position: relative;
  padding: 40px 36px 36px;
  background: linear-gradient(
    160deg,
    color-mix(in srgb, var(--portal-accent, #0b6e75) 92%, #000) 0%,
    var(--portal-brand, #08545a) 100%
  );
  color: #f4fbfb;
  overflow: hidden;
}
.glow {
  position: absolute;
  inset: auto -20% -30% 20%;
  height: 70%;
  background: radial-gradient(circle at 30% 40%, rgba(255, 255, 255, 0.22), transparent 55%);
  pointer-events: none;
}
.eyebrow {
  position: relative;
  margin: 0 0 14px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  opacity: 0.78;
}
.title {
  position: relative;
  margin: 0 0 14px;
  font-size: clamp(26px, 3.2vw, 34px);
  line-height: 1.25;
  letter-spacing: -0.03em;
  font-weight: 700;
}
.lead {
  position: relative;
  margin: 0 0 28px;
  font-size: 14px;
  line-height: 1.65;
  opacity: 0.88;
  max-width: 28em;
}
.points {
  position: relative;
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 10px;
}
.points li {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  opacity: 0.92;
}
.points li::before {
  content: "";
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.85);
  flex-shrink: 0;
}
.tpl-tag {
  position: relative;
  margin: 28px 0 0;
  font-size: 11px;
  letter-spacing: 0.06em;
  opacity: 0.55;
}

.panel {
  padding: 36px 34px 28px;
  display: flex;
  flex-direction: column;
  background: var(--portal-surface, #fff);
}
.panel-hd h2 {
  margin: 0 0 6px;
  font-size: 24px;
  letter-spacing: -0.03em;
  color: var(--portal-ink, #15202b);
}
.panel-hd p {
  margin: 0 0 22px;
  color: var(--portal-muted, #6b7c8a);
  font-size: 13px;
}
.panel-ft {
  margin-top: 22px;
  padding-top: 16px;
  border-top: 1px solid var(--portal-line, #dfe7ec);
  font-size: 13px;
  color: var(--portal-muted, #6b7c8a);
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.panel-ft :deep(a) {
  color: var(--portal-accent, #0b6e75);
  font-weight: 600;
  text-decoration: none;
}
.panel-ft :deep(a:hover) { text-decoration: underline; }
.note {
  margin: 12px 0 0;
  font-size: 12px;
  color: var(--portal-muted, #8a9aa6);
  line-height: 1.45;
}

/* 有氛围图：品牌栏铺图 */
.auth[data-hero="1"][data-auth="split"] .brand,
.auth[data-hero="1"][data-auth="mirror"] .brand,
.auth[data-hero="1"][data-auth="ribbon"] .brand {
  background-image:
    linear-gradient(
      160deg,
      color-mix(in srgb, var(--portal-brand, #08545a) 78%, transparent) 0%,
      color-mix(in srgb, var(--portal-accent, #0b6e75) 55%, transparent) 100%
    ),
    var(--auth-hero);
  background-size: cover;
  background-position: center;
}
.auth[data-hero="1"][data-auth="folio"] .brand {
  background-image:
    linear-gradient(
      180deg,
      color-mix(in srgb, var(--portal-surface, #fff) 88%, transparent) 0%,
      color-mix(in srgb, var(--portal-bg, #eef3f5) 72%, transparent) 100%
    ),
    var(--auth-hero);
  background-size: cover;
  background-position: center;
  color: var(--portal-ink, #15202b);
}

/* —— 2 mirror —— */
.auth[data-auth="mirror"] .stage {
  grid-template-columns: 0.95fr 1.05fr;
}
.auth[data-auth="mirror"] .brand { order: 2; }
.auth[data-auth="mirror"] .panel { order: 1; }

/* —— 3 center：全屏氛围 —— */
.auth[data-auth="center"] {
  place-items: center;
}
.auth[data-hero="1"][data-auth="center"] {
  background:
    linear-gradient(
      165deg,
      color-mix(in srgb, var(--portal-bg, #eef3f5) 82%, transparent) 0%,
      color-mix(in srgb, #fff 55%, transparent) 100%
    ),
    var(--auth-hero) center / cover no-repeat;
}
.auth[data-auth="center"] .stage {
  width: min(420px, 100%);
  grid-template-columns: 1fr;
  border: none;
  background: transparent;
  box-shadow: none;
  overflow: visible;
}
.auth[data-auth="center"] .brand {
  background: transparent;
  color: var(--portal-ink, #15202b);
  text-align: center;
  padding: 8px 12px 18px;
}
.auth[data-auth="center"] .glow { display: none; }
.auth[data-auth="center"] .eyebrow {
  color: var(--portal-accent, #0b6e75);
  opacity: 1;
}
.auth[data-auth="center"] .lead {
  margin: 0 auto 0;
  opacity: 1;
  color: var(--portal-muted, #6b7c8a);
}
.auth[data-auth="center"] .points,
.auth[data-auth="center"] .tpl-tag { display: none; }
.auth[data-auth="center"] .panel {
  border-radius: var(--auth-radius);
  border: 1px solid var(--portal-line, #d5dde3);
  box-shadow: var(--portal-shadow, 0 16px 40px rgba(15, 40, 50, 0.1));
}

/* —— 4 ribbon —— */
.auth[data-auth="ribbon"] .stage {
  width: min(520px, 100%);
  grid-template-columns: 1fr;
}
.auth[data-auth="ribbon"] .brand {
  padding: 28px 28px 24px;
  min-height: auto;
}
.auth[data-auth="ribbon"] .lead { margin-bottom: 0; max-width: none; }
.auth[data-auth="ribbon"] .points { display: none; }
.auth[data-auth="ribbon"] .tpl-tag { margin-top: 16px; }
.auth[data-auth="ribbon"] .panel { padding-top: 28px; }

/* —— 5 ledge：全屏氛围 + 水印 —— */
.auth[data-auth="ledge"] {
  align-items: end;
  padding: 16px 20px 28px;
}
.auth[data-auth="ledge"] .title {
  font-size: clamp(22px, 2.6vw, 28px);
  margin-bottom: 8px;
}
.auth[data-auth="ledge"] .lead {
  font-size: 13px;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.auth[data-auth="ledge"] .panel {
  padding: 22px 24px 18px;
}
/* 宽面板：注册分步 —— 双栏版式要加宽（勿压窄）；单栏版式略加宽即可 */
.auth[data-wide="1"] {
  align-items: center;
  padding: 20px 24px 24px;
}
/* split / mirror / folio：默认 920，注册再加宽 */
.auth[data-wide="1"] .stage {
  width: min(1080px, 96vw);
}
.auth[data-wide="1"][data-auth="mirror"] .stage,
.auth[data-wide="1"][data-auth="split"] .stage,
.auth[data-wide="1"][data-auth="folio"] .stage {
  width: min(1080px, 96vw);
  min-height: min(560px, calc(100% - 32px));
}
.auth[data-wide="1"][data-auth="ledge"] {
  padding-bottom: 20px;
}
.auth[data-wide="1"][data-auth="ledge"] .stage {
  width: min(560px, 100%);
  margin-right: clamp(0px, 4vw, 40px);
}
.auth[data-wide="1"][data-auth="ledge"] .brand {
  padding: 0 4px 8px;
}
.auth[data-wide="1"][data-auth="ledge"] .title {
  font-size: clamp(18px, 2.2vw, 24px);
  margin-bottom: 4px;
}
.auth[data-wide="1"][data-auth="ledge"] .lead {
  display: none;
}
/* center / ribbon：单栏默认偏窄，注册略加宽 */
.auth[data-wide="1"][data-auth="ribbon"] .stage {
  width: min(560px, 100%);
}
.auth[data-wide="1"][data-auth="card"] .stage,
.auth[data-wide="1"][data-auth="center"] .stage {
  width: min(520px, 100%);
}
.auth[data-wide="1"] .panel {
  padding: 28px 32px 22px;
}
.auth[data-wide="1"] .panel-hd h2 { font-size: 22px; margin-bottom: 4px; }
.auth[data-wide="1"] .panel-hd p { margin-bottom: 12px; font-size: 13px; }
.auth[data-wide="1"] .panel-ft {
  margin-top: 14px;
  padding-top: 12px;
}
.auth[data-auth="ledge"] .panel-hd h2 { font-size: 20px; }
.auth[data-auth="ledge"] .panel-hd p { margin-bottom: 14px; }
.auth[data-auth="ledge"] .panel-ft {
  margin-top: 14px;
  padding-top: 12px;
}
.auth[data-hero="1"][data-auth="ledge"] {
  background:
    linear-gradient(
      115deg,
      color-mix(in srgb, var(--portal-bg, #eef3f5) 78%, transparent) 0%,
      color-mix(in srgb, #fff 40%, transparent) 55%,
      color-mix(in srgb, var(--portal-accent, #0b6e75) 18%, transparent) 100%
    ),
    var(--auth-hero) center / cover no-repeat fixed;
}
.auth[data-auth="ledge"] .stage {
  width: min(440px, 100%);
  margin-left: auto;
  margin-right: clamp(0px, 8vw, 80px);
  grid-template-columns: 1fr;
  border: none;
  background: transparent;
  box-shadow: none;
  overflow: visible;
}
.auth[data-auth="ledge"]::before {
  content: attr(data-watermark);
  position: fixed;
  left: 4vw;
  bottom: 8vh;
  font-size: clamp(48px, 12vw, 120px);
  font-weight: 800;
  letter-spacing: -0.06em;
  line-height: 0.9;
  color: color-mix(in srgb, var(--portal-accent, #0b6e75) 14%, transparent);
  pointer-events: none;
  max-width: 50vw;
  word-break: break-all;
  z-index: 0;
}
/* 有氛围图时不再叠巨型截断水印，避免「校园网故障报修管」半截字 */
.auth[data-hero="1"][data-auth="ledge"]::before {
  display: none;
}
.auth[data-auth="ledge"] .stage { z-index: 1; }
.auth[data-auth="ledge"] .brand {
  background: transparent;
  color: var(--portal-ink, #15202b);
  padding: 0 8px 16px;
}
.auth[data-hero="1"][data-auth="ledge"] .brand {
  color: #f7fbfb;
  text-shadow: 0 1px 12px rgba(0, 0, 0, 0.35);
}
.auth[data-hero="1"][data-auth="ledge"] .eyebrow {
  color: #e8fffb;
}
.auth[data-hero="1"][data-auth="ledge"] .lead {
  color: color-mix(in srgb, #fff 88%, transparent);
}
.auth[data-auth="ledge"] .glow,
.auth[data-auth="ledge"] .points,
.auth[data-auth="ledge"] .tpl-tag { display: none; }
.auth[data-auth="ledge"] .eyebrow {
  color: var(--portal-accent, #0b6e75);
  opacity: 1;
}
.auth[data-auth="ledge"] .lead {
  color: var(--portal-muted, #6b7c8a);
  opacity: 1;
  margin-bottom: 0;
}
.auth[data-auth="ledge"] .panel {
  border-radius: 16px 16px 4px 4px;
  border: 1px solid var(--portal-line, #d5dde3);
  border-bottom-width: 4px;
  border-bottom-color: var(--portal-accent, #0b6e75);
  box-shadow: 0 20px 48px rgba(15, 40, 50, 0.12);
}

/* —— 6 folio —— */
.auth[data-auth="folio"] .stage {
  grid-template-columns: 1fr 1fr;
  background: color-mix(in srgb, var(--portal-surface, #fff) 94%, var(--portal-bg, #eef3f5));
}
.auth[data-auth="folio"] .brand {
  background: transparent;
  color: var(--portal-ink, #15202b);
  border-right: 1px solid var(--portal-line, #d5dde3);
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.auth[data-auth="folio"] .glow { display: none; }
.auth[data-auth="folio"] .eyebrow {
  color: var(--portal-accent, #0b6e75);
  opacity: 1;
}
.auth[data-auth="folio"] .title {
  font-size: clamp(28px, 3.6vw, 40px);
}
.auth[data-auth="folio"] .lead {
  opacity: 1;
  color: var(--portal-muted, #6b7c8a);
}
.auth[data-auth="folio"] .points li { color: var(--portal-ink, #15202b); opacity: 0.85; }
.auth[data-auth="folio"] .points li::before {
  background: var(--portal-accent, #0b6e75);
}
.auth[data-auth="folio"] .tpl-tag {
  color: var(--portal-muted, #8a9aa6);
  opacity: 1;
}
.auth[data-auth="folio"] .panel {
  background: transparent;
  justify-content: center;
}

@media (max-width: 820px) {
  .auth[data-auth="split"] .stage,
  .auth[data-auth="mirror"] .stage,
  .auth[data-auth="folio"] .stage {
    grid-template-columns: 1fr;
  }
  .auth[data-auth="mirror"] .brand { order: 0; }
  .auth[data-auth="folio"] .brand {
    border-right: none;
    border-bottom: 1px solid var(--portal-line, #d5dde3);
    padding: 28px 24px 22px;
  }
  .auth[data-auth="split"] .points,
  .auth[data-auth="mirror"] .points,
  .auth[data-auth="folio"] .points { display: none; }
  .auth[data-auth="ledge"] {
    align-items: center;
    padding-bottom: 28px;
  }
  .auth[data-auth="ledge"] .stage {
    margin-right: auto;
  }
  .auth[data-auth="ledge"]::before { display: none; }
  .auth[data-hero="1"][data-auth="ledge"] {
    background-attachment: scroll;
  }
  .brand { padding: 28px 24px 24px; }
  .panel { padding: 28px 22px 22px; }
}
</style>
