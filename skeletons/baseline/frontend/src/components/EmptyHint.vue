<template>
  <div class="empty-hint" :class="{ 'has-cta': !!ctaLabel || $slots.cta }">
    <div v-if="illustration !== false" class="illu" aria-hidden="true">
      <slot name="illustration">
        <span class="illu-mark">{{ mark }}</span>
      </slot>
    </div>
    <p class="title">{{ title }}</p>
    <p v-if="desc" class="desc">{{ desc }}</p>
    <div v-if="ctaLabel || $slots.cta" class="cta">
      <slot name="cta">
        <el-button v-if="ctaLabel" type="primary" @click="$emit('cta')">{{ ctaLabel }}</el-button>
      </slot>
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, default: '暂无内容' },
  desc: { type: String, default: '' },
  ctaLabel: { type: String, default: '' },
  /** 插画区字母，默认空态用「空」 */
  mark: { type: String, default: '空' },
  /** false 时不渲染插画区（兼容极简空态） */
  illustration: { type: [Boolean, String], default: true },
})
defineEmits(['cta'])
</script>

<style scoped>
.empty-hint {
  padding: 48px 16px;
  text-align: center;
  color: var(--portal-muted, #94a3b8);
}
.illu {
  margin: 0 auto 14px;
  width: 64px;
  height: 64px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background:
    radial-gradient(circle at 30% 28%, color-mix(in srgb, var(--portal-accent, #0b6e75) 18%, transparent), transparent 55%),
    color-mix(in srgb, var(--portal-bg, #f1f5f9) 80%, var(--portal-surface, #fff));
  border: 1px solid var(--portal-line, #e2e8f0);
}
.illu-mark {
  font-family: var(--portal-font-display, inherit);
  font-size: 22px;
  font-weight: 700;
  color: var(--portal-accent, #0b6e75);
  opacity: 0.85;
}
.title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--portal-ink, #334155);
}
.desc {
  margin: 8px auto 0;
  max-width: 28em;
  font-size: 13px;
  line-height: 1.5;
}
.cta { margin-top: 16px; }
</style>
