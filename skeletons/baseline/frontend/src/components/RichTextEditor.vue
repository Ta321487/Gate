<template>
  <div class="rte" :class="{ focused }">
    <div class="bar" role="toolbar">
      <button type="button" title="加粗" @mousedown.prevent="cmd('bold')"><b>B</b></button>
      <button type="button" title="斜体" @mousedown.prevent="cmd('italic')"><i>I</i></button>
      <button type="button" title="下划线" @mousedown.prevent="cmd('underline')"><u>U</u></button>
      <button type="button" title="无序列表" @mousedown.prevent="cmd('insertUnorderedList')">• 列表</button>
      <button type="button" title="有序列表" @mousedown.prevent="cmd('insertOrderedList')">1. 列表</button>
      <button type="button" title="插入链接" @mousedown.prevent="link">链接</button>
      <button type="button" title="清除格式" @mousedown.prevent="cmd('removeFormat')">清除</button>
    </div>
    <div
      ref="ed"
      class="body"
      contenteditable="true"
      :data-placeholder="placeholder"
      @input="onInput"
      @focus="focused = true"
      @blur="onBlur"
    />
  </div>
</template>

<script setup>
import { nextTick, onMounted, ref, watch } from 'vue'
import { sanitizeHtml } from '../utils/richHtml.js'

const props = defineProps({
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: '请输入正文…' },
  minHeight: { type: String, default: '160px' },
})

const emit = defineEmits(['update:modelValue'])
const ed = ref(null)
const focused = ref(false)
let syncing = false

function setHtml(html) {
  if (!ed.value) return
  syncing = true
  ed.value.innerHTML = html || ''
  syncing = false
}

function onInput() {
  if (syncing || !ed.value) return
  emit('update:modelValue', ed.value.innerHTML)
}

function onBlur() {
  focused.value = false
  if (!ed.value) return
  const clean = sanitizeHtml(ed.value.innerHTML)
  if (clean !== ed.value.innerHTML) setHtml(clean)
  emit('update:modelValue', clean)
}

function cmd(name) {
  document.execCommand(name, false, null)
  ed.value?.focus()
  onInput()
}

function link() {
  const url = window.prompt('链接地址（https://…）', 'https://')
  if (!url) return
  document.execCommand('createLink', false, url.trim())
  ed.value?.focus()
  onInput()
}

watch(
  () => props.modelValue,
  (v) => {
    if (!ed.value) return
    if (ed.value.innerHTML === (v || '')) return
    if (ed.value === document.activeElement) return
    setHtml(v || '')
  },
)

onMounted(async () => {
  await nextTick()
  setHtml(props.modelValue || '')
})
</script>

<style scoped>
.rte {
  border: var(--portal-border-width, 1px) solid var(--portal-line, #dcdfe6);
  border-radius: var(--portal-radius-sm, 8px);
  background: var(--portal-surface, #fff);
  overflow: hidden;
}
.rte.focused {
  border-color: var(--portal-accent, var(--el-color-primary, #409eff));
}
.bar {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  padding: 6px 8px;
  border-bottom: var(--portal-border-width, 1px) solid var(--portal-line, #ebeef5);
  background: color-mix(in srgb, var(--portal-bg, #f8fafc) 80%, #fff);
}
.bar button {
  border: 0;
  background: transparent;
  padding: 4px 8px;
  border-radius: var(--portal-radius-sm, 4px);
  font-size: 12px;
  color: #475569;
  cursor: pointer;
}
.bar button:hover {
  background: var(--portal-accent-soft, #e2e8f0);
  color: #0f172a;
}
.body {
  min-height: v-bind(minHeight);
  padding: 10px 12px;
  outline: none;
  font-size: 14px;
  line-height: 1.6;
  color: #1e293b;
}
.body:empty::before {
  content: attr(data-placeholder);
  color: #94a3b8;
  pointer-events: none;
}
</style>
