import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.dirname(fileURLToPath(import.meta.url))
const proxyTarget = process.env.VITE_API_PROXY || 'http://127.0.0.1:8080'

export default defineConfig({
  // 独立缓存，避免共享 node_modules 联接下 Windows 抢锁 EBUSY
  cacheDir: path.join(root, '.vite'),
  plugins: [vue()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    // 端口被占时直接失败（Vite 默认静默 +1，会让 DB 记录端口与真实监听漂移，停止/清理漏杀）
    strictPort: true,
    proxy: {
      '/api': { target: proxyTarget, changeOrigin: true },
      '/uploads': { target: proxyTarget, changeOrigin: true },
    },
  },
})
