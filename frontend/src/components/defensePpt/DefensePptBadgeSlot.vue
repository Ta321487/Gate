<template>
  <div>
    <label class="field-label">校徽 <span class="req">*</span></label>
    <div
      class="ppt-badge-slot"
      :class="{ 'is-focus': focused }"
      tabindex="0"
      role="button"
      aria-label="粘贴或选择校徽"
      @focus="focused = true"
      @blur="focused = false"
      @paste="onPaste"
      @click="onSlotClick"
    >
      <div v-if="modelValue" class="ppt-badge-preview">
        <img :src="modelValue" alt="校徽预览" />
      </div>
      <div v-else class="ppt-badge-empty">
        <div class="ppt-badge-empty-title">在此粘贴校徽</div>
        <div class="small muted">从 Word 选中复制后按 Ctrl+V；默认保持原样</div>
      </div>
    </div>
    <div class="row mt-8" style="align-items:center;flex-wrap:wrap;gap:8px">
      <label style="margin:0;cursor:pointer">
        <n-button size="small" secondary tag="span">选择图片</n-button>
        <input type="file" accept="image/*" hidden @change="onFile" />
      </label>
      <n-button v-if="modelValue" size="small" secondary :loading="busy === 'knock'" @click="knock">去掉白底</n-button>
      <n-button
        v-if="modelValue && originalUrl && modelValue !== originalUrl"
        size="small"
        quaternary
        @click="restore"
      >
        恢复原图
      </n-button>
      <n-button v-if="modelValue" size="small" quaternary @click="clear">清除</n-button>
      <span class="small muted">{{ hint }}</span>
    </div>
    <p class="small muted" style="margin:6px 0 0">
      从 Word 复制校徽后在此粘贴。默认保持原样；需要时再点「去掉白底」。徽和字在一起时可能去不干净，不对就恢复或重贴。
    </p>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { knockNearWhiteToAlpha, readBlobAsDataUrl } from '../../ppt/badgeKnockout.js'
import { message } from '../../api.js'

const props = defineProps({
  modelValue: { type: String, default: null },
})
const emit = defineEmits(['update:modelValue'])

const focused = ref(false)
const originalUrl = ref('')
const hint = ref('未放入')
const busy = ref('')

watch(
  () => props.modelValue,
  (v) => {
    if (v && !originalUrl.value) originalUrl.value = v
    if (!v) {
      originalUrl.value = ''
      hint.value = '未放入'
    }
  },
)

function setUrl(url, note, { asOriginal = true } = {}) {
  if (asOriginal) originalUrl.value = url
  emit('update:modelValue', url)
  hint.value = note || '已放入 · 原样'
}

async function ingestBlob(blob, sourceLabel) {
  const raw = await readBlobAsDataUrl(blob)
  setUrl(raw, `${sourceLabel || '已放入'} · 原样（可再去掉白底）`, { asOriginal: true })
  message.success('校徽已放入 · 默认原样，需要再点「去掉白底」')
}

function onPaste(e) {
  const items = [...(e.clipboardData?.items || [])]
  const imgItem = items.find((it) => it.type && it.type.startsWith('image/'))
  if (!imgItem) return
  e.preventDefault()
  const blob = imgItem.getAsFile()
  if (blob) ingestBlob(blob, '已粘贴')
}

function onFile(e) {
  const file = e.target?.files?.[0]
  if (!file) return
  ingestBlob(file, '已选择')
  e.target.value = ''
}

function onSlotClick() {
  /* 仅聚焦以便粘贴 */
}

async function knock() {
  if (!props.modelValue) return
  busy.value = 'knock'
  try {
    const { url, changed } = await knockNearWhiteToAlpha(originalUrl.value || props.modelValue)
    setUrl(url, changed ? '已去掉近白底（预览为准）' : '无明显白底可去', { asOriginal: false })
  } finally {
    busy.value = ''
  }
}

function restore() {
  if (!originalUrl.value) return
  setUrl(originalUrl.value, '已恢复原图', { asOriginal: true })
}

function clear() {
  originalUrl.value = ''
  emit('update:modelValue', null)
  hint.value = '未放入'
}
</script>

<style scoped>
.field-label {
  display: block;
  font-size: 13px;
  margin-bottom: 6px;
  color: var(--ink-2);
}
</style>
