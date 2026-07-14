import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { ElMessage } from 'element-plus'

const MUSIC_SOURCE_URL = 'https://tannerhelland.com/music.html'
const MUSIC_LICENSE_URL = 'https://creativecommons.org/licenses/by/4.0/'

const builtInTracks = [
  {
    id: 'daybreak',
    title: 'Daybreak',
    artist: 'Tanner Helland',
    album: 'VisionDrive 公路歌单',
    duration: 114.076735,
    url: '/audio/daybreak.mp3',
    sourceUrl: MUSIC_SOURCE_URL,
    licenseUrl: MUSIC_LICENSE_URL,
    license: 'CC BY 4.0',
    tone: 'dawn',
    isLocal: false
  },
  {
    id: 'familiar-roads',
    title: 'Familiar Roads',
    artist: 'Tanner Helland',
    album: 'VisionDrive 公路歌单',
    duration: 223.085714,
    url: '/audio/familiar-roads.mp3',
    sourceUrl: MUSIC_SOURCE_URL,
    licenseUrl: MUSIC_LICENSE_URL,
    license: 'CC BY 4.0',
    tone: 'road',
    isLocal: false
  },
  {
    id: 'syntheticity',
    title: 'Syntheticity',
    artist: 'Tanner Helland',
    album: 'VisionDrive 公路歌单',
    duration: 205.035102,
    url: '/audio/syntheticity.mp3',
    sourceUrl: MUSIC_SOURCE_URL,
    licenseUrl: MUSIC_LICENSE_URL,
    license: 'CC BY 4.0',
    tone: 'night',
    isLocal: false
  }
]

function storedVolume() {
  const stored = globalThis.localStorage?.getItem('visiondrive-music-volume')
  if (stored === null || stored === undefined || stored === '') return 42
  const value = Number(stored)
  return Number.isFinite(value) ? Math.min(100, Math.max(0, value)) : 42
}

function parseFileName(fileName) {
  const baseName = fileName.replace(/\.[^.]+$/, '').trim()
  const [artist, ...titleParts] = baseName.split(/\s+-\s+/)
  if (titleParts.length) {
    return { artist: artist.trim(), title: titleParts.join(' - ').trim() }
  }
  return { artist: '本地音乐', title: baseName || '未命名歌曲' }
}

export const useMusicStore = defineStore('music', () => {
  const tracks = ref(builtInTracks.map(track => ({ ...track })))
  const currentIndex = ref(0)
  const isPlaying = ref(false)
  const volume = ref(storedVolume())
  const currentTime = ref(0)
  const duration = ref(tracks.value[0]?.duration || 0)
  const playbackError = ref('')
  let audioElement = null
  let previousVolume = volume.value || 42

  const currentTrack = computed(() => tracks.value[currentIndex.value] || null)
  const trackCount = computed(() => tracks.value.length)

  function ensureAudio() {
    if (audioElement || typeof Audio === 'undefined') return audioElement
    audioElement = new Audio()
    audioElement.preload = 'metadata'
    audioElement.volume = volume.value / 100
    audioElement.addEventListener('timeupdate', handleTimeUpdate)
    audioElement.addEventListener('loadedmetadata', handleLoadedMetadata)
    audioElement.addEventListener('ended', next)
    audioElement.addEventListener('error', handleAudioError)
    audioElement.addEventListener('pause', () => { isPlaying.value = false })
    audioElement.addEventListener('play', () => { isPlaying.value = true })
    return audioElement
  }

  function loadTrack(index) {
    if (index < 0 || index >= tracks.value.length) return null
    const audio = ensureAudio()
    if (!audio) return null
    const track = tracks.value[index]
    currentIndex.value = index
    currentTime.value = 0
    duration.value = track.duration || 0
    playbackError.value = ''
    audio.src = track.url
    audio.load()
    return audio
  }

  async function play(index = currentIndex.value) {
    if (!tracks.value.length) return
    const shouldLoad = index !== currentIndex.value || !audioElement?.src
    const audio = shouldLoad ? loadTrack(index) : ensureAudio()
    if (!audio) return
    try {
      await audio.play()
    } catch (error) {
      isPlaying.value = false
      playbackError.value = '播放未能启动，请再次轻触播放键'
      console.warn('音乐播放失败:', error)
    }
  }

  function playById(id) {
    const index = tracks.value.findIndex(track => track.id === id)
    if (index >= 0) play(index)
  }

  function togglePlay() {
    if (isPlaying.value) pause()
    else play()
  }

  function pause() {
    audioElement?.pause()
    isPlaying.value = false
  }

  function prev() {
    if (!tracks.value.length) return
    const index = currentIndex.value <= 0 ? tracks.value.length - 1 : currentIndex.value - 1
    play(index)
  }

  function next() {
    if (!tracks.value.length) return
    const index = (currentIndex.value + 1) % tracks.value.length
    play(index)
  }

  function seek(value) {
    const audio = ensureAudio()
    if (!audio || !Number.isFinite(Number(value))) return
    const nextTime = Math.min(duration.value || 0, Math.max(0, Number(value)))
    audio.currentTime = nextTime
    currentTime.value = nextTime
  }

  function setVolume(value) {
    const nextVolume = Math.min(100, Math.max(0, Number(value)))
    if (nextVolume > 0) previousVolume = nextVolume
    volume.value = nextVolume
    if (audioElement) audioElement.volume = nextVolume / 100
    globalThis.localStorage?.setItem('visiondrive-music-volume', String(nextVolume))
  }

  function toggleMute() {
    setVolume(volume.value > 0 ? 0 : previousVolume)
  }

  function addLocalTrack(file) {
    const extension = file.name.split('.').pop()?.toLowerCase()
    if (!['mp3', 'wav', 'flac', 'ogg', 'm4a'].includes(extension)) {
      ElMessage.error('仅支持 MP3 / WAV / FLAC / OGG / M4A 格式')
      return false
    }
    if (file.size > 50 * 1024 * 1024) {
      ElMessage.error('单个音乐文件不能超过 50MB')
      return false
    }

    const metadata = parseFileName(file.name)
    tracks.value.push({
      id: `local-${Date.now()}-${Math.random().toString(16).slice(2)}`,
      ...metadata,
      album: '本次驾驶',
      duration: 0,
      url: URL.createObjectURL(file),
      license: '本地文件',
      tone: 'local',
      isLocal: true
    })
    ElMessage.success(`已加入「${metadata.title}」`)
    return true
  }

  function removeLocalTrack(id) {
    const index = tracks.value.findIndex(track => track.id === id && track.isLocal)
    if (index < 0) return
    const [removed] = tracks.value.splice(index, 1)
    URL.revokeObjectURL(removed.url)

    if (index === currentIndex.value) {
      pause()
      if (audioElement) {
        audioElement.removeAttribute('src')
        audioElement.load()
      }
      currentIndex.value = Math.min(index, tracks.value.length - 1)
      currentTime.value = 0
      duration.value = currentTrack.value?.duration || 0
    } else if (index < currentIndex.value) {
      currentIndex.value -= 1
    }
  }

  function handleTimeUpdate() {
    if (audioElement) currentTime.value = audioElement.currentTime
  }

  function handleLoadedMetadata() {
    if (!audioElement || !Number.isFinite(audioElement.duration)) return
    duration.value = audioElement.duration
    if (currentTrack.value) currentTrack.value.duration = audioElement.duration
  }

  function handleAudioError() {
    isPlaying.value = false
    playbackError.value = '音频加载失败，请检查文件后重试'
  }

  return {
    tracks,
    currentIndex,
    currentTrack,
    trackCount,
    isPlaying,
    volume,
    currentTime,
    duration,
    playbackError,
    play,
    playById,
    togglePlay,
    pause,
    prev,
    next,
    seek,
    setVolume,
    toggleMute,
    addLocalTrack,
    removeLocalTrack
  }
})
