/** 轻量消毒：去掉脚本/事件处理器，保留常见排版标签。 */

const ALLOWED = new Set([
  'P', 'BR', 'DIV', 'SPAN', 'STRONG', 'B', 'EM', 'I', 'U', 'S', 'A',
  'UL', 'OL', 'LI', 'H1', 'H2', 'H3', 'H4', 'BLOCKQUOTE', 'PRE', 'CODE',
  'IMG', 'HR',
])

export function looksLikeHtml(s) {
  const t = String(s || '').trim()
  return t.startsWith('<') && /<\/?[a-z][\s\S]*>/i.test(t)
}

export function sanitizeHtml(html) {
  const raw = String(html || '')
  if (!raw.trim()) return ''
  if (typeof DOMParser === 'undefined') {
    return raw.replace(/<script[\s\S]*?>[\s\S]*?<\/script>/gi, '')
  }
  const doc = new DOMParser().parseFromString(raw, 'text/html')
  const walk = (node) => {
    const kids = [...node.childNodes]
    for (const child of kids) {
      if (child.nodeType === Node.ELEMENT_NODE) {
        const tag = child.tagName
        if (!ALLOWED.has(tag)) {
          while (child.firstChild) node.insertBefore(child.firstChild, child)
          node.removeChild(child)
          continue
        }
        ;[...child.attributes].forEach((attr) => {
          const name = attr.name.toLowerCase()
          const val = attr.value || ''
          if (name.startsWith('on') || name === 'style') {
            child.removeAttribute(attr.name)
            return
          }
          if (tag === 'A' && name === 'href') {
            if (!/^(https?:|mailto:|\/|#)/i.test(val.trim())) {
              child.removeAttribute(attr.name)
            } else {
              child.setAttribute('target', '_blank')
              child.setAttribute('rel', 'noopener noreferrer')
            }
            return
          }
          if (tag === 'IMG' && name === 'src') {
            if (!/^(https?:|\/|data:image\/)/i.test(val.trim())) {
              child.removeAttribute(attr.name)
            }
            return
          }
          if (!['href', 'src', 'alt', 'title'].includes(name)) {
            child.removeAttribute(attr.name)
          }
        })
        walk(child)
      } else if (child.nodeType === Node.COMMENT_NODE) {
        node.removeChild(child)
      }
    }
  }
  walk(doc.body)
  return doc.body.innerHTML
}

export function plainFromHtml(html) {
  const s = String(html || '')
  if (!looksLikeHtml(s)) return s
  if (typeof DOMParser === 'undefined') {
    return s.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()
  }
  const doc = new DOMParser().parseFromString(s, 'text/html')
  return (doc.body.textContent || '').replace(/\s+/g, ' ').trim()
}
