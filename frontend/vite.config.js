import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

const backendTarget = process.env.VITE_BACKEND_URL || 'http://localhost:8080'
const algorithmTarget = process.env.VITE_ALGORITHM_URL || 'http://localhost:8000'

const ownerGestureApiProxy = {
  target: algorithmTarget,
  ws: true
}

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api/health': ownerGestureApiProxy,
      '/api/state': ownerGestureApiProxy,
      '/api/config': ownerGestureApiProxy,
      '/api/prototypes': ownerGestureApiProxy,
      '/api/recordings': ownerGestureApiProxy,
      '/api/recognize': ownerGestureApiProxy,
      '/api/recognition/stream': ownerGestureApiProxy,
      '/api': backendTarget,
      '/owner-gesture-stream': {
        target: algorithmTarget,
        ws: true,
        rewrite: () => '/api/v1/owner-gestures/recognition/stream'
      },
      '/ws': {
        target: backendTarget,
        ws: true
      }
    }
  }
})
