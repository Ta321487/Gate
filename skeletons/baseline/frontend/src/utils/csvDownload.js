/**
 * Excel 友好的 CSV 下载（防中文乱码）。
 * - UTF-8 BOM（0xEF,0xBB,0xBF）用字节写入，避免字符串 BOM 被二次编码
 * - 行尾 CRLF（Windows Excel）
 * - RFC4180 引号转义；防公式注入
 */

function csvEscape(v) {
  let s = v == null ? '' : String(v)
  s = s.replace(/\r\n/g, '\n').replace(/\r/g, '\n')
  // Excel 公式注入：单元格以 = + - @ 开头时加前缀 '
  if (/^[=+\-@]/.test(s)) s = `'${s}`
  if (/[",\n]/.test(s)) return `"${s.replace(/"/g, '""')}"`
  return s
}

/**
 * @param {string} filename 建议 .csv 结尾
 * @param {string[]} headers
 * @param {Array<Array<string|number|null|undefined>>} rows
 */
export function downloadCsv(filename, headers, rows) {
  const lines = [headers.map(csvEscape).join(',')]
  for (const row of rows || []) {
    lines.push((row || []).map(csvEscape).join(','))
  }
  const body = lines.join('\r\n')
  const bom = new Uint8Array([0xef, 0xbb, 0xbf])
  const encoded = new TextEncoder().encode(body)
  const blob = new Blob([bom, encoded], { type: 'text/csv;charset=utf-8;' })
  const a = document.createElement('a')
  const url = URL.createObjectURL(blob)
  a.href = url
  a.download = filename.endsWith('.csv') ? filename : `${filename}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

/** 解析本地 CSV 文本（去 BOM），返回行字符串数组（含表头）。 */
export function stripBom(text) {
  if (!text) return ''
  return String(text).replace(/^\uFEFF/, '')
}

export { csvEscape }
