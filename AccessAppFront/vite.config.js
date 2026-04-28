import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// HTTPS enablement note:
// Set VITE_API_PROXY_TARGET to an `https://...` backend origin after TLS is configured.
const proxyTarget = process.env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:5000'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: proxyTarget,
        changeOrigin: true
      }
    }
  }
})
