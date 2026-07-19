import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 与后端 GF_HOST 对齐：服务器部署设 GF_HOST=0.0.0.0（或单独 VITE_HOST）
const host = process.env.VITE_HOST || process.env.GF_HOST || '127.0.0.1'
const apiProxy = process.env.VITE_API_PROXY || 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [vue()],
  server: {
    host,
    port: 5173,
    proxy: {
      '/api': { target: apiProxy, changeOrigin: true },
    },
  },
})
