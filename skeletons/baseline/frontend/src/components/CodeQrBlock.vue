<template>
  <div v-if="code" class="code-qr">
    <el-button size="small" type="primary" plain @click="open">{{ showVerb }}</el-button>
    <el-dialog
      v-model="visible"
      :title="label"
      width="360px"
      align-center
      destroy-on-close
      class="code-qr-dialog"
    >
      <div class="sheet" ref="sheetRef">
        <p class="label">{{ label }}</p>
        <p class="code-text">{{ code }}</p>
        <img v-if="dataUrl" :src="dataUrl" class="qr" :alt="label" />
        <p class="hint">{{ hint }}</p>
      </div>
      <template #footer>
        <el-button @click="visible = false">关闭</el-button>
        <el-button type="primary" @click="doPrint">{{ printVerb }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
/** 通行码/取件码二维码出示（E-07） */
import { computed, ref, watch } from 'vue'
import { getSchema } from '../utils/domainSchema.js'
import { codeToDataUrl } from '../utils/codeQr.js'

const props = defineProps({
  code: { type: String, default: '' },
  label: { type: String, default: '通行码' },
})

const labels = computed(() => getSchema()?.labels || {})
const showVerb = computed(() => labels.value.codeQrShowVerb || '出示二维码')
const printVerb = computed(() => labels.value.codeQrPrintVerb || '打印')
const hint = computed(
  () => labels.value.codeQrHint || '扫码可识别码文；用于出示核对，不对接闸机硬件。',
)

const visible = ref(false)
const dataUrl = ref('')
const sheetRef = ref(null)

async function refresh() {
  dataUrl.value = ''
  if (!props.code) return
  try {
    dataUrl.value = await codeToDataUrl(props.code, { width: 240 })
  } catch {
    dataUrl.value = ''
  }
}

async function open() {
  visible.value = true
  await refresh()
}

watch(
  () => props.code,
  () => {
    if (visible.value) refresh()
  },
)

function doPrint() {
  const node = sheetRef.value
  if (!node) return
  const w = window.open('', '_blank', 'width=420,height=560')
  if (!w) return
  w.document.write(
    `<!doctype html><html><head><title>${props.label}</title>` +
      '<style>body{font-family:sans-serif;text-align:center;padding:24px}' +
      '.code{font-size:20px;font-weight:700;letter-spacing:.06em;margin:8px 0 16px}' +
      'img{width:240px;height:240px} .hint{color:#64748b;font-size:12px;margin-top:12px}</style>' +
      `</head><body>${node.innerHTML}</body></html>`,
  )
  w.document.close()
  w.focus()
  w.print()
}
</script>

<style scoped>
.code-qr { display: inline-block; margin-left: 8px; vertical-align: middle; }
.sheet { text-align: center; }
.label { margin: 0; color: var(--portal-muted, #64748b); font-size: 13px; }
.code-text {
  margin: 8px 0 14px;
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 0.06em;
  word-break: break-all;
}
.qr { width: 240px; height: 240px; image-rendering: pixelated; }
.hint { margin: 12px 0 0; color: var(--portal-muted, #94a3b8); font-size: 12px; line-height: 1.5; }
</style>
