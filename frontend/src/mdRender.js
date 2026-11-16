/** 轻量 Markdown 渲染（论文材料预览）。html:true 以支持逻辑设计主键/外键下划线标记。 */
import MarkdownIt from 'markdown-it'

const md = new MarkdownIt({
  html: true,
  linkify: false,
  breaks: true,
  typographer: false,
})

export function renderMarkdown(src) {
  const s = String(src || '').trim()
  if (!s) return ''
  return md.render(s)
}
