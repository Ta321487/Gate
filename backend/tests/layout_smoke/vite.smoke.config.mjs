/**
 * D3/D4 冒烟：基线 frontend + script-setup-src 垫片 + APP_DELIVERED 皮覆盖 Proxy。
 * 不改 skeletons 业务页；仅工厂测夹具配置。
 */
import path from 'node:path'
import { createRequire } from 'node:module'
import { fileURLToPath } from 'node:url'
import { vueScriptSetupSrc } from './vue-script-setup-src.mjs'
import { layoutSmokeDeliveredProxy } from './delivered-proxy.mjs'

const here = path.dirname(fileURLToPath(import.meta.url))
// backend/tests/layout_smoke → 仓库根
const baselineFe = path.resolve(here, '../../../skeletons/baseline/frontend')
const require = createRequire(path.join(baselineFe, 'package.json'))
const { defineConfig } = require('vite')
const vue = require('@vitejs/plugin-vue')

export default defineConfig({
  root: baselineFe,
  cacheDir: path.join(baselineFe, '.vite-layout-smoke'),
  plugins: [layoutSmokeDeliveredProxy(), vueScriptSetupSrc(), vue()],
  server: {
    host: '127.0.0.1',
    strictPort: true,
    hmr: { overlay: false },
  },
})
