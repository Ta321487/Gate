<template>
  <button
    type="button"
    class="copy-btn"
    :class="{ ok: copied }"
    :title="copied ? '已复制' : tip"
    :aria-label="copied ? '已复制' : tip"
    :disabled="!text"
    @click.stop="onCopy"
  >
    <!-- check -->
    <svg v-if="copied" viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
      <path
        fill="currentColor"
        d="M9.55 17.6 4.9 12.95l1.4-1.4 3.25 3.25 7.15-7.15 1.4 1.4z"
      />
    </svg>
    <!-- copy -->
    <svg v-else viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
      <path
        fill="currentColor"
        d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"
      />
    </svg>
  </button>
</template>

<script setup>
import { onUnmounted, ref } from 'vue'

const props = defineProps({
  text: { type: String, default: '' },
  tip: { type: String, default: '复制' },
})

const copied = ref(false)
let timer = 0

async function writeClipboard(value) {
  try {
    await navigator.clipboard.writeText(value)
    return true
  } catch {
    try {
      const ta = document.createElement('textarea')
      ta.value = value
      ta.setAttribute('readonly', '')
      ta.style.position = 'fixed'
      ta.style.left = '-9999px'
      document.body.appendChild(ta)
      ta.select()
      const ok = document.execCommand('copy')
      document.body.removeChild(ta)
      return ok
    } catch {
      return false
    }
  }
}

async function onCopy() {
  const value = String(props.text || '')
  if (!value) return
  const ok = await writeClipboard(value)
  if (!ok) return
  copied.value = true
  window.clearTimeout(timer)
  timer = window.setTimeout(() => {
    copied.value = false
  }, 1400)
}

onUnmounted(() => window.clearTimeout(timer))
</script>

<style scoped>
.copy-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  padding: 0;
  margin: 0;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #94a3b8;
  cursor: pointer;
  vertical-align: middle;
  flex-shrink: 0;
  transition: color 0.15s ease, background 0.15s ease;
}
.copy-btn:hover:not(:disabled) {
  color: #334155;
  background: #f1f5f9;
}
.copy-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}
.copy-btn.ok {
  color: #16a34a;
  background: #f0fdf4;
}
</style>
