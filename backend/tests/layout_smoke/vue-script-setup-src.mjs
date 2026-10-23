/**
 * 工厂冒烟专用：把 `<script setup src="./X.setup.js">` 内联成合法 `<script setup>`。
 * 真源拆分页范式见 docs/vue-split-batch.md；Vue 官方禁止 setup+src，Vite 需此垫片才能起基线。
 */
import fs from 'node:fs'
import path from 'node:path'

const SETUP_SRC_RE =
  /<script\s+setup\s+src=(["'])([^"']+)\1\s*>\s*<\/script>/i

export function vueScriptSetupSrc() {
  return {
    name: 'layout-smoke-vue-script-setup-src',
    enforce: 'pre',
    transform(code, id) {
      if (!id.includes('.vue')) return null
      const m = code.match(SETUP_SRC_RE)
      if (!m) return null
      const abs = path.resolve(path.dirname(id.split('?')[0]), m[2])
      if (!fs.existsSync(abs)) {
        this.error(`script setup src 找不到: ${abs}`)
        return null
      }
      const body = fs.readFileSync(abs, 'utf8')
      const next = code.replace(m[0], `<script setup>\n${body}\n</script>`)
      return { code: next, map: null }
    },
  }
}
