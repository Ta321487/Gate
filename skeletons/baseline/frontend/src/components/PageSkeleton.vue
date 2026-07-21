<template>
  <div class="skel" :data-variant="variant" aria-busy="true" aria-label="加载中">
    <template v-if="variant === 'detail'">
      <div class="row">
        <div class="block cover" />
        <div class="col">
          <div class="line w40" />
          <div class="line w70" />
          <div class="line w55" />
          <div class="chips">
            <span /><span />
          </div>
        </div>
      </div>
      <div class="panel">
        <div class="line w30" />
        <div class="line w90" />
        <div class="line w80" />
        <div class="line w65" />
      </div>
    </template>
    <template v-else-if="variant === 'list'">
      <div class="line w35 head" />
      <div v-for="n in rows" :key="n" class="list-row">
        <div class="block thumb" />
        <div class="col">
          <div class="line w60" />
          <div class="line w40" />
        </div>
      </div>
    </template>
    <template v-else>
      <div class="line w50" />
      <div class="line w80" />
      <div class="line w70" />
    </template>
  </div>
</template>

<script setup>
defineProps({
  /** detail | list | text */
  variant: { type: String, default: 'detail' },
  rows: { type: Number, default: 4 },
})
</script>

<style scoped>
.skel {
  padding: 8px 0;
}
.row {
  display: grid;
  grid-template-columns: 140px 1fr;
  gap: 22px;
  padding: 20px;
  background: var(--portal-surface, #fff);
  border: var(--portal-border-width, 1px) solid var(--portal-line, #dfe7ec);
  border-radius: var(--portal-radius, 12px);
  box-shadow: var(--portal-shadow, none);
}
.col { min-width: 0; }
.panel {
  margin-top: 14px;
  padding: 18px 20px;
  background: var(--portal-surface, #fff);
  border: var(--portal-border-width, 1px) solid var(--portal-line, #dfe7ec);
  border-radius: var(--portal-radius, 12px);
}
.block,
.line,
.chips span {
  background: linear-gradient(
    90deg,
    var(--portal-accent-soft, #d7eef0) 0%,
    var(--portal-line, #d5dde3) 50%,
    var(--portal-accent-soft, #d7eef0) 100%
  );
  background-size: 200% 100%;
  animation: shimmer 1.35s ease-in-out infinite;
  border-radius: var(--portal-radius-sm, 8px);
}
.cover {
  width: 140px;
  height: 180px;
}
.thumb {
  width: 48px;
  height: 48px;
  border-radius: var(--portal-radius-sm, 10px);
  flex-shrink: 0;
}
.line {
  height: 12px;
  margin-bottom: 12px;
}
.line.head { margin-bottom: 18px; }
.w30 { width: 30%; }
.w35 { width: 35%; }
.w40 { width: 40%; }
.w50 { width: 50%; }
.w55 { width: 55%; }
.w60 { width: 60%; }
.w65 { width: 65%; }
.w70 { width: 70%; }
.w80 { width: 80%; }
.w90 { width: 90%; }
.chips {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}
.chips span {
  display: block;
  width: 64px;
  height: 24px;
  border-radius: 999px;
}
.list-row {
  display: flex;
  gap: 14px;
  align-items: center;
  padding: 12px 14px;
  margin-bottom: 8px;
  background: var(--portal-surface, #fff);
  border: var(--portal-border-width, 1px) solid var(--portal-line, #dfe7ec);
  border-radius: var(--portal-radius, 10px);
}
.list-row .line { margin-bottom: 8px; }
.list-row .line:last-child { margin-bottom: 0; }
@keyframes shimmer {
  0% { background-position: 100% 0; }
  100% { background-position: -100% 0; }
}
@media (max-width: 640px) {
  .row { grid-template-columns: 1fr; }
  .cover { width: 100%; height: 160px; }
}
</style>
