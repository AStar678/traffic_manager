import { ref, nextTick, onBeforeUnmount } from 'vue'

/**
 * 浏览器摄像头接入
 *
 * 调用方式：
 *   const { videoEl, isActive, startCamera, stopCamera } = useCamera()
 *   onMounted(() => startCamera())
 *
 * 关键：必须先设 isActive=true 让 <video> 渲染到 DOM，
 * 再用 nextTick 等 Vue 把 ref 绑好，最后才设 srcObject。
 */
export function useCamera() {
  const videoEl = ref(null)        // template ref="videoEl" 绑定
  const stream = ref(null)
  const isActive = ref(false)
  const errorMsg = ref('')
  const loading = ref(false)

  async function startCamera(opts = {}) {
    if (stream.value) return stream.value

    loading.value = true
    errorMsg.value = ''

    // 1. 先让 video 元素进入 DOM（否则 ref 为 null 绑不上）
    isActive.value = true
    await nextTick()

    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: opts.width || 1280 },
          height: { ideal: opts.height || 720 },
          facingMode: opts.facingMode || 'user',
        },
        audio: false,
      })

      stream.value = mediaStream

      // 2. 等 Vue 完成 DOM 更新，ref 绑定到位
      await nextTick()

      if (videoEl.value) {
        videoEl.value.srcObject = mediaStream
        try { await videoEl.value.play() } catch (_) { /* 浏览器可能拦截自动播放 */ }
      }

      loading.value = false
      return mediaStream
    } catch (err) {
      loading.value = false
      isActive.value = false  // 回退，显示降级UI
      errorMsg.value = err.message || '无法访问摄像头'
      console.warn('[Camera] 启动失败:', err.name, err.message)

      if (err.name === 'NotAllowedError') {
        errorMsg.value = '摄像头权限被拒绝，请在浏览器设置中允许访问摄像头'
      } else if (err.name === 'NotFoundError') {
        errorMsg.value = '未检测到摄像头设备'
      }

      // 降级重试：不指定任何约束
      try {
        const fb = await navigator.mediaDevices.getUserMedia({ video: true, audio: false })
        stream.value = fb
        isActive.value = true
        await nextTick()
        if (videoEl.value) {
          videoEl.value.srcObject = fb
          try { await videoEl.value.play() } catch (_) {}
        }
        errorMsg.value = ''
        return fb
      } catch (_) {
        isActive.value = false
      }
      return null
    }
  }

  function stopCamera() {
    if (stream.value) {
      stream.value.getTracks().forEach(t => t.stop())
      stream.value = null
    }
    if (videoEl.value) {
      videoEl.value.srcObject = null
    }
    isActive.value = false
  }

  async function switchCamera() {
    const facing = stream.value?.getVideoTracks()?.[0]?.getSettings()?.facingMode
    stopCamera()
    return startCamera({ facingMode: facing === 'user' ? 'environment' : 'user' })
  }

  function captureFrame() {
    if (!videoEl.value || !isActive.value) return null
    const v = videoEl.value
    const c = document.createElement('canvas')
    c.width = v.videoWidth || 1280
    c.height = v.videoHeight || 720
    c.getContext('2d').drawImage(v, 0, 0, c.width, c.height)
    return c.toDataURL('image/jpeg', 0.85)
  }

  onBeforeUnmount(() => stopCamera())

  return { videoEl, stream, isActive, errorMsg, loading, startCamera, stopCamera, switchCamera, captureFrame }
}
