/** 上传材料收集：普通文件 / 文件夹拖入 / zip·压缩包解压。 */

const ALLOWED_EXT = new Set(['.pdf', '.doc', '.docx', '.txt'])
const ARCHIVE_EXT = new Set(['.zip'])

/** 单次上传材料上限（展开后的 PDF/Word/TXT 份数；与后端一致） */
export const MAX_UPLOAD_MATERIALS = 8

export function materialExt(name) {
  const n = String(name || '')
  const i = n.lastIndexOf('.')
  return i >= 0 ? n.slice(i).toLowerCase() : ''
}

export function isAllowedMaterial(name) {
  return ALLOWED_EXT.has(materialExt(name))
}

export function isArchive(name) {
  return ARCHIVE_EXT.has(materialExt(name))
}

function basename(path) {
  const s = String(path || '').replace(/\\/g, '/')
  const parts = s.split('/').filter(Boolean)
  return parts[parts.length - 1] || s
}

function shouldSkipEntry(path) {
  const p = String(path || '').replace(/\\/g, '/')
  if (!p || p.endsWith('/')) return true
  if (p.includes('__MACOSX/') || p.includes('/.DS_Store') || p.endsWith('.DS_Store')) return true
  const base = basename(p)
  if (base.startsWith('~$')) return true
  return false
}

/**
 * 从 DataTransfer / input 收集材料 File[]（含目录递归、zip 解压）。
 *
 * 计数口径与「直接选文件」相同：一律按展开后的材料份数。
 * 例：8 个 zip、每个里 1 份开题 → 合计 8 份 → 可通过；
 * 1 个 zip 里 9 份 → 拒绝；8 个 zip 各 2 份 → 合计 16 → 拒绝。
 * 超出则 error，不截取。
 *
 * @returns {Promise<{ files: File[], skipped: string[], notes: string[], error: string }>}
 */
export async function collectUploadMaterials(input, { maxFiles = MAX_UPLOAD_MATERIALS } = {}) {
  /** @type {File[]} */
  const raw = []
  const notes = []
  const skipped = []

  if (!input) {
    return { files: [], skipped, notes, error: '' }
  }

  // 优先：拖放条目（可识别文件夹）
  if (input.dataTransfer?.items?.length) {
    const items = [...input.dataTransfer.items]
    for (const item of items) {
      if (item.kind !== 'file') continue
      const entry = item.webkitGetAsEntry?.()
      if (entry) {
        await walkEntry(entry, raw, skipped)
      } else {
        const f = item.getAsFile?.()
        if (f) raw.push(f)
      }
    }
  } else if (input.files?.length) {
    raw.push(...[...input.files])
  } else if (Array.isArray(input)) {
    raw.push(...input.filter(Boolean))
  } else if (typeof input.length === 'number') {
    raw.push(...[...input].filter(Boolean))
  }

  /** @type {File[]} */
  const out = []
  for (const file of raw) {
    const name = file.name || ''
    if (isArchive(name)) {
      try {
        const extracted = await expandZipFile(file)
        if (!extracted.length) {
          skipped.push(`${name}（空压缩包或无可用材料）`)
          continue
        }
        if (extracted.length > maxFiles) {
          return {
            files: [],
            skipped,
            notes: [],
            error: `压缩包「${name}」内有 ${extracted.length} 份材料，超出单次上限 ${maxFiles} 份（按解压后材料计）`,
          }
        }
        notes.push(`已从 ${name} 解出 ${extracted.length} 份材料`)
        out.push(...extracted)
      } catch (e) {
        skipped.push(`${name}（解压失败：${e?.message || e}）`)
      }
      continue
    }
    if (!isAllowedMaterial(name)) {
      skipped.push(name || '(无名文件)')
      continue
    }
    out.push(file)
  }

  // 同名去重（保留先到）
  const seen = new Set()
  const deduped = []
  for (const f of out) {
    const key = (f.name || '').toLowerCase()
    if (!key || seen.has(key)) {
      if (key) skipped.push(`${f.name}（重名跳过）`)
      continue
    }
    seen.add(key)
    deduped.push(f)
  }

  if (deduped.length > maxFiles) {
    return {
      files: [],
      skipped,
      notes: [],
      error: `展开后共 ${deduped.length} 份材料，单次最多 ${maxFiles} 份（按解压后材料计，与直接选文件相同）`,
    }
  }
  return { files: deduped, skipped, notes, error: '' }
}

async function walkEntry(entry, out, skipped, prefix = '') {
  if (!entry) return
  if (entry.isFile) {
    const file = await readFileEntry(entry)
    if (!file) return
    const rel = prefix ? `${prefix}/${file.name}` : file.name
    if (shouldSkipEntry(rel)) {
      skipped.push(rel)
      return
    }
    // 保留原名；若文件夹内重名由上层 dedupe
    out.push(file)
    return
  }
  if (entry.isDirectory) {
    const reader = entry.createReader()
    const children = await readAllDirectoryEntries(reader)
    const dirPrefix = prefix ? `${prefix}/${entry.name}` : entry.name
    for (const child of children) {
      await walkEntry(child, out, skipped, dirPrefix)
    }
  }
}

function readFileEntry(entry) {
  return new Promise((resolve) => {
    entry.file(resolve, () => resolve(null))
  })
}

function readAllDirectoryEntries(reader) {
  return new Promise((resolve, reject) => {
    const all = []
    const pump = () => {
      reader.readEntries((batch) => {
        if (!batch.length) {
          resolve(all)
          return
        }
        all.push(...batch)
        pump()
      }, reject)
    }
    pump()
  })
}

async function expandZipFile(file) {
  const JSZip = (await import('jszip')).default
  const zip = await JSZip.loadAsync(await file.arrayBuffer())
  /** @type {File[]} */
  const out = []
  const names = Object.keys(zip.files)
  for (const path of names) {
    const entry = zip.files[path]
    if (!entry || entry.dir || shouldSkipEntry(path)) continue
    const base = basename(path)
    if (!isAllowedMaterial(base)) continue
    const blob = await entry.async('blob')
    out.push(new File([blob], base, { type: blob.type || guessMime(base) }))
  }
  return out
}

function guessMime(name) {
  const ext = materialExt(name)
  if (ext === '.pdf') return 'application/pdf'
  if (ext === '.txt') return 'text/plain'
  if (ext === '.docx') {
    return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
  }
  if (ext === '.doc') return 'application/msword'
  return 'application/octet-stream'
}
