import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const backendTarget = process.env.VITE_BACKEND_URL || env.VITE_BACKEND_URL || 'http://localhost:8080'
  const gestureAlgorithmTarget = process.env.VITE_GESTURE_ALGORITHM_URL
    || env.VITE_GESTURE_ALGORITHM_URL
    || process.env.VITE_ALGORITHM_URL
    || env.VITE_ALGORITHM_URL
    || 'http://localhost:8002'
  const webRtcSignalTarget = process.env.VITE_WEBRTC_SIGNAL_URL
    || env.VITE_WEBRTC_SIGNAL_URL
    || 'http://localhost:8003'

  const ownerGestureApiProxy = {
    target: gestureAlgorithmTarget,
    ws: true
  }

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
        '/api/health': ownerGestureApiProxy,
        '/api/state': ownerGestureApiProxy,
        '/api/algorithm': ownerGestureApiProxy,
        '/api/config': ownerGestureApiProxy,
        '/api/prototypes': ownerGestureApiProxy,
        '/api/recordings': ownerGestureApiProxy,
        '/api/recognize': ownerGestureApiProxy,
        '/api/recognition/stream': ownerGestureApiProxy,
        '/api': backendTarget,
        '/owner-gesture-stream': {
          target: gestureAlgorithmTarget,
          ws: true,
          rewrite: () => '/api/v1/owner-gestures/recognition/stream'
        },
        '/ws': {
          target: backendTarget,
          ws: true
        }
      }
    }
  }
})
