<template>
  <div class="ed">
    <div class="ed-top">
      <slot name="back" />
    </div>

    <div v-if="loading" class="ed-loading">
      <PageSkeleton variant="detail" />
    </div>
    <div v-else-if="!found" class="ed-state">
      <slot name="empty">未找到该记录</slot>
    </div>

    <template v-else>
      <section class="ed-hero">
        <div class="ed-media">
          <slot name="media" />
        </div>
        <div class="ed-main">
          <div v-if="$slots.kicker" class="ed-kicker">
            <slot name="kicker" />
          </div>
          <h1 class="ed-title">
            <slot name="title" />
          </h1>
          <div v-if="$slots.subtitle" class="ed-sub">
            <slot name="subtitle" />
          </div>
          <div v-if="$slots.status" class="ed-status">
            <slot name="status" />
          </div>
          <div v-if="$slots.actions" class="ed-actions">
            <slot name="actions" />
          </div>
        </div>
      </section>

      <section v-if="$slots.meta" class="ed-block">
        <h2 class="ed-h">{{ metaTitle }}</h2>
        <dl class="ed-kv">
          <slot name="meta" />
        </dl>
      </section>

      <section v-if="$slots.body" class="ed-block">
        <h2 class="ed-h">{{ bodyTitle }}</h2>
        <div class="ed-body">
          <slot name="body" />
        </div>
      </section>

      <section v-if="$slots.related" class="ed-block">
        <div class="ed-block-hd">
          <h2 class="ed-h">{{ relatedTitle }}</h2>
          <slot name="relatedExtra" />
        </div>
        <div class="ed-related">
          <slot name="related" />
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
/**
 * 领域通用详情壳：媒体 + 标题/状态/主操作 + 键值信息 + 说明 + 相关列表。
 * 业务文案与字段由各领域页填 slot，不在此写死行业词。
 */
import PageSkeleton from './PageSkeleton.vue'

defineProps({
  loading: { type: Boolean, default: false },
  found: { type: Boolean, default: true },
  metaTitle: { type: String, default: '基本信息' },
  bodyTitle: { type: String, default: '说明' },
  relatedTitle: { type: String, default: '相关' },
})
</script>

<style scoped>
.ed {
  max-width: 880px;
}
.ed-top {
  margin-bottom: 14px;
}
.ed-loading {
  max-width: 880px;
}
.ed-state {
  padding: 64px 16px;
  text-align: center;
  color: var(--portal-muted, #6b7c8a);
  background: var(--portal-surface, #fff);
  border: var(--portal-border-width, 1px) dashed var(--portal-line, #dfe7ec);
  border-radius: var(--portal-radius, 12px);
}
.ed-hero {
  display: grid;
  grid-template-columns: 160px 1fr;
  gap: 28px;
  align-items: start;
  padding: 22px 24px;
  background: var(--portal-surface, #fff);
  border: var(--portal-border-width, 1px) solid var(--portal-line, #dfe7ec);
  border-radius: var(--portal-radius, 12px);
  box-shadow: var(--portal-shadow, none);
}
.ed-media {
  width: 160px;
  min-height: 210px;
}
.ed-media :deep(img),
.ed-media :deep(.ed-cover) {
  width: 160px;
  height: 210px;
  object-fit: cover;
  border-radius: var(--portal-radius-sm, 8px);
  display: block;
}
.ed-media :deep(.ed-cover) {
  display: grid;
  place-items: center;
  background: var(--portal-cover, linear-gradient(160deg, #0b6e75, #08545a));
  color: #fff;
  font-size: 42px;
  font-weight: 700;
  letter-spacing: -0.02em;
}
.ed-kicker {
  margin-bottom: 6px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--portal-accent, #0b6e75);
}
.ed-title {
  margin: 0 0 8px;
  font-size: 26px;
  line-height: 1.25;
  letter-spacing: -0.03em;
  color: var(--portal-ink, #15202b);
}
.ed-sub {
  margin: 0 0 12px;
  color: var(--portal-muted, #6b7c8a);
  font-size: 14px;
  line-height: 1.5;
}
.ed-status {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 18px;
}
.ed-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}
.ed-block {
  margin-top: 18px;
  padding: 18px 22px 20px;
  background: var(--portal-surface, #fff);
  border: var(--portal-border-width, 1px) solid var(--portal-line, #dfe7ec);
  border-radius: var(--portal-radius, 12px);
}
.ed-block-hd {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 4px;
}
.ed-h {
  margin: 0 0 14px;
  font-size: 14px;
  font-weight: 650;
  color: var(--portal-ink, #15202b);
}
.ed-block-hd .ed-h {
  margin-bottom: 0;
}
.ed-kv {
  margin: 0;
  display: grid;
  grid-template-columns: 96px 1fr;
  gap: 10px 16px;
  font-size: 14px;
}
.ed-kv :deep(dt) {
  margin: 0;
  color: var(--portal-muted, #6b7c8a);
}
.ed-kv :deep(dd) {
  margin: 0;
  color: var(--portal-ink, #15202b);
  word-break: break-all;
}
.ed-body {
  color: var(--portal-ink, #15202b);
  font-size: 14px;
  line-height: 1.65;
}
.ed-body :deep(.ed-tip) {
  margin: 0;
  padding: 12px 14px;
  border-radius: var(--portal-radius-sm, 8px);
  background: var(--portal-accent-soft, #d7eef0);
  color: var(--portal-ink, #15202b);
  border-left: 3px solid var(--portal-accent, #0b6e75);
}
.ed-related {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  margin-top: 12px;
}
.ed-related :deep(.ed-rel) {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 10px 12px;
  border: var(--portal-border-width, 1px) solid var(--portal-line, #dfe7ec);
  border-radius: var(--portal-radius-sm, 8px);
  cursor: pointer;
  text-decoration: none;
  color: inherit;
  background: transparent;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.ed-related :deep(.ed-rel:hover) {
  border-color: var(--portal-accent, #0b6e75);
  box-shadow: var(--portal-shadow, none);
}
.ed-related :deep(.ed-rel-cover) {
  width: 40px;
  height: 52px;
  border-radius: var(--portal-radius-sm, 4px);
  flex-shrink: 0;
  object-fit: cover;
  display: grid;
  place-items: center;
  background: var(--portal-cover, linear-gradient(160deg, #0b6e75, #08545a));
  color: #fff;
  font-weight: 700;
  font-size: 14px;
}
.ed-related :deep(.ed-rel-title) {
  margin: 0 0 4px;
  font-size: 14px;
  font-weight: 600;
  color: var(--portal-ink, #15202b);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ed-related :deep(.ed-rel-sub) {
  margin: 0;
  font-size: 12px;
  color: var(--portal-muted, #6b7c8a);
}
@media (max-width: 640px) {
  .ed-hero {
    grid-template-columns: 1fr;
    justify-items: start;
  }
  .ed-related {
    grid-template-columns: 1fr;
  }
  .ed-title {
    font-size: 22px;
  }
}
</style>
