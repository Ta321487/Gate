/** 汉字与数字/字母之间不留空格（表 3.1→表3.1，使用 Vue →使用Vue）。 */
export function squeezeCjkAlnumSpaces(text) {
  return String(text || '')
    .replace(/([\u4e00-\u9fff])[ \t]+(?=[A-Za-z0-9])/g, '$1')
    .replace(/([A-Za-z0-9.])[ \t]+(?=[\u4e00-\u9fff])/g, '$1')
}

/** 可贴论文材料：纯文本 / HTML 一律贴边后再进剪贴板（标签名无汉字，整串处理安全）。 */
export async function writeMaterialClipboard({ html = '', text = '' } = {}) {
  const plain = squeezeCjkAlnumSpaces(text)
  const rich = squeezeCjkAlnumSpaces(html)
  if (!plain && !rich) throw new Error('empty')
  if (rich && navigator.clipboard?.write && typeof ClipboardItem !== 'undefined') {
    await navigator.clipboard.write([
      new ClipboardItem({
        'text/html': new Blob([rich], { type: 'text/html' }),
        'text/plain': new Blob([plain || rich], { type: 'text/plain' }),
      }),
    ])
    return
  }
  await navigator.clipboard.writeText(plain || rich)
}

export async function copyMaterialText(text) {
  const plain = squeezeCjkAlnumSpaces(text)
  if (!plain) throw new Error('empty')
  await navigator.clipboard.writeText(plain)
}
