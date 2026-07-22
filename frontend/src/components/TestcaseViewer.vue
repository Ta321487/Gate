<template>
  <div class="tc-viewer" :class="{ 'is-dark': isDark }">
    <div class="tc-toolbar row mb-12">
      <n-radio-group :value="fieldsLocal" size="small" :disabled="loading" @update:value="onFields">
        <n-radio-button :value="5">5字段</n-radio-button>
        <n-radio-button :value="6">6字段</n-radio-button>
        <n-radio-button :value="7">7字段</n-radio-button>
        <n-radio-button :value="8">8字段</n-radio-button>
        <n-radio-button :value="9">9字段</n-radio-button>
      </n-radio-group>
      <n-button size="small" :loading="loading" @click="$emit('reload')">重新加载</n-button>
      <n-button size="small" type="primary" @click="copyTable">复制表格</n-button>
      <n-button size="small" type="primary" secondary @click="copyMarkdown">复制 Markdown</n-button>
      <n-button size="small" quaternary @click="downloadMd">下载 .md</n-button>
    </div>
    <p class="small muted mb-8">
      由交付菜单与角色推导；与系统实现一致，不发明未实现功能。默认 6 字段，可按学校模板切换。
      <span v-if="count">· 共 {{ count }} 条</span>
    </p>
    <div class="tc-frame">
      <table class="tc-table">
        <thead>
          <tr>
            <th v-for="c in columns" :key="c.key">{{ c.title }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(r, i) in rows" :key="r.id || i">
            <td v-for="c in columns" :key="c.key">{{ r[c.key] }}</td>
          </tr>
        </tbody>
      </table>
      <p v-if="!rows.length" class="small muted" style="padding:16px">暂无测试用例</p>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { message } from '../api'
import { isDark } from '../theme'

const props = defineProps({
  columns: { type: Array, default: () => [] },
  rows: { type: Array, default: () => [] },
  markdown: { type: String, default: '' },
  fields: { type: Number, default: 6 },
  count: { type: Number, default: 0 },
  downloadName: { type: String, default: 'testcases' },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['reload', 'update:fields'])

const fieldsLocal = ref(
  props.fields === 5 || props.fields === 7 || props.fields === 8 || props.fields === 9
    ? props.fields
    : 6,
)

watch(
  () => props.fields,
  (v) => {
    const n = Number(v)
    fieldsLocal.value = [5, 6, 7, 8, 9].includes(n) ? n : 6
  },
)

function onFields(v) {
  const n = Number(v)
  const next = [5, 6, 7, 8, 9].includes(n) ? n : 6
  fieldsLocal.value = next
  emit('update:fields', next)
}

const fileBase = computed(
  () => String(props.downloadName || 'testcases').replace(/\.(md|txt)$/i, '') || 'testcases',
)

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function tableTsv() {
  const cols = props.columns || []
  const head = cols.map((c) => c.title).join('\t')
  const body = (props.rows || [])
    .map((r) =>
      cols
        .map((c) => String(r[c.key] ?? '').replace(/\t/g, ' ').replace(/\n/g, ' '))
        .join('\t'),
    )
    .join('\n')
  return `${head}\n${body}`
}

/** Word 粘贴用：纯黑白线框（无灰底/主题色），表头加粗居中 */
function tableHtmlForWord() {
  const cols = props.columns || []
  const border = 'border:1px solid #000;'
  const thStyle =
    `${border}padding:4pt 6pt;vertical-align:middle;text-align:center;` +
    `font-weight:bold;color:#000;background:#fff;white-space:nowrap;`
  const tdStyle =
    `${border}padding:4pt 6pt;vertical-align:top;text-align:left;` +
    `font-weight:normal;color:#000;background:#fff;`
  const th = cols.map((c) => `<th style="${thStyle}">${escapeHtml(c.title)}</th>`).join('')
  const trs = (props.rows || [])
    .map((r) => {
      const tds = cols
        .map((c) => {
          const raw = String(r[c.key] ?? '')
          const html = escapeHtml(raw).replace(/\n/g, '<br>')
          return `<td style="${tdStyle}">${html}</td>`
        })
        .join('')
      return `<tr>${tds}</tr>`
    })
    .join('')
  // Word 更认带完整 html 壳 + 显式黑白样式的表
  return (
    `<html><body>` +
    `<table border="1" cellspacing="0" cellpadding="0" ` +
    `style="border-collapse:collapse;border:1px solid #000;width:100%;` +
    `font-size:12pt;font-family:宋体,SimSun,serif;color:#000;background:#fff">` +
    `<thead><tr>${th}</tr></thead><tbody>${trs}</tbody></table>` +
    `</body></html>`
  )
}

async function copyTable() {
  const html = tableHtmlForWord()
  const tsv = tableTsv()
  try {
    if (navigator.clipboard?.write && typeof ClipboardItem !== 'undefined') {
      await navigator.clipboard.write([
        new ClipboardItem({
          'text/html': new Blob([html], { type: 'text/html' }),
          'text/plain': new Blob([tsv], { type: 'text/plain' }),
        }),
      ])
    } else {
      await navigator.clipboard.writeText(tsv)
    }
    message.success('已复制表格，可粘贴到 Word')
  } catch {
    try {
      await navigator.clipboard.writeText(tsv)
      message.warning('已复制为纯文本，建议在 Word 中粘贴后转表格')
    } catch {
      message.error('复制失败')
    }
  }
}

async function copyMarkdown() {
  try {
    await navigator.clipboard.writeText(props.markdown || '')
    message.success('已复制 Markdown')
  } catch {
    message.error('复制失败')
  }
}

function downloadMd() {
  const blob = new Blob([props.markdown || ''], { type: 'text/markdown;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `${fileBase.value}.md`
  a.click()
  URL.revokeObjectURL(a.href)
}
</script>

<style scoped>
.tc-toolbar {
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.tc-frame {
  max-height: 72vh;
  overflow: auto;
  border: 1px solid var(--line);
  background: var(--surface-2, #fafafa);
}
.tc-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  background: var(--surface, #fff);
  color: var(--ink, #0f172a);
}
.tc-table th,
.tc-table td {
  border: 1px solid var(--line, #cbd5e1);
  padding: 6px 8px;
  vertical-align: top;
  text-align: left;
  color: inherit;
}
.tc-table th {
  background: color-mix(in srgb, var(--ink, #0f172a) 6%, var(--surface, #fff));
  font-weight: 600;
  white-space: nowrap;
}
.tc-table td {
  min-width: 72px;
}
.tc-viewer.is-dark .tc-frame {
  background: #0f161e;
  border-color: #334155;
}
.tc-viewer.is-dark .tc-table {
  background: transparent;
}
.tc-viewer.is-dark .tc-table th {
  background: color-mix(in srgb, #fff 8%, transparent);
}
</style>
