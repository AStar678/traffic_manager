<template>
  <div class="music-page">
    <header class="music-heading">
      <div>
        <span class="section-kicker">DRIVE SOUND</span>
        <h1>车载音乐</h1>
        <p>为驾驶舱准备的离线曲库，切歌与进度控制无需连接后端。</p>
      </div>
      <div class="heading-actions">
        <span class="library-status"><i class="status-dot online"></i>{{ store.trackCount }} 首可播放</span>
        <input
          ref="fileInput"
          class="file-input"
          type="file"
          multiple
          accept=".mp3,.wav,.flac,.ogg,.m4a,audio/*"
          @change="handleFileInput"
        >
        <el-button type="primary" @click="openFilePicker">
          <el-icon><Upload /></el-icon>
          导入本地音乐
        </el-button>
      </div>
    </header>

    <div class="music-workspace">
      <section class="card library-panel" aria-labelledby="library-title">
        <div class="panel-heading">
          <div>
            <span class="panel-eyebrow">OFFLINE LIBRARY</span>
            <h2 id="library-title">驾驶歌单</h2>
          </div>
          <span class="track-total">{{ store.trackCount.toString().padStart(2, '0') }}</span>
        </div>

        <div class="track-list">
          <article
            v-for="(track, index) in store.tracks"
            :key="track.id"
            class="track-row"
            :class="{ active: store.currentTrack?.id === track.id }"
          >
            <button class="track-main" type="button" @click="store.playById(track.id)">
              <span class="track-index" aria-hidden="true">
                <span v-if="store.currentTrack?.id === track.id && store.isPlaying" class="mini-eq">
                  <i></i><i></i><i></i>
                </span>
                <el-icon v-else-if="store.currentTrack?.id === track.id"><VideoPlay /></el-icon>
                <span v-else>{{ String(index + 1).padStart(2, '0') }}</span>
              </span>
              <span class="track-copy">
                <strong>{{ track.title }}</strong>
                <small>{{ track.artist }} · {{ track.album }}</small>
              </span>
              <span class="track-duration mono">{{ formatTime(track.duration) }}</span>
            </button>
            <div class="track-meta">
              <a
                v-if="track.sourceUrl"
                :href="track.sourceUrl"
                target="_blank"
                rel="noreferrer"
                :aria-label="`查看 ${track.title} 的授权来源`"
              >{{ track.license }}</a>
              <span v-else>{{ track.license }}</span>
              <button
                v-if="track.isLocal"
                type="button"
                class="remove-track"
                :aria-label="`移除 ${track.title}`"
                @click="store.removeLocalTrack(track.id)"
              >
                <el-icon><Delete /></el-icon>
              </button>
            </div>
          </article>
        </div>

        <footer class="library-note">
          <el-icon><FolderOpened /></el-icon>
          <span>本地导入仅保留在当前浏览器会话，单个文件上限 50MB。</span>
        </footer>
      </section>

      <section class="card player-panel" :class="[`tone-${store.currentTrack?.tone || 'dawn'}`, { playing: store.isPlaying }]" aria-labelledby="now-playing-title">
        <div class="player-topline">
          <span id="now-playing-title">NOW PLAYING</span>
          <span class="play-state"><i></i>{{ store.isPlaying ? '播放中' : '已暂停' }}</span>
        </div>

        <div class="album-stage" aria-hidden="true">
          <div class="road-orbit orbit-one"></div>
          <div class="road-orbit orbit-two"></div>
          <div class="record-disc">
            <span class="record-label">VD</span>
          </div>
          <div class="frequency-bars">
            <i v-for="bar in 9" :key="bar" :style="{ '--bar': bar }"></i>
          </div>
        </div>

        <div class="current-track">
          <span>{{ store.currentTrack?.album || 'VisionDrive' }}</span>
          <h2>{{ store.currentTrack?.title || '选择一首歌曲' }}</h2>
          <p>{{ store.currentTrack?.artist || '—' }}</p>
        </div>

        <div class="timeline">
          <input
            :value="store.currentTime"
            type="range"
            min="0"
            :max="Math.max(store.duration, 1)"
            step="0.1"
            aria-label="播放进度"
            :style="progressStyle"
            @input="handleSeek"
          >
          <div class="timeline-labels mono">
            <span>{{ formatTime(store.currentTime) }}</span>
            <span>{{ formatTime(store.duration) }}</span>
          </div>
        </div>

        <p v-if="store.playbackError" class="playback-error" role="status">{{ store.playbackError }}</p>

        <div class="transport" aria-label="音乐播放控制">
          <button type="button" aria-label="上一首" @click="store.prev">
            <el-icon><DArrowLeft /></el-icon>
          </button>
          <button class="play-button" type="button" :aria-label="store.isPlaying ? '暂停' : '播放'" @click="store.togglePlay">
            <el-icon>
              <VideoPause v-if="store.isPlaying" />
              <VideoPlay v-else />
            </el-icon>
          </button>
          <button type="button" aria-label="下一首" @click="store.next">
            <el-icon><DArrowRight /></el-icon>
          </button>
        </div>

        <div class="volume-control">
          <button type="button" :aria-label="store.volume > 0 ? '静音' : '恢复音量'" @click="store.toggleMute">
            <el-icon><Mute v-if="store.volume === 0" /><Headset v-else /></el-icon>
          </button>
          <input
            :value="store.volume"
            type="range"
            min="0"
            max="100"
            step="1"
            aria-label="音量"
            :style="volumeStyle"
            @input="handleVolume"
          >
          <span class="mono">{{ store.volume.toString().padStart(2, '0') }}</span>
        </div>

        <footer class="music-credit">
          内置音乐由
          <a href="https://tannerhelland.com/music.html" target="_blank" rel="noreferrer">Tanner Helland</a>
          创作，采用
          <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noreferrer">CC BY 4.0</a>
        </footer>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useMusicStore } from '@/stores/music'

const store = useMusicStore()
const fileInput = ref(null)

const progressStyle = computed(() => ({
  '--range-progress': `${store.duration ? (store.currentTime / store.duration) * 100 : 0}%`
}))

const volumeStyle = computed(() => ({ '--range-progress': `${store.volume}%` }))

function openFilePicker() {
  fileInput.value?.click()
}

function handleFileInput(event) {
  Array.from(event.target.files || []).forEach(store.addLocalTrack)
  event.target.value = ''
}

function handleSeek(event) {
  store.seek(Number(event.target.value))
}

function handleVolume(event) {
  store.setVolume(Number(event.target.value))
}

function formatTime(seconds) {
  if (!Number.isFinite(Number(seconds)) || Number(seconds) <= 0) return '0:00'
  const minutes = Math.floor(Number(seconds) / 60)
  const remainder = Math.floor(Number(seconds) % 60)
  return `${minutes}:${String(remainder).padStart(2, '0')}`
}
</script>

<style scoped>
.music-page {
  width: min(100%, 1480px);
  min-height: 100%;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.music-heading,
.heading-actions,
.panel-heading,
.player-topline,
.timeline-labels,
.volume-control {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.music-heading {
  gap: 24px;
}

.section-kicker,
.panel-eyebrow,
.player-topline {
  color: var(--primary-color);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 1.7px;
}

.music-heading h1 {
  margin-top: 3px;
  color: var(--text-primary);
  font-size: 26px;
  line-height: 1.15;
  letter-spacing: -0.5px;
}

.music-heading p {
  margin-top: 6px;
  color: var(--text-muted);
  font-size: 13px;
}

.heading-actions {
  flex: 0 0 auto;
  gap: 16px;
}

.library-status {
  display: inline-flex;
  align-items: center;
  color: var(--text-secondary);
  font-size: 12px;
}

.file-input {
  display: none;
}

.music-workspace {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(350px, 410px);
  gap: 18px;
  align-items: stretch;
}

.library-panel,
.player-panel {
  min-width: 0;
  padding: 20px;
}

.library-panel {
  display: flex;
  flex-direction: column;
}

.panel-heading {
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border-subtle);
}

.panel-heading h2 {
  margin-top: 3px;
  font-size: 19px;
  color: var(--text-primary);
}

.track-total {
  color: rgba(0, 180, 216, 0.3);
  font-family: "SF Mono", "Cascadia Code", monospace;
  font-size: 34px;
  font-weight: 800;
  line-height: 1;
}

.track-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 8px 0;
}

.track-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.055);
  transition: background var(--duration-fast), border-color var(--duration-fast);
}

.track-row:hover,
.track-row:focus-within {
  background: rgba(255, 255, 255, 0.025);
}

.track-row.active {
  background: linear-gradient(90deg, rgba(0, 180, 216, 0.11), rgba(0, 180, 216, 0.015));
  border-bottom-color: rgba(0, 180, 216, 0.24);
}

.track-main {
  min-width: 0;
  min-height: 70px;
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr) 56px;
  align-items: center;
  gap: 12px;
  padding: 9px 10px;
  border: 0;
  background: transparent;
  color: inherit;
  text-align: left;
  cursor: pointer;
}

.track-main:focus-visible,
.transport button:focus-visible,
.volume-control button:focus-visible,
.remove-track:focus-visible {
  outline: 2px solid var(--primary-color);
  outline-offset: -2px;
}

.track-index {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  border: 1px solid var(--border-subtle);
  border-radius: 50%;
  color: var(--text-muted);
  font-family: "SF Mono", "Cascadia Code", monospace;
  font-size: 11px;
}

.active .track-index {
  border-color: var(--border-active);
  background: var(--primary-soft);
  color: var(--primary-color);
}

.track-copy {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.track-copy strong,
.track-copy small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.track-copy strong {
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 750;
}

.track-copy small {
  color: var(--text-muted);
  font-size: 11px;
}

.active .track-copy strong {
  color: var(--primary-color);
}

.track-duration {
  color: var(--text-secondary);
  font-size: 12px;
  text-align: right;
}

.track-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  padding-right: 12px;
  color: var(--text-muted);
  font-size: 10px;
}

.track-meta a {
  padding: 4px 7px;
  border: 1px solid var(--border-subtle);
  border-radius: 999px;
  color: var(--text-muted);
}

.track-meta a:hover {
  border-color: var(--border-active);
  color: var(--primary-color);
}

.remove-track {
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
}

.remove-track:hover {
  background: rgba(255, 61, 0, 0.1);
  color: var(--danger-color);
}

.mini-eq {
  height: 14px;
  display: flex;
  align-items: flex-end;
  gap: 2px;
}

.mini-eq i {
  width: 2px;
  height: 45%;
  border-radius: 2px;
  background: var(--primary-color);
  animation: miniEq 700ms ease-in-out infinite alternate;
}

.mini-eq i:nth-child(2) { animation-delay: -350ms; }
.mini-eq i:nth-child(3) { animation-delay: -180ms; }

.library-note {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-top: 13px;
  border-top: 1px solid var(--border-subtle);
  color: var(--text-muted);
  font-size: 11px;
}

.player-panel {
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  align-items: center;
  background:
    radial-gradient(circle at 50% 25%, rgba(0, 180, 216, 0.11), transparent 42%),
    var(--bg-card);
}

.player-panel::before {
  content: '';
  position: absolute;
  inset: 0;
  opacity: 0.38;
  pointer-events: none;
  background-image: linear-gradient(rgba(255, 255, 255, 0.025) 1px, transparent 1px);
  background-size: 100% 24px;
}

.player-topline {
  position: relative;
  z-index: 1;
  width: 100%;
}

.play-state {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--text-muted);
  font-size: 10px;
  letter-spacing: 0;
}

.play-state i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-muted);
}

.playing .play-state {
  color: var(--success-color);
}

.playing .play-state i {
  background: var(--success-color);
  box-shadow: 0 0 8px rgba(0, 230, 118, 0.5);
}

.album-stage {
  position: relative;
  width: 214px;
  height: 214px;
  flex: 0 0 214px;
  display: grid;
  place-items: center;
  margin: 14px 0 9px;
}

.road-orbit,
.record-disc {
  position: absolute;
  border-radius: 50%;
}

.road-orbit {
  border: 1px solid rgba(0, 180, 216, 0.18);
}

.orbit-one { inset: 8px; }
.orbit-two { inset: 24px; border-style: dashed; }

.record-disc {
  inset: 35px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(255, 255, 255, 0.18);
  background:
    radial-gradient(circle, var(--primary-color) 0 5px, #0b101b 6px 22px, rgba(0, 180, 216, 0.7) 23px 25px, transparent 26px),
    repeating-radial-gradient(circle, #111827 0 4px, #080c14 5px 7px);
  box-shadow: 0 14px 34px rgba(0, 0, 0, 0.42), 0 0 30px rgba(0, 180, 216, 0.09);
}

.playing .record-disc,
.playing .orbit-two {
  animation: spin 10s linear infinite;
}

.record-label {
  position: relative;
  z-index: 1;
  color: var(--text-primary);
  font-family: "SF Mono", "Cascadia Code", monospace;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 1px;
}

.frequency-bars {
  position: absolute;
  right: 6px;
  bottom: 28px;
  height: 42px;
  display: flex;
  align-items: flex-end;
  gap: 3px;
}

.frequency-bars i {
  width: 3px;
  height: calc(7px + (var(--bar) % 5) * 5px);
  border-radius: 4px;
  background: var(--primary-color);
  opacity: 0.35;
}

.playing .frequency-bars i {
  opacity: 0.85;
  animation: frequency 760ms ease-in-out infinite alternate;
  animation-delay: calc(var(--bar) * -85ms);
}

.tone-road { --primary-glow: rgba(0, 230, 118, 0.18); }
.tone-road .record-disc { filter: hue-rotate(38deg); }
.tone-night .record-disc { filter: hue-rotate(65deg); }
.tone-local .record-disc { filter: hue-rotate(150deg); }

.current-track {
  position: relative;
  z-index: 1;
  width: 100%;
  min-width: 0;
  text-align: center;
}

.current-track span {
  color: var(--primary-color);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 1.2px;
  text-transform: uppercase;
}

.current-track h2 {
  margin: 6px 0 4px;
  overflow: hidden;
  color: var(--text-primary);
  font-size: 21px;
  line-height: 1.2;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.current-track p {
  color: var(--text-muted);
  font-size: 12px;
}

.timeline {
  position: relative;
  z-index: 1;
  width: 100%;
  margin-top: 18px;
}

input[type='range'] {
  width: 100%;
  height: 20px;
  margin: 0;
  appearance: none;
  -webkit-appearance: none;
  background: transparent;
  cursor: pointer;
}

input[type='range']::-webkit-slider-runnable-track {
  height: 4px;
  border-radius: 999px;
  background: linear-gradient(90deg, var(--primary-color) var(--range-progress), rgba(255, 255, 255, 0.1) var(--range-progress));
}

input[type='range']::-webkit-slider-thumb {
  width: 14px;
  height: 14px;
  margin-top: -5px;
  appearance: none;
  -webkit-appearance: none;
  border: 3px solid var(--bg-card);
  border-radius: 50%;
  background: var(--primary-color);
  box-shadow: 0 0 0 1px var(--primary-color), 0 0 12px var(--primary-glow);
}

input[type='range']::-moz-range-track {
  height: 4px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.1);
}

input[type='range']::-moz-range-progress {
  height: 4px;
  border-radius: 999px;
  background: var(--primary-color);
}

input[type='range']::-moz-range-thumb {
  width: 12px;
  height: 12px;
  border: 2px solid var(--bg-card);
  border-radius: 50%;
  background: var(--primary-color);
}

input[type='range']:focus-visible {
  outline: 2px solid var(--primary-color);
  outline-offset: 3px;
  border-radius: 999px;
}

.timeline-labels {
  color: var(--text-muted);
  font-size: 10px;
}

.playback-error {
  position: relative;
  z-index: 1;
  margin-top: 8px;
  color: var(--warning-color);
  font-size: 11px;
}

.transport {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 24px;
  margin-top: 16px;
}

.transport button,
.volume-control button {
  display: grid;
  place-items: center;
  border: 1px solid var(--border-card);
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.035);
  color: var(--text-secondary);
  cursor: pointer;
  transition: border-color var(--duration-fast), color var(--duration-fast), transform var(--duration-fast);
}

.transport button {
  width: 42px;
  height: 42px;
  font-size: 18px;
}

.transport button:hover,
.volume-control button:hover {
  border-color: var(--border-active);
  color: var(--primary-color);
}

.transport .play-button {
  width: 58px;
  height: 58px;
  border-color: var(--primary-color);
  background: var(--primary-color);
  color: var(--text-inverse);
  font-size: 26px;
  box-shadow: 0 0 28px var(--primary-glow);
}

.transport .play-button:hover {
  color: var(--text-inverse);
  transform: scale(1.04);
}

.volume-control {
  position: relative;
  z-index: 1;
  width: 72%;
  gap: 10px;
  margin-top: 14px;
}

.volume-control button {
  flex: 0 0 30px;
  width: 30px;
  height: 30px;
}

.volume-control input {
  flex: 1;
}

.volume-control > span {
  width: 24px;
  color: var(--text-muted);
  font-size: 10px;
  text-align: right;
}

.music-credit {
  position: relative;
  z-index: 1;
  width: 100%;
  margin-top: auto;
  padding-top: 16px;
  color: var(--text-muted);
  font-size: 9px;
  text-align: center;
}

.music-credit a {
  color: var(--text-secondary);
  text-decoration: underline;
  text-underline-offset: 2px;
}

@keyframes spin { to { transform: rotate(360deg); } }
@keyframes miniEq { from { height: 35%; } to { height: 100%; } }
@keyframes frequency { from { transform: scaleY(0.35); } to { transform: scaleY(1); } }

@media (max-width: 960px) {
  .music-workspace {
    grid-template-columns: minmax(0, 1fr) 340px;
  }

  .track-main {
    grid-template-columns: 38px minmax(0, 1fr) 48px;
    gap: 8px;
  }

  .track-meta a {
    max-width: 56px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

@media (max-width: 760px) {
  .music-heading {
    align-items: flex-start;
    flex-direction: column;
    gap: 12px;
  }

  .music-heading h1 { font-size: 23px; }
  .heading-actions { width: 100%; }
  .heading-actions .el-button { margin-left: auto; }

  .music-workspace {
    display: flex;
    flex-direction: column;
  }

  .player-panel { order: -1; }

  .album-stage {
    width: 178px;
    height: 178px;
    flex-basis: 178px;
  }

  .library-panel,
  .player-panel { padding: 16px; }
  .track-main { min-height: 66px; padding-left: 4px; }
  .track-meta { padding-right: 6px; }
}

@media (max-width: 430px) {
  .library-status { display: none; }
  .track-main { grid-template-columns: 34px minmax(0, 1fr) 42px; }
  .track-meta a { display: none; }
  .volume-control { width: 88%; }
}

@media (prefers-reduced-motion: reduce) {
  .playing .record-disc,
  .playing .orbit-two,
  .playing .frequency-bars i,
  .mini-eq i {
    animation: none;
  }
}
</style>
