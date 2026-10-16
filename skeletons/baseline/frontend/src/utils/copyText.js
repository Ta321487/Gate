import { notifyFail, notifyOk } from './notify.js'

/** 复制文本到剪贴板，并给出提示。 */
export async function copyText(text, okMsg = '已复制') {
  const s = String(text ?? '').trim()
  if (!s) {
    notifyFail('没有可复制的内容')
    return false
  }
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(s)
    } else {
      const ta = document.createElement('textarea')
      ta.value = s
      ta.setAttribute('readonly', '')
      ta.style.position = 'fixed'
      ta.style.left = '-9999px'
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
    }
    notifyOk(okMsg)
    return true
  } catch {
    notifyFail('复制失败')
    return false
  }
}
