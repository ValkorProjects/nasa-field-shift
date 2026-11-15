import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

// Which backend the app calls:
//   npm run dev         → .env.development: http://localhost:8000 through the proxy below
//   npm run dev:mock    → .env.mock: sample data, no backend
//   vite build          → .env.production: https://rollcrop-backend.vercel.app (Vercel production = main)
//   Vercel preview      → http://localhost:8000 (the dev branch and pull requests, for development)
// A VITE_API_BASE set in the environment (e.g. Vercel project settings) always wins.
export default defineConfig(({ mode }) => {
  if (process.env.VERCEL_ENV === 'preview' && !process.env.VITE_API_BASE) {
    process.env.VITE_API_BASE = 'http://localhost:8000' // read by Vite's env loading after this config runs
  }
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
