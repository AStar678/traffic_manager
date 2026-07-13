import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const backendTarget = process.env.VITE_BACKEND_URL || env.VITE_BACKEND_URL || 'http://localhost:8080'
  const webRtcSignalTarget = process.env.VITE_WEBRTC_SIGNAL_URL
    || env.VITE_WEBRTC_SIGNAL_URL
    || 'http://localhost:8003'

  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url))
      }
    },
    server: {
      port: 5173,
      proxy: {
        '/webrtc': {
          target: webRtcSignalTarget,
          rewrite: path => path.replace(/^\/webrtc/, '')
        },
        '/api': backendTarget,
        '/ws': {
          target: backendTarget,
          ws: true
        }
      }
    }
  }
})
