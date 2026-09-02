<template>
  <n-modal
    :show="show"
    preset="card"
    title="答辩 PPT 检查"
    style="width: min(520px, 94vw)"
    @update:show="(v) => emit('update:show', v)"
  >
    <ul v-if="result?.items?.length" class="ppt-check-list">
      <li
        v-for="(it, i) in result.items"
        :key="i"
        :class="it.level === 'error' ? 'err' : it.level === 'warning' ? 'warn' : 'ok'"
      >
        <strong>{{ levelMark(it.level) }}</strong>
        {{ it.message }}
        <span v-if="it.code" class="small muted"> · {{ it.code }}</span>
      </li>
    </ul>
    <p v-else class="small muted">暂无检查结果</p>
    <p class="small muted" style="margin-top:12px">
      导出条件：无 error · bake 门禁仍过 · 业务指纹未脏。PPTX 单独下载，不进学生 ZIP。
    </p>
    <template #footer>
      <div class="row" style="justify-content:flex-end;gap:8px">
        <n-button @click="emit('update:show', false)">回改</n-button>
        <n-button
          type="primary"
          :disabled="!canExport"
          :loading="exporting"
          @click="emit('export')"
        >
          导出 PPTX
        </n-button>
      </div>
    </template>
  </n-modal>
</template>

<script setup>
defineProps({
  show: { type: Boolean, default: false },
  result: { type: Object, default: null },
  canExport: { type: Boolean, default: false },
  exporting: { type: Boolean, default: false },
})
const emit = defineEmits(['update:show', 'export'])

function levelMark(level) {
  if (level === 'error') return '✕'
  if (level === 'warning') return '⚠'
  return '✓'
}
</script>
