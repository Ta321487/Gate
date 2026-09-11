<template>
  <span class="status-chip" :class="[`tone-${tone}`, { compact }]">
    <i class="dot" aria-hidden="true" />
    <span v-if="label || $slots.default" class="lab"><slot>{{ label }}</slot></span>
  </span>
</template>

<script setup>
defineProps({
  tone: { type: String, default: 'muted' },
  label: { type: String, default: '' },
  compact: { type: Boolean, default: false },
})
</script>

<style scoped>
.status-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--portal-muted, #64748b);
  vertical-align: middle;
}
.status-chip.compact .lab { display: none; }
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
  background: var(--imm-tone, #94a3b8);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--imm-tone, #94a3b8) 22%, transparent);
}
.lab { line-height: 1.2; }
.tone-pending { --imm-tone: #d97706; }
.tone-progress { --imm-tone: #0284c7; }
.tone-warn { --imm-tone: #ea580c; }
.tone-ok { --imm-tone: #059669; }
.tone-danger { --imm-tone: #dc2626; }
.tone-muted { --imm-tone: #94a3b8; }
</style>
