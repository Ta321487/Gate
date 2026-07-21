<template>
  <div
    v-if="safe"
    class="rtv"
    :class="{ compact }"
    v-html="safe"
  />
  <div v-else-if="fallback" class="rtv plain">{{ fallback }}</div>
</template>

<script setup>
import { computed } from 'vue'
import { looksLikeHtml, sanitizeHtml } from '../utils/richHtml.js'

const props = defineProps({
  html: { type: String, default: '' },
  compact: { type: Boolean, default: false },
})

const safe = computed(() => {
  const raw = props.html || ''
  if (!raw.trim()) return ''
  if (!looksLikeHtml(raw)) return ''
  return sanitizeHtml(raw)
})

const fallback = computed(() => {
  const raw = (props.html || '').trim()
  if (!raw || looksLikeHtml(raw)) return ''
  return raw
})
</script>

<style scoped>
.rtv {
  color: #334155;
  font-size: 14px;
  line-height: 1.65;
  word-break: break-word;
}
.rtv.compact {
  font-size: 13px;
  line-height: 1.5;
  max-height: 4.5em;
  overflow: hidden;
}
.rtv.plain {
  white-space: pre-wrap;
}
.rtv :deep(p) { margin: 0 0 0.6em; }
.rtv :deep(p:last-child) { margin-bottom: 0; }
.rtv :deep(ul),
.rtv :deep(ol) { margin: 0.4em 0 0.6em; padding-left: 1.4em; }
.rtv :deep(a) { color: var(--portal-brand, #2563eb); }
.rtv :deep(img) { max-width: 100%; height: auto; border-radius: var(--portal-radius-sm, 6px); }
.rtv :deep(blockquote) {
  margin: 0.5em 0;
  padding: 0.2em 0.8em;
  border-left: 3px solid #cbd5e1;
  color: #64748b;
}
</style>
