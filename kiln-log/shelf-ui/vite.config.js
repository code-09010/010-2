import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    // 本地开发时把接口转给本机的 fire-api
    proxy: { '/api': 'http://localhost:8000' },
  },
})
