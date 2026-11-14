<template>
  <div v-if="bad" class="banner fail diagram-rubric-banner mb-8">
    <h4>工厂提示 · 论文图规则红</h4>
    <p class="small">
      {{ note || '老师规矩确定性检查未过，禁止当可交导出（打开图仍可看）。修工厂 diagram_rubric / 出包结构，勿只擦本包。' }}
    </p>
    <ul v-if="rows.length" class="small diagram-rubric-findings">
      <li v-for="(f, i) in rows" :key="i">
        <strong>{{ levelZh(f.level) }}</strong>
        <span v-if="f.where" class="muted"> · {{ f.where }}</span>
        · {{ f.msg }}
      </li>
    </ul>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  /** pack_* 返回的 rubric_gate */
  gate: { type: Object, default: null },
})

const bad = computed(() => props.gate && props.gate.ok === false)
const note = computed(() => String(props.gate?.note || '').trim())
const rows = computed(() => {
  const raw = props.gate?.findings
  if (!Array.isArray(raw)) return []
  return raw.filter((f) => f && (f.level === 'error' || f.level === 'warn')).slice(0, 20)
})

function levelZh(level) {
  if (level === 'error') return '错'
  if (level === 'warn') return '警'
  return '提示'
}
</script>

<style scoped>
.diagram-rubric-banner h4 {
  margin: 0 0 6px;
  font-size: 14px;
}
.diagram-rubric-findings {
  margin: 8px 0 0;
  padding-left: 1.2em;
}
.diagram-rubric-findings li {
  margin: 2px 0;
}
</style>
