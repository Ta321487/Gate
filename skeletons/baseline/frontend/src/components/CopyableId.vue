<template>
  <span class="copyable-id">
    <span class="copyable-id__text">{{ display }}</span>
    <el-button
      v-if="text != null && String(text) !== ''"
      link
      type="primary"
      class="copyable-id__btn"
      @click.stop="onCopy"
    >复制</el-button>
  </span>
</template>

<script setup>
import { computed } from 'vue'
import { copyText } from '../utils/copyText.js'

const props = defineProps({
  value: { type: [String, Number], default: '' },
  prefix: { type: String, default: '' },
})

const text = computed(() => {
  const v = props.value
  if (v == null || v === '') return ''
  return `${props.prefix || ''}${v}`
})
const display = computed(() => (text.value ? String(props.value) : '—'))

function onCopy() {
  copyText(text.value)
}
</script>

<style scoped>
.copyable-id {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
}
.copyable-id__btn {
  padding: 0 2px;
  font-size: 12px;
}
</style>
