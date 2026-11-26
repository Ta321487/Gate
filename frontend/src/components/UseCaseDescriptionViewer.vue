<template>
  <div class="ucd-viewer" :class="{ 'is-dark': isDark }">
    <div class="ucd-toolbar row mb-12">
      <n-button size="small" :loading="loading" @click="$emit('reload')">重新加载</n-button>
      <n-button size="small" type="primary" :disabled="rubricBad" :title="exportBlockTitle" @click="copyAll">复制全文（可贴 Word）</n-button>
      <n-button size="small" type="primary" secondary :disabled="rubricBad" :title="exportBlockTitle" @click="copyMarkdown">复制 Markdown</n-button>
      <n-button size="small" quaternary :disabled="rubricBad" :title="exportBlockTitle" @click="downloadMd">下载 .md</n-button>
    </div>
    <DiagramRubricBanner :gate="rubricGate" />
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
            （{{ i + 1 }}）{{ c.name }}功能的用例说明，见表{{ c.table_no }}所示。
          </p>
          <p class="ucd-table-title">表{{ c.table_no }} “{{ c.name }}”的用例描述表</p>
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
import DiagramRubricBanner from './DiagramRubricBanner.vue'
import { isDark } from '../theme'
import {
  copyMaterialText,
  squeezeCjkAlnumSpaces,
  writeMaterialClipboard,
} from '../utils/zhCopy'
import {
  escapeHtml,
  kvTableHtml,
  wordCellParagraphs,
  wrapWordHtml,
} from '../utils/thesisTableHtml'

const props = defineProps({
  intro: { type: String, default: '' },
  sourceNote: { type: String, default: '' },
  cases: { type: Array, default: () => [] },
  markdown: { type: String, default: '' },
  count: { type: Number, default: 0 },
  downloadName: { type: String, default: 'usecase-descriptions' },
  loading: { type: Boolean, default: false },
  rubricGate: { type: Object, default: null },
})

const rubricBad = computed(() => props.rubricGate && props.rubricGate.ok === false)
const exportBlockTitle = computed(() =>
  rubricBad.value ? String(props.rubricGate?.note || '论文图规则红，不可导出') : undefined,
)

defineEmits(['reload'])

const fileBase = computed(
  () =>
    String(props.downloadName || 'usecase-descriptions').replace(/\.(md|txt)$/i, '') ||
    'usecase-descriptions',
)

function htmlForWord() {
  const pStyle = 'margin:0 0 8pt;color:#000;font-size:12pt;font-family:宋体,SimSun,serif'
  const parts = []
  if (props.intro) {
    parts.push(`<p style="${pStyle}">${escapeHtml(props.intro)}</p>`)
  }
  for (let i = 0; i < (props.cases || []).length; i++) {
    const c = props.cases[i]
    const flowHtml = wordCellParagraphs(
      (c.flow || []).map((s, si) => `${si + 1}. ${escapeHtml(s)}`),
    )
    parts.push(
      `<p style="${pStyle}">${escapeHtml(
        squeezeCjkAlnumSpaces(
          `（${i + 1}）${c.name}功能的用例说明，见表${c.table_no}所示。`,
        ),
      )}</p>`,
    )
    parts.push(
      `<p style="${pStyle};text-align:center">${escapeHtml(
        squeezeCjkAlnumSpaces(`表${c.table_no} “${c.name}”的用例描述表`),
      )}</p>`,
    )
    parts.push(
      kvTableHtml([
        ['用例名称', escapeHtml(c.name)],
        ['执行者', escapeHtml(c.actor)],
        ['简要说明', escapeHtml(c.summary)],
        ['基本事件流', flowHtml],
      ]),
    )
  }
  return wrapWordHtml(parts.join(''))
}

function plainText() {
  const lines = []
  if (props.intro) lines.push(props.intro, '')
  for (let i = 0; i < (props.cases || []).length; i++) {
    const c = props.cases[i]
    lines.push(
      squeezeCjkAlnumSpaces(
        `（${i + 1}）${c.name}功能的用例说明，见表${c.table_no}所示。`,
      ),
    )
    lines.push(squeezeCjkAlnumSpaces(`表${c.table_no} “${c.name}”的用例描述表`))
    lines.push(`用例名称\t${c.name}`)
    lines.push(`执行者\t${c.actor}`)
    lines.push(`简要说明\t${c.summary}`)
    lines.push(
      `基本事件流\t${(c.flow || []).map((s, si) => `${si + 1}. ${s}`).join('\n')}`,
    )
    lines.push('')
  }
  return lines.join('\n')
}

async function copyAll() {
  try {
    await writeMaterialClipboard({ html: htmlForWord(), text: plainText() })
    message.success('已复制，可粘贴到 Word')
  } catch {
    try {
      await copyMaterialText(plainText())
      message.warning('已复制为纯文本')
    } catch {
      message.error('复制失败')
    }
  }
}

async function copyMarkdown() {
  try {
    await copyMaterialText(props.markdown || '')
    message.success('已复制 Markdown')
  } catch {
    message.error('复制失败')
  }
}

function downloadMd() {
  const blob = new Blob([squeezeCjkAlnumSpaces(props.markdown || '')], {
    type: 'text/markdown;charset=utf-8',
  })
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
/* 预览：校模板三线+轻网格（复制 Word 走 htmlForWord 内联粗/细线） */
.ucd-table {
  width: 100%;
  border-collapse: collapse;
  border: none;
  border-top: 2px solid var(--ink, #0f172a);
  border-bottom: 2px solid var(--ink, #0f172a);
  font-size: 13px;
  background: var(--surface, #fff);
  color: var(--ink, #0f172a);
}
.ucd-table th,
.ucd-table td {
  border: 1px solid var(--ink, #0f172a);
  padding: 8px 10px;
  vertical-align: top;
  color: inherit;
  background: transparent;
}
.ucd-table tr:first-child th,
.ucd-table tr:first-child td {
  border-top-width: 2px;
}
.ucd-table tr:last-child th,
.ucd-table tr:last-child td {
  border-bottom-width: 2px;
}
.ucd-table th {
  width: 96px;
  text-align: center;
  font-weight: 600;
  white-space: nowrap;
  background: transparent;
}
.ucd-flow {
  margin: 0;
  padding-left: 1.25em;
}
.ucd-flow li {
  margin: 2px 0;
}
/* 预览跟测例同一套日夜；复制 Word 仍走 htmlForWord 白底黑字 */
.ucd-viewer.is-dark .ucd-frame {
  background: #0f161e;
  border-color: #334155;
  color: #e8eef2;
}
.ucd-viewer.is-dark .ucd-intro,
.ucd-viewer.is-dark .ucd-cap,
.ucd-viewer.is-dark .ucd-table-title {
  color: inherit;
}
.ucd-viewer.is-dark .ucd-table {
  background: transparent;
  color: inherit;
  border-top-color: #e8eef2;
  border-bottom-color: #e8eef2;
}
.ucd-viewer.is-dark .ucd-table th,
.ucd-viewer.is-dark .ucd-table td {
  border-color: #94a3b8;
  background: transparent;
  color: inherit;
}
</style>
