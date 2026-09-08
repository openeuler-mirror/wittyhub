import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  css: {
    preprocessorOptions: {
      scss: {
        api: 'modern-compiler',
        additionalData: `@use "@/styles/mixin/index.scss" as *;\n`
      }
    }
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    port: 5174,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://localhost:8081',
        changeOrigin: true
      },
      // Mirror openEuler-portal: the analytics SDK posts to the shared dsapi
      // collector via a same-origin /api-dsapi prefix, rewritten away here to
      // avoid cross-origin CORS. See tmp/openEuler-portal/app/vite.config.js.
      '/api-dsapi': {
        target: 'https://dsapi.test.osinfra.cn',
        changeOrigin: true,
        rewrite: (url) => url.replace(/^\/api-dsapi/, '')
      }
    }
  }
})
