import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd())
  return {
    plugins: [vue()],
    resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
    server: {
      // Dev proxy: the browser calls /api on the Vite server, Vite forwards to the backend (no CORS).
      proxy: {
        '/api': { target: env.VITE_BACKEND_URL || 'http://localhost:8000', changeOrigin: true }
      }
    }
  }
})
