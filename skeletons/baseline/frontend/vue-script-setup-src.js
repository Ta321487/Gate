/**
 * 学生包 / 基线 Vite：把 `<script setup src="./X.setup.js">` 内联成合法 `<script setup>`。
 * Vue 官方禁止 setup+src（会报 ambiguous）；拆分页范式见 docs/vue-split-batch.md。
 * 须在 @vitejs/plugin-vue 之前注册。
 */
import fs from 'node:fs'
import path from 'node:path'

const SETUP_SRC_RE =
  /<script\s+setup\s+src=(["'])([^"']+)\1\s*>\s*<\/script>/i

export function vueScriptSetupSrc() {
  return {
    name: 'vue-script-setup-src',
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
      // 内联后 Vite 默认只盯 .vue；不 watch setup 则改 .setup.js 不重编、HMR 假绿
      this.addWatchFile(abs)
      const body = fs.readFileSync(abs, 'utf8')
      const next = code.replace(m[0], `<script setup>\n${body}\n</script>`)
      return { code: next, map: null }
    },
  }
}
