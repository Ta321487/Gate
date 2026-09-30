<template>
  <div v-if="visible.length" class="schema-hints">
    <p v-for="h in visible" :key="h.key" class="page-hint">{{ h.text }}</p>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { schemaLabels } from '../utils/domainSchema.js'

/** 开题密功能 labels.* 可见挂载：有文案才展示，禁止空壳占位。 */
const props = defineProps({
  keys: { type: Array, default: () => [] },
})

const visible = computed(() => {
  const lab = schemaLabels() || {}
  return (props.keys || [])
    .map((key) => ({ key, text: String(lab[key] || '').trim() }))
    .filter((x) => x.text)
})
</script>

<style scoped>
.schema-hints { margin: 0 0 10px; }
.page-hint {
  margin: 0 0 6px;
  color: var(--portal-muted, #64748b);
  font-size: 13px;
  line-height: 1.45;
}
</style>
