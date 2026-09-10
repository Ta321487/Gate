<template>
  <div class="ucd-viewer" :class="{ 'is-dark': isDark }">
    <div class="ucd-toolbar row mb-12">
      <n-button size="small" :loading="loading" @click="$emit('reload')">重新加载</n-button>
      <n-button size="small" type="primary" @click="copyAll">复制全文（可贴 Word）</n-button>
      <n-button size="small" type="primary" secondary @click="copyMarkdown">复制 Markdown</n-button>
      <n-button size="small" quaternary @click="downloadMd">下载 .md</n-button>
    </div>
    <p class="small muted mb-8">
      {{ sourceNote || '由交付菜单与开题材料推导；事件流对照实包操作，不发明未实现功能。' }}
      <span v-if="count">· 共 {{ count }} 个用例</span>
    </p>
    <div class="ucd-frame">
      <ContentLoading v-if="loading && !cases.length" :rows="4" compact />
      <template v-else>
        <p v-if="intro" class="ucd-intro">{{ intro }}</p>
        <div v-for="(c, i) in cases" :key="c.id || i" class="ucd-case">
          <p class="ucd-cap">
            （{{ i + 1 }}）{{ c.name }}功能的用例说明，见表 {{ c.table_no }} 所示。
          </p>
          <p class="ucd-table-title">表 {{ c.table_no }} “{{ c.name }}”的用例描述表</p>
          <table class="ucd-table">
            <tbody>
              <tr>
                <th>用例名称</th>
                <td>{{ c.name }}</td>
              </tr>
              <tr>
                <th>执行者</th>
                <td>{{ c.actor }}</td>
              </tr>
              <tr>
                <th>简要说明</th>
                <td>{{ c.summary }}</td>
              </tr>
              <tr>
                <th>基本事件流</th>
                <td>
                  <ol class="ucd-flow">
                    <li v-for="(step, si) in c.flow || []" :key="si">{{ step }}</li>
                  </ol>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-if="!cases.length" class="small muted" style="padding:16px">暂无用例描述</p>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { message } from '../api'
import ContentLoading from './ContentLoading.vue'
import { isDark } from '../theme'

const props = defineProps({
  intro: { type: String, default: '' },
  sourceNote: { type: String, default: '' },
  cases: { type: Array, default: () => [] },
  markdown: { type: String, default: '' },
  count: { type: Number, default: 0 },
  downloadName: { type: String, default: 'usecase-descriptions' },
  loading: { type: Boolean, default: false },
})

defineEmits(['reload'])

const fileBase = computed(
  () =>
    String(props.downloadName || 'usecase-descriptions').replace(/\.(md|txt)$/i, '') ||
    'usecase-descriptions',
)

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function htmlForWord() {
  const border = 'border:1px solid #000;'
  const thStyle =
    `${border}padding:4pt 6pt;vertical-align:middle;text-align:center;` +
    `font-weight:bold;color:#000;background:#fff;width:88pt;white-space:nowrap;`
  const tdStyle =
    `${border}padding:4pt 6pt;vertical-align:top;text-align:left;` +
    `font-weight:normal;color:#000;background:#fff;`
  const parts = []
  if (props.intro) {
    parts.push(`<p style="color:#000;font-size:12pt;font-family:宋体,SimSun,serif">${escapeHtml(props.intro)}</p>`)
  }
  for (let i = 0; i < (props.cases || []).length; i++) {
    const c = props.cases[i]
    const flowHtml = (c.flow || [])
      .map((s, si) => `${si + 1}. ${escapeHtml(s)}`)
      .join('<br>')
    parts.push(
      `<p style="color:#000;font-size:12pt;font-family:宋体,SimSun,serif">（${i + 1}）${escapeHtml(c.name)}功能的用例说明，见表 ${escapeHtml(c.table_no)} 所示。</p>`,
    )
    parts.push(
      `<p style="color:#000;font-size:12pt;font-family:宋体,SimSun,serif;text-align:center">表 ${escapeHtml(c.table_no)} “${escapeHtml(c.name)}”的用例描述表</p>`,
    )
    parts.push(
      `<table border="1" cellspacing="0" cellpadding="0" ` +
        `style="border-collapse:collapse;border:1px solid #000;width:100%;` +
        `font-size:12pt;font-family:宋体,SimSun,serif;color:#000;background:#fff;margin-bottom:12pt">` +
        `<tbody>` +
        `<tr><th style="${thStyle}">用例名称</th><td style="${tdStyle}">${escapeHtml(c.name)}</td></tr>` +
        `<tr><th style="${thStyle}">执行者</th><td style="${tdStyle}">${escapeHtml(c.actor)}</td></tr>` +
        `<tr><th style="${thStyle}">简要说明</th><td style="${tdStyle}">${escapeHtml(c.summary)}</td></tr>` +
        `<tr><th style="${thStyle}">基本事件流</th><td style="${tdStyle}">${flowHtml}</td></tr>` +
        `</tbody></table>`,
    )
  }
  return `<html><body>${parts.join('')}</body></html>`
}

function plainText() {
  const lines = []
  if (props.intro) lines.push(props.intro, '')
  for (let i = 0; i < (props.cases || []).length; i++) {
    const c = props.cases[i]
    lines.push(`（${i + 1}）${c.name}功能的用例说明，见表 ${c.table_no} 所示。`)
    lines.push(`表 ${c.table_no} “${c.name}”的用例描述表`)
    lines.push(`用例名称\t${c.name}`)
    lines.push(`执行者\t${c.actor}`)
    lines.push(`简要说明\t${c.summary}`)
    lines.push(`基本事件流\t${(c.flow || []).map((s, si) => `${si + 1}. ${s}`).join(' ')}`)
    lines.push('')
  }
  return lines.join('\n')
}

async function copyAll() {
  const html = htmlForWord()
  const text = plainText()
  try {
    if (navigator.clipboard?.write && typeof ClipboardItem !== 'undefined') {
      await navigator.clipboard.write([
        new ClipboardItem({
          'text/html': new Blob([html], { type: 'text/html' }),
          'text/plain': new Blob([text], { type: 'text/plain' }),
        }),
      ])
    } else {
      await navigator.clipboard.writeText(text)
    }
    message.success('已复制，可粘贴到 Word')
  } catch {
    try {
      await navigator.clipboard.writeText(text)
      message.warning('已复制为纯文本')
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
.ucd-toolbar {
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.ucd-frame {
  max-height: 72vh;
  overflow: auto;
  border: 1px solid var(--line);
  background: var(--surface-2, #fafafa);
  padding: 16px;
}
.ucd-intro {
  margin: 0 0 16px;
  font-size: 14px;
  line-height: 1.6;
}
.ucd-case {
  margin-bottom: 20px;
}
.ucd-cap,
.ucd-table-title {
  margin: 0 0 8px;
  font-size: 13px;
  line-height: 1.5;
}
.ucd-table-title {
  text-align: center;
  font-weight: 600;
}
.ucd-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  background: #fff;
  color: #111;
}
.ucd-table th,
.ucd-table td {
  border: 1px solid #000;
  padding: 8px 10px;
  vertical-align: top;
}
.ucd-table th {
  width: 96px;
  text-align: center;
  font-weight: 700;
  white-space: nowrap;
  background: #fff;
}
.ucd-flow {
  margin: 0;
  padding-left: 1.25em;
}
.ucd-flow li {
  margin: 2px 0;
}
.ucd-viewer.is-dark .ucd-frame {
  background: var(--surface-2);
}
.ucd-viewer.is-dark .ucd-table {
  background: var(--surface);
  color: var(--text);
}
.ucd-viewer.is-dark .ucd-table th,
.ucd-viewer.is-dark .ucd-table td {
  border-color: var(--line);
  background: var(--surface);
  color: var(--text);
}
</style>
