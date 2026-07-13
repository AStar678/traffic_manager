import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getMusicList, uploadMusic, deleteMusic, getStreamUrl } from '@/api/music'
import { ElMessage } from 'element-plus'

/**
 * 音乐播放器状态管理
 */
export const useMusicStore = defineStore('music', () => {
  // ---- 播放列表 ----
  const tracks = ref([])           // 歌曲列表
  const currentIndex = ref(-1)     // 当前播放索引
  const isPlaying = ref(false)     // 播放状态
  const volume = ref(42)           // 音量 0-100
  const currentTime = ref(0)       // 当前播放进度（秒）
  const duration = ref(0)          // 总时长（秒）
  const loading = ref(false)       // 加载中
  const audioElement = ref(null)   // HTML5 Audio 实例

  // ---- 计算属性 ----
  const currentTrack = computed(() => {
    if (currentIndex.value >= 0 && currentIndex.value < tracks.value.length) {
      return tracks.value[currentIndex.value]
    }
    return null
  })

  const trackCount = computed(() => tracks.value.length)

  const progress = computed(() => {
    if (duration.value > 0) {
      return (currentTime.value / duration.value) * 100
    }
    return 0
  })

  // ---- 方法 ----

  /** 加载音乐列表 */
  async function fetchTracks() {
    loading.value = true
    try {
      const res = await getMusicList()
      tracks.value = res.data || []
    } catch (e) {
      ElMessage.error('加载音乐列表失败')
    } finally {
      loading.value = false
    }
  }

  /** 上传音乐 */
  async function upload(file) {
    try {
      const res = await uploadMusic(file)
      ElMessage.success('上传成功')
      await fetchTracks()
      return res.data
    } catch (e) {
      ElMessage.error('上传失败')
      throw e
    }
  }

  /** 删除歌曲 */
  async function remove(id) {
    try {
      await deleteMusic(id)
      ElMessage.success('已删除')
      // 如果删除的是当前播放的，先停止
      if (currentTrack.value && currentTrack.value.id === id) {
        stop()
      }
      await fetchTracks()
    } catch (e) {
      ElMessage.error('删除失败')
    }
  }

  /** 播放指定索引的歌曲 */
  function play(index) {
    if (index < 0 || index >= tracks.value.length) return

    currentIndex.value = index
    const track = tracks.value[index]

    // 创建或复用 Audio 实例
    if (!audioElement.value) {
      audioElement.value = new Audio()
      audioElement.value.addEventListener('timeupdate', onTimeUpdate)
      audioElement.value.addEventListener('loadedmetadata', onLoaded)
      audioElement.value.addEventListener('ended', onEnded)
      audioElement.value.addEventListener('error', onError)
    }

    const audio = audioElement.value
    audio.src = getStreamUrl(track.id)
    audio.volume = volume.value / 100
    audio.play().then(() => {
      isPlaying.value = true
    }).catch(e => {
      console.warn('播放失败:', e.message)
    })
  }

  /** 播放/暂停切换 */
  function togglePlay() {
    if (!audioElement.value) return
    if (isPlaying.value) {
      pause()
    } else {
      resume()
    }
  }

  /** 暂停 */
  function pause() {
    if (audioElement.value) {
      audioElement.value.pause()
      isPlaying.value = false
    }
  }

  /** 继续播放 */
  function resume() {
    if (audioElement.value && currentTrack.value) {
      audioElement.value.play().then(() => {
        isPlaying.value = true
      }).catch(e => {
        console.warn('续播失败:', e.message)
      })
    }
  }

  /** 停止 */
  function stop() {
    if (audioElement.value) {
      audioElement.value.pause()
      audioElement.value.currentTime = 0
      isPlaying.value = false
      currentTime.value = 0
      duration.value = 0
    }
  }

  /** 上一首 */
  function prev() {
    if (tracks.value.length === 0) return
    const idx = currentIndex.value <= 0 ? tracks.value.length - 1 : currentIndex.value - 1
    play(idx)
  }

  /** 下一首 */
  function next() {
    if (tracks.value.length === 0) return
    const idx = (currentIndex.value + 1) % tracks.value.length
    play(idx)
  }

  /** 设置音量 */
  function setVolume(vol) {
    volume.value = Math.max(0, Math.min(100, vol))
    if (audioElement.value) {
      audioElement.value.volume = volume.value / 100
    }
  }

  /** 跳转到指定进度 */
  function seek(time) {
    if (audioElement.value) {
      audioElement.value.currentTime = time
      currentTime.value = time
    }
  }

  /** 播放指定id的歌曲 */
  function playById(id) {
    const idx = tracks.value.findIndex(t => t.id === id)
    if (idx !== -1) {
      play(idx)
    }
  }

  // ---- Audio 事件处理 ----
  function onTimeUpdate() {
    if (audioElement.value) {
      currentTime.value = audioElement.value.currentTime
    }
  }

  function onLoaded() {
    if (audioElement.value) {
      duration.value = audioElement.value.duration
    }
  }

  function onEnded() {
    // 自动播放下一首
    next()
  }

  function onError() {
    isPlaying.value = false
    ElMessage.warning('音频加载失败')
  }

  return {
    // 状态
    tracks, currentIndex, isPlaying, volume, currentTime, duration, loading,
    // 计算
    currentTrack, trackCount, progress,
    // 方法
    fetchTracks, upload, remove, play, togglePlay, pause, resume, stop, prev, next, setVolume, seek, playById
  }
})
