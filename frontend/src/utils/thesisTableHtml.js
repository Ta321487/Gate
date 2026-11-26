/**
 * 论文材料表 HTML：校模板常见「三线 + 轻网格」。
 * 与 backend thesis_table_html.py 同口径：顶/表头下/底粗线，行间·竖向细线；禁 border="1"。
 */

const THICK = '1.5pt solid #000'
const THIN = '0.5pt solid #000'

export function escapeHtml(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function cellBorderCss({ isHeaderRow = false, isFirstRow = false, isLastRow = false } = {}) {
  const top = isHeaderRow || isFirstRow ? THICK : THIN
  let bottom = THIN
  if (isHeaderRow || isLastRow) bottom = THICK
  return `border-top:${top};border-bottom:${bottom};border-left:${THIN};border-right:${THIN};`
}

export function thStyle({
  isHeaderRow = true,
  isFirstRow = true,
  isLastRow = false,
  align = 'center',
  nowrap = true,
  width = '',
  fontSize = '12pt',
} = {}) {
  let s =
    cellBorderCss({ isHeaderRow, isFirstRow, isLastRow }) +
    `padding:4pt 6pt;vertical-align:middle;text-align:${align};` +
    `font-weight:bold;color:#000;background:#fff;` +
    `font-size:${fontSize};font-family:宋体,SimSun,serif;`
  if (nowrap) s += 'white-space:nowrap;'
  if (width) s += `width:${width};`
  return s
}

export function tdStyle({
  isHeaderRow = false,
  isFirstRow = false,
  isLastRow = false,
  align = 'center',
  fontSize = '12pt',
  vertical = 'middle',
} = {}) {
  return (
    cellBorderCss({ isHeaderRow, isFirstRow, isLastRow }) +
    `padding:4pt 6pt;vertical-align:${vertical};text-align:${align};` +
    `font-weight:normal;color:#000;background:#fff;` +
    `font-size:${fontSize};font-family:宋体,SimSun,serif;`
  )
}

function tableOpen(fontSize = '12pt') {
  return (
    `<table border="0" cellspacing="0" cellpadding="0" ` +
    `style="border-collapse:collapse;border:none;width:100%;` +
    `font-size:${fontSize};font-family:宋体,SimSun,serif;color:#000;background:#fff;margin:0 0 12pt">`
  )
}

/** 格内多行用段落（Word ↵），禁止 <br> 软回车。 */
export function wordCellParagraphs(lines, { fontSize = '12pt' } = {}) {
  const pStyle =
    `margin:0;padding:0;color:#000;font-size:${fontSize};font-family:宋体,SimSun,serif;`
  return (lines || [])
    .map((line) => `<p style="${pStyle}">${line === '' ? '&nbsp;' : line}</p>`)
    .join('')
}

/** 首行表头网格表（测例等）。cells 已是 HTML 片段时传 escape=false。 */
export function gridTableHtml(rows, { tdAlign = 'center', thAlign = 'center', fontSize = '12pt' } = {}) {
  if (!rows?.length) return ''
  const [head, ...body] = rows
  const thCss = thStyle({ fontSize, align: thAlign })
  const th = head.map((c) => `<th style="${thCss}">${c}</th>`).join('')
  const trs = [`<tr>${th}</tr>`]
  body.forEach((r, i) => {
    const last = i === body.length - 1
    const tdCss = tdStyle({ isLastRow: last, align: tdAlign, fontSize, vertical: 'top' })
    const tds = r.map((c) => `<td style="${tdCss}">${c}</td>`).join('')
    trs.push(`<tr>${tds}</tr>`)
  })
  return `${tableOpen(fontSize)}<thead>${trs[0]}</thead><tbody>${trs.slice(1).join('')}</tbody></table>`
}

/** 左右字段表（用例描述）。valueHtml 可为已拼好的 HTML。 */
export function kvTableHtml(pairs, { labelWidth = '88pt', fontSize = '12pt', valueAlign = 'left' } = {}) {
  if (!pairs?.length) return ''
  const trs = pairs.map(([label, valueHtml], i) => {
    const first = i === 0
    const last = i === pairs.length - 1
    const thCss = thStyle({
      isHeaderRow: false,
      isFirstRow: first,
      isLastRow: last,
      align: 'center',
      width: labelWidth,
      fontSize,
    })
    const tdCss = tdStyle({
      isFirstRow: first,
      isLastRow: last,
      align: valueAlign,
      fontSize,
      vertical: 'top',
    })
    return `<tr><th style="${thCss}">${escapeHtml(label)}</th><td style="${tdCss}">${valueHtml}</td></tr>`
  })
  return `${tableOpen(fontSize)}<tbody>${trs.join('')}</tbody></table>`
}

export function wrapWordHtml(inner) {
  return `<html><head><meta charset="utf-8"></head><body style="color:#000;background:#fff;margin:12pt">${inner}</body></html>`
}
