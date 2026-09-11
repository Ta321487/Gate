<template>
  <ol class="imm-steps" :aria-label="ariaLabel">
    <li
      v-for="s in steps"
      :key="s.key"
      class="step"
      :class="s.state"
    >
      <i class="node" aria-hidden="true" />
      <span class="lab">{{ s.label }}</span>
    </li>
  </ol>
</template>

<script setup>
defineProps({
  /** { key, label, state: 'done'|'current'|'todo' }[] */
  steps: { type: Array, default: () => [] },
  ariaLabel: { type: String, default: '进度' },
})
</script>

<style scoped>
.imm-steps {
  list-style: none;
  margin: 8px 0 4px;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 0;
  align-items: center;
}
.step {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--portal-muted, #94a3b8);
  position: relative;
  padding-right: 18px;
}
.step:not(:last-child)::after {
  content: '';
  position: absolute;
  right: 6px;
  top: 50%;
  width: 10px;
  height: 1px;
  background: var(--portal-line, #e2e8f0);
}
.node {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--portal-line, #cbd5e1);
  flex-shrink: 0;
}
.step.done { color: var(--portal-ink, #475569); }
.step.done .node { background: #059669; }
.step.current { color: var(--portal-accent, #0b6e75); font-weight: 600; }
.step.current .node {
  background: var(--portal-accent, #0b6e75);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--portal-accent, #0b6e75) 22%, transparent);
}
.step.todo .node { background: #cbd5e1; }
</style>
