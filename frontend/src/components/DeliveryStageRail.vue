<template>
  <nav v-if="stages.length" class="stage-rail" aria-label="交付阶段">
    <ol class="stage-rail-list">
      <li
        v-for="(s, idx) in stages"
        :key="s.key"
        class="stage-rail-item"
        :class="'is-' + s.state"
      >
        <button
          type="button"
          class="stage-rail-btn"
          :disabled="s.state === 'locked' || !s.tab"
          :title="s.state === 'locked' ? s.lockReason : (s.tab ? `进入${s.label}` : s.label)"
          @click="onClick(s)"
        >
          <span class="stage-rail-idx">{{ idx + 1 }}</span>
          <span class="stage-rail-label">{{ s.label }}</span>
        </button>
        <span v-if="idx < stages.length - 1" class="stage-rail-sep" aria-hidden="true" />
      </li>
    </ol>
    <div class="stage-rail-side">
      <button
        type="button"
        class="stage-rail-tools"
        :class="{ 'is-current': activeTab === 'runtime' }"
        title="启停学生端预览（旁链，非毕设主步）"
        @click="emit('select', 'runtime')"
      >预览</button>
      <button
        type="button"
        class="stage-rail-tools"
        :class="{ 'is-current': activeTab === 'tools' }"
        title="生成与预览日志（旁链，非毕设主步）"
        @click="emit('select', 'tools')"
      >日志</button>
    </div>
    <p v-if="lockHint" class="stage-rail-hint small muted">{{ lockHint }}</p>
  </nav>
</template>

<script setup>
import { computed } from 'vue'
import { buildDeliveryStages } from '../deliveryStages'

const props = defineProps({
  project: { type: Object, default: null },
  activeTab: { type: String, default: '' },
})

const emit = defineEmits(['select'])

const stages = computed(() => buildDeliveryStages(props.project, props.activeTab))

const lockHint = computed(() => {
  const locked = stages.value.find((s) => s.state === 'locked' && s.lockReason)
  const current = stages.value.find((s) => s.state === 'current')
  if (current?.key === 'match' || current?.key === 'generate') {
    return locked?.lockReason || ''
  }
  return ''
})

function onClick(s) {
  if (!s.tab || s.state === 'locked') return
  emit('select', s.tab)
}
</script>

<style scoped>
.stage-rail {
  margin: 2px 0 10px;
  padding: 8px 10px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px 8px;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 4px;
}
.stage-rail-side {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.stage-rail-tools {
  border: 1px solid transparent;
  background: transparent;
  border-radius: 999px;
  padding: 5px 12px;
  font: inherit;
  font-size: 12px;
  color: var(--muted);
  cursor: pointer;
  transition: color 0.12s ease, border-color 0.12s ease, background 0.12s ease;
}
.stage-rail-tools:hover {
  color: var(--ink-2);
  border-color: var(--line);
  background: var(--surface);
}
.stage-rail-tools.is-current {
  border-color: var(--teal);
  background: var(--teal-soft);
  color: var(--teal-deep);
  font-weight: 600;
}
.stage-rail-list {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0;
  list-style: none;
  margin: 0;
  padding: 0;
}
.stage-rail-item {
  display: inline-flex;
  align-items: center;
}
.stage-rail-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid transparent;
  background: transparent;
  border-radius: 999px;
  padding: 5px 12px 5px 5px;
  font: inherit;
  font-size: 12px;
  color: var(--ink-2);
  cursor: pointer;
  transition: background 0.12s ease, border-color 0.12s ease, color 0.12s ease;
}
.stage-rail-btn:hover:not(:disabled) {
  background: var(--surface);
  border-color: var(--line);
}
.stage-rail-btn:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}
.stage-rail-idx {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  background: var(--line-soft);
  color: var(--ink-2);
}
.is-done .stage-rail-btn {
  border-color: var(--banner-ok-line);
  background: var(--banner-ok-bg);
  color: var(--ink);
}
.is-done .stage-rail-idx {
  background: var(--green-soft);
  color: var(--green);
}
.is-current .stage-rail-btn {
  border-color: var(--teal);
  background: var(--teal-soft);
  color: var(--teal-deep);
  font-weight: 600;
}
.is-current .stage-rail-idx {
  background: var(--teal);
  color: #fff;
}
.is-locked .stage-rail-btn {
  background: var(--surface-2);
}
.stage-rail-sep {
  width: 12px;
  height: 2px;
  margin: 0 2px;
  border-radius: 1px;
  background: color-mix(in srgb, var(--line) 80%, transparent);
}
.stage-rail-hint {
  margin: 6px 0 0;
}
</style>
