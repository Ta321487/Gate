<template>
  <pre
    class="spec-preview code-preview"
    :class="extraClass"
    :style="boxStyle"
    v-html="html"
  />
</template>

<script setup>
import { computed } from 'vue'
import { highlightCode } from '../codeHighlight'

const props = defineProps({
  /** 原始代码文本（复制仍用这一份，勿从 DOM 扒） */
  code: { type: String, default: '' },
  /** sql | json | plain */
  lang: { type: String, default: 'plain' },
  maxHeight: { type: [String, Number], default: '' },
  extraClass: { type: [String, Array, Object], default: '' },
})

const html = computed(() => highlightCode(props.code, props.lang))

const boxStyle = computed(() => {
  if (props.maxHeight === '' || props.maxHeight == null) return undefined
  const h = typeof props.maxHeight === 'number' ? `${props.maxHeight}px` : props.maxHeight
  return { maxHeight: h }
})
</script>
