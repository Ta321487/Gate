/** 只读代码预览轻量高亮（零依赖）。输出已转义 HTML，可进 v-html。 */

const SQL_KEYWORDS = new Set(
  [
    'ADD',
    'ALTER',
    'AS',
    'ASC',
    'AUTO_INCREMENT',
    'BIGINT',
    'BINARY',
    'BLOB',
    'BOOLEAN',
    'BTREE',
    'CASCADE',
    'CHAR',
    'CHARACTER',
    'CHARSET',
    'COLLATE',
    'COLUMN',
    'COMMENT',
    'CONSTRAINT',
    'CREATE',
    'CURRENT_TIMESTAMP',
    'DATABASE',
    'DATE',
    'DATETIME',
    'DECIMAL',
    'DEFAULT',
    'DELETE',
    'DESC',
    'DOUBLE',
    'DROP',
    'ENGINE',
    'EXISTS',
    'FALSE',
    'FLOAT',
    'FOREIGN',
    'IF',
    'INDEX',
    'INNODB',
    'INT',
    'INTEGER',
    'JSON',
    'KEY',
    'LIKE',
    'LONGBLOB',
    'LONGTEXT',
    'MEDIUMBLOB',
    'MEDIUMINT',
    'MEDIUMTEXT',
    'NOT',
    'NULL',
    'ON',
    'PRIMARY',
    'REFERENCES',
    'RESTRICT',
    'SET',
    'SMALLINT',
    'TABLE',
    'TEXT',
    'TIME',
    'TIMESTAMP',
    'TINYBLOB',
    'TINYINT',
    'TINYTEXT',
    'TRUE',
    'UNIQUE',
    'UNSIGNED',
    'UPDATE',
    'USE',
    'USING',
    'VALUES',
    'VARBINARY',
    'VARCHAR',
    'VIEW',
    'WHERE',
    'WITH',
  ].map((k) => k.toUpperCase()),
)

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

function wrap(cls, raw) {
  return `<span class="tok-${cls}">${escapeHtml(raw)}</span>`
}

/**
 * @param {string} text
 * @param {'sql'|'json'|'plain'} lang
 * @returns {string}
 */
export function highlightCode(text, lang = 'plain') {
  const src = text == null ? '' : String(text)
  if (!src) return ''
  if (lang === 'sql') return highlightSql(src)
  if (lang === 'json') return highlightJson(src)
  return escapeHtml(src)
}

function highlightSql(src) {
  let i = 0
  const n = src.length
  let out = ''
  while (i < n) {
    const ch = src[i]
    // line comment
    if (ch === '-' && src[i + 1] === '-') {
      let j = i + 2
      while (j < n && src[j] !== '\n') j += 1
      out += wrap('cmt', src.slice(i, j))
      i = j
      continue
    }
    // block comment
    if (ch === '/' && src[i + 1] === '*') {
      let j = i + 2
      while (j < n - 1 && !(src[j] === '*' && src[j + 1] === '/')) j += 1
      j = Math.min(n, j + 2)
      out += wrap('cmt', src.slice(i, j))
      i = j
      continue
    }
    // string
    if (ch === "'" || ch === '"') {
      const q = ch
      let j = i + 1
      while (j < n) {
        if (src[j] === '\\') {
          j += 2
          continue
        }
        if (src[j] === q) {
          // SQL doubled quote escape
          if (q === "'" && src[j + 1] === "'") {
            j += 2
            continue
          }
          j += 1
          break
        }
        j += 1
      }
      out += wrap('str', src.slice(i, j))
      i = j
      continue
    }
    // backtick ident
    if (ch === '`') {
      let j = i + 1
      while (j < n && src[j] !== '`') j += 1
      if (j < n) j += 1
      out += wrap('ident', src.slice(i, j))
      i = j
      continue
    }
    // number
    if (/[0-9]/.test(ch) || (ch === '.' && /[0-9]/.test(src[i + 1] || ''))) {
      let j = i + 1
      while (j < n && /[0-9.]/.test(src[j])) j += 1
      out += wrap('num', src.slice(i, j))
      i = j
      continue
    }
    // word
    if (/[A-Za-z_]/.test(ch)) {
      let j = i + 1
      while (j < n && /[A-Za-z0-9_]/.test(src[j])) j += 1
      const word = src.slice(i, j)
      if (SQL_KEYWORDS.has(word.toUpperCase())) out += wrap('kw', word)
      else out += escapeHtml(word)
      i = j
      continue
    }
    out += escapeHtml(ch)
    i += 1
  }
  return out
}

function highlightJson(src) {
  let i = 0
  const n = src.length
  let out = ''
  while (i < n) {
    const ch = src[i]
    if (ch === '"') {
      let j = i + 1
      while (j < n) {
        if (src[j] === '\\') {
          j += 2
          continue
        }
        if (src[j] === '"') {
          j += 1
          break
        }
        j += 1
      }
      const lit = src.slice(i, j)
      // key if next non-space is :
      let k = j
      while (k < n && /\s/.test(src[k])) k += 1
      out += wrap(src[k] === ':' ? 'key' : 'str', lit)
      i = j
      continue
    }
    if (/[0-9-]/.test(ch) && (ch !== '-' || /[0-9]/.test(src[i + 1] || ''))) {
      let j = i + 1
      while (j < n && /[0-9.eE+-]/.test(src[j])) j += 1
      out += wrap('num', src.slice(i, j))
      i = j
      continue
    }
    if (/[A-Za-z]/.test(ch)) {
      let j = i + 1
      while (j < n && /[A-Za-z]/.test(src[j])) j += 1
      const word = src.slice(i, j)
      if (word === 'true' || word === 'false' || word === 'null') out += wrap('kw', word)
      else out += escapeHtml(word)
      i = j
      continue
    }
    out += escapeHtml(ch)
    i += 1
  }
  return out
}
