import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 与后端 GF_HOST 对齐：服务器部署设 GF_HOST=0.0.0.0（或单独 VITE_HOST）
const host = process.env.VITE_HOST || process.env.GF_HOST || '127.0.0.1'
const apiProxy = process.env.VITE_API_PROXY || 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [vue()],
  server: {
    host,
    // 避开学生包默认 Vite :5173，工厂控制台固定 :5300
    port: 5300,
    proxy: {
      '/api': { target: apiProxy, changeOrigin: true },
      '/docs': { target: apiProxy, changeOrigin: true },
      '/redoc': { target: apiProxy, changeOrigin: true },
      '/openapi.json': { target: apiProxy, changeOrigin: true },
    },
  },
})
