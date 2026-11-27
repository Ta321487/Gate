/**
 * 论文图导出共用：PNG / SVG / Draw.io / Mermaid。
 * 各 *DiagramViewer 只保留取图 DOM / 序列化，交互走这里。
 */
import { message } from '../ui'

export const PNG_SCALE_DEFAULT = 2.5

export function triggerDownload(blob, filename) {
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = filename
  a.click()
  URL.revokeObjectURL(a.href)
}

/** 从内存中的 SVG DOM 栅格化（架构/用例/模块/序列/活动等同构路径）。 */
export async function svgDomToCanvas(svg, { scale = PNG_SCALE_DEFAULT } = {}) {
  if (!svg) throw new Error('无图')
  const clone = svg.cloneNode(true)
  const vb = svg.viewBox?.baseVal
  const w = vb?.width || Number(svg.getAttribute('width')) || 800
  const h = vb?.height || Number(svg.getAttribute('height')) || 600
  clone.setAttribute('width', String(w))
  clone.setAttribute('height', String(h))
  const xml = new XMLSerializer().serializeToString(clone)
  return svgXmlToCanvas(xml, w, h, scale)
}

/** 已有 XML 字符串时栅格化（类图 / ER 等自定义序列化）。 */
export async function svgXmlToCanvas(xml, w, h, scale = PNG_SCALE_DEFAULT) {
  if (!xml) throw new Error('empty svg')
  const url = URL.createObjectURL(new Blob([xml], { type: 'image/svg+xml;charset=utf-8' }))
  try {
    const img = new Image()
    await new Promise((resolve, reject) => {
      img.onload = resolve
      img.onerror = reject
      img.src = url
    })
    const canvas = document.createElement('canvas')
    canvas.width = Math.max(1, Math.round(w * scale))
    canvas.height = Math.max(1, Math.round(h * scale))
    const ctx = canvas.getContext('2d')
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
    return canvas
  } finally {
    URL.revokeObjectURL(url)
  }
}

export function canvasToPngBlob(canvas) {
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (!blob) reject(new Error('png'))
      else resolve(blob)
    }, 'image/png')
  })
}

/** ER 风格：按 CSS 像素绘，再乘 pixelRatio（与 setTransform 路径兼容）。 */
export async function svgXmlToPngBlob(
  xml,
  w,
  h,
  {
    scale = PNG_SCALE_DEFAULT,
    useSetTransform = false,
  } = {},
) {
  if (!xml) throw new Error('empty svg')
  const url = URL.createObjectURL(new Blob([xml], { type: 'image/svg+xml;charset=utf-8' }))
  try {
    const img = new Image()
    await new Promise((resolve, reject) => {
      img.onload = resolve
      img.onerror = () => reject(new Error('svg load failed'))
      img.src = url
    })
    const canvas = document.createElement('canvas')
    canvas.width = Math.max(1, Math.round(w * scale))
    canvas.height = Math.max(1, Math.round(h * scale))
    const ctx = canvas.getContext('2d')
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    if (useSetTransform) {
      ctx.setTransform(scale, 0, 0, scale, 0, 0)
      ctx.drawImage(img, 0, 0, w, h)
    } else {
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
    }
    return await canvasToPngBlob(canvas)
  } finally {
    URL.revokeObjectURL(url)
  }
}

export async function copyPngBlob(
  blob,
  {
    okText = '已复制图片',
    failText = '复制失败，可改下 PNG',
    fallbackFilename = null,
  } = {},
) {
  if (!blob) throw new Error('png')
  if (!navigator.clipboard?.write || typeof ClipboardItem === 'undefined') {
    if (fallbackFilename) {
      triggerDownload(blob, fallbackFilename)
      message.warning('当前环境不支持复制图片，已改为下载 PNG')
      return 'fallback'
    }
    message.error(failText)
    return 'fail'
  }
  try {
    await navigator.clipboard.write([
      new ClipboardItem({ 'image/png': Promise.resolve(blob) }),
    ])
    message.success(okText)
    return 'ok'
  } catch {
    if (fallbackFilename) {
      triggerDownload(blob, fallbackFilename)
      message.warning('复制失败，已改为下载 PNG')
      return 'fallback'
    }
    message.error(failText)
    return 'fail'
  }
}

export async function downloadPngBlob(blob, filename, { failText = '下载 PNG 失败', okText = '' } = {}) {
  try {
    if (!blob) throw new Error('png')
    triggerDownload(blob, filename)
    if (okText) message.success(okText)
  } catch {
    message.error(failText)
  }
}

export function downloadSvgText(raw, filename, { emptyText = '无矢量源' } = {}) {
  if (!raw) {
    message.error(emptyText)
    return false
  }
  triggerDownload(new Blob([raw], { type: 'image/svg+xml;charset=utf-8' }), filename)
  return true
}

function withCacheBust(url) {
  if (!url) return url
  return `${url}${url.includes('?') ? '&' : '?'}t=${Date.now()}`
}

export async function fetchUrlText(url, { cacheBust = true, credentials } = {}) {
  if (!url) throw new Error('no url')
  const opts = {}
  if (credentials) opts.credentials = credentials
  const res = await fetch(cacheBust ? withCacheBust(url) : url, opts)
  if (!res.ok) throw new Error('fetch')
  return await res.text()
}

export async function downloadDrawioUrl(
  url,
  filename,
  { failText = '下载 Draw.io 失败', emptyText = '无 Draw.io 下载地址' } = {},
) {
  if (!url) {
    message.error(emptyText)
    return false
  }
  try {
    const text = await fetchUrlText(url)
    triggerDownload(new Blob([text], { type: 'application/xml;charset=utf-8' }), filename)
    return true
  } catch {
    message.error(failText)
    return false
  }
}

export async function copyMermaidUrl(
  url,
  {
    okText = '已复制 Mermaid（可贴 diagrams.net）',
    failText = '复制 Mermaid 失败',
    credentials,
  } = {},
) {
  try {
    const text = await fetchUrlText(url, { credentials })
    await navigator.clipboard.writeText(text)
    message.success(okText)
    return true
  } catch {
    message.error(failText)
    return false
  }
}

export async function downloadMermaidUrl(
  url,
  filename,
  { failText = '下载 Mermaid 失败', credentials } = {},
) {
  try {
    const text = await fetchUrlText(url, { credentials })
    triggerDownload(new Blob([text], { type: 'text/plain;charset=utf-8' }), filename)
    return true
  } catch {
    message.error(failText)
    return false
  }
}

/** 简单 Viewer：从 getSvg() 一键复制/下载 PNG。 */
export async function copyPngFromSvgDom(getSvg, {
  scale = PNG_SCALE_DEFAULT,
  okText = '已复制图片',
  failText = '复制失败，可改下 PNG',
  fallbackFilename = null,
} = {}) {
  try {
    const canvas = await svgDomToCanvas(getSvg(), { scale })
    const blob = await canvasToPngBlob(canvas)
    return await copyPngBlob(blob, { okText, failText, fallbackFilename })
  } catch {
    message.error(failText)
    return 'fail'
  }
}

export async function downloadPngFromSvgDom(getSvg, filename, {
  scale = PNG_SCALE_DEFAULT,
  failText = '下载 PNG 失败',
  okText = '',
} = {}) {
  try {
    const canvas = await svgDomToCanvas(getSvg(), { scale })
    const blob = await canvasToPngBlob(canvas)
    await downloadPngBlob(blob, filename, { failText, okText })
  } catch {
    message.error(failText)
  }
}
