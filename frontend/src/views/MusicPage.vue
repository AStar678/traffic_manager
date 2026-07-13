<template>
  <div class="music-page">
    <!-- 左侧：歌曲列表 -->
    <section class="track-list-panel">
      <div class="panel-header">
        <h2><el-icon><Headset /></el-icon> 音乐库</h2>
        <el-upload
          :show-file-list="false"
          :before-upload="handleBeforeUpload"
          :http-request="handleUpload"
          accept=".mp3,.wav,.flac,.ogg,.m4a"
        >
          <el-button type="primary" size="small" :loading="uploading">
            <el-icon><Upload /></el-icon> 上传本地音乐
          </el-button>
        </el-upload>
      </div>

      <el-table
        :data="store.tracks"
        style="width: 100%"
        highlight-current-row
        @row-click="handleRowClick"
        empty-text="暂无音乐，请上传"
        max-height="420"
      >
        <el-table-column type="index" label="#" width="50" />
        <el-table-column prop="title" label="歌名" min-width="180">
          <template #default="{ row }">
            <div class="track-title" :class="{ active: store.currentTrack?.id === row.id }">
              <el-icon v-if="store.currentTrack?.id === row.id && store.isPlaying" class="playing-icon">
                <VideoPlay />
              </el-icon>
              {{ row.title }}
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="artist" label="歌手" width="140" />
        <el-table-column label="时长" width="80">
          <template #default="{ row }">
            {{ row.duration ? formatTime(row.duration) : '--:--' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button type="danger" size="small" text @click.stop="handleDelete(row)">
              <el-icon><Delete /></el-icon>
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="track-count" v-if="store.trackCount > 0">
        共 {{ store.trackCount }} 首歌曲
      </div>
    </section>

    <!-- 右侧：播放器 -->
    <section class="player-panel">
      <div class="player-card">
        <!-- 专辑封面占位 -->
        <div class="album-art">
          <el-icon :size="80"><Headset /></el-icon>
          <div class="eq-bars" v-if="store.isPlaying">
            <span v-for="i in 5" :key="i" class="eq-bar" :style="{ animationDelay: i * 0.15 + 's' }"></span>
          </div>
        </div>

        <!-- 歌曲信息 -->
        <div class="track-info">
          <h3>{{ store.currentTrack?.title || '未选择歌曲' }}</h3>
          <p>{{ store.currentTrack?.artist || '--' }}</p>
        </div>

        <!-- 进度条 -->
        <div class="progress-area">
          <span class="time">{{ formatTime(store.currentTime) }}</span>
          <el-slider
            v-model="sliderValue"
            :max="store.duration || 100"
            :disabled="!store.currentTrack"
            :show-tooltip="false"
            @change="handleSeek"
            class="progress-slider"
          />
          <span class="time">{{ formatTime(store.duration) }}</span>
        </div>

        <!-- 播放控制 -->
        <div class="controls">
          <el-button :disabled="!store.currentTrack" circle @click="store.prev()">
            <el-icon :size="20"><VideoPrevious /></el-icon>
          </el-button>
          <el-button
            type="primary"
            circle
            size="large"
            :disabled="!store.currentTrack"
            @click="store.togglePlay()"
            class="play-btn"
          >
            <el-icon :size="28">
              <VideoPause v-if="store.isPlaying" />
              <VideoPlay v-else />
            </el-icon>
          </el-button>
          <el-button :disabled="!store.currentTrack" circle @click="store.next()">
            <el-icon :size="20"><VideoNext /></el-icon>
          </el-button>
        </div>

        <!-- 音量 -->
        <div class="volume-area">
          <el-icon><VideoPlay v-if="store.volume > 0" /><VideoMute v-else /></el-icon>
          <el-slider
            v-model="store.volume"
            :max="100"
            :show-tooltip="false"
            class="volume-slider"
            @input="store.setVolume(store.volume)"
          />
          <span class="volume-num">{{ store.volume }}</span>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useMusicStore } from '@/stores/music'
import { ElMessage, ElMessageBox } from 'element-plus'

const store = useMusicStore()
const uploading = ref(false)
const sliderValue = ref(0)

// 同步进度条
watch(() => store.currentTime, (val) => {
  sliderValue.value = val
})

onMounted(() => {
  store.fetchTracks()
})

function handleBeforeUpload(file) {
  const validTypes = ['audio/mpeg', 'audio/wav', 'audio/flac', 'audio/ogg', 'audio/mp4', 'audio/x-m4a',
    'audio/mp3', 'audio/x-wav', 'audio/x-flac', 'application/octet-stream']
  const ext = file.name.split('.').pop().toLowerCase()
  const validExts = ['mp3', 'wav', 'flac', 'ogg', 'm4a']
  if (!validExts.includes(ext)) {
    ElMessage.error('仅支持 MP3 / WAV / FLAC / OGG / M4A 格式')
    return false
  }
  if (file.size > 50 * 1024 * 1024) {
    ElMessage.error('文件大小不能超过 50MB')
    return false
  }
  return true
}

async function handleUpload(options) {
  uploading.value = true
  try {
    await store.upload(options.file)
  } finally {
    uploading.value = false
  }
}

function handleRowClick(row) {
  store.playById(row.id)
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定删除「${row.title}」吗？`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
    await store.remove(row.id)
  } catch { /* 取消 */ }
}

function handleSeek(val) {
  store.seek(val)
}

function formatTime(seconds) {
  if (!seconds || !isFinite(seconds)) return '0:00'
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}
</script>

<style scoped>
.music-page {
  display: grid;
  grid-template-columns: 1fr 380px;
  gap: 24px;
  height: 100%;
  padding: 20px 24px;
  box-sizing: border-box;
}

/* ---- 左侧列表 ---- */
.track-list-panel {
  background: rgba(255,255,255,0.04);
  border-radius: 16px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  border: 1px solid rgba(255,255,255,0.06);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.panel-header h2 {
  margin: 0;
  font-size: 18px;
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-primary, #e0e0e0);
}
.header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.track-title {
  display: flex;
  align-items: center;
  gap: 6px;
}
.track-title.active {
  color: #409eff;
  font-weight: 600;
}
.playing-icon {
  animation: pulse 0.8s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.track-count {
  margin-top: 12px;
  text-align: center;
  font-size: 13px;
  color: var(--text-secondary, #999);
}

/* ---- 右侧播放器 ---- */
.player-panel {
  display: flex;
  align-items: flex-start;
}
.player-card {
  width: 100%;
  background: rgba(255,255,255,0.04);
  border-radius: 16px;
  padding: 32px 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
  border: 1px solid rgba(255,255,255,0.06);
  position: sticky;
  top: 20px;
}

.album-art {
  width: 160px;
  height: 160px;
  border-radius: 50%;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  border: 3px solid rgba(64,158,255,0.3);
}
.album-art .el-icon {
  color: rgba(255,255,255,0.6);
}

.eq-bars {
  position: absolute;
  bottom: 24px;
  display: flex;
  gap: 3px;
  align-items: flex-end;
  height: 30px;
}
.eq-bar {
  width: 4px;
  background: #409eff;
  border-radius: 2px;
  animation: eq 0.8s ease-in-out infinite alternate;
}
@keyframes eq {
  0% { height: 6px; }
  100% { height: 28px; }
}

.track-info {
  text-align: center;
}
.track-info h3 {
  margin: 0 0 4px;
  font-size: 18px;
  color: var(--text-primary, #e0e0e0);
}
.track-info p {
  margin: 0;
  font-size: 14px;
  color: var(--text-secondary, #999);
}

.progress-area {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
}
.progress-slider {
  flex: 1;
}
.time {
  font-size: 12px;
  color: var(--text-secondary, #999);
  width: 36px;
  text-align: center;
  font-variant-numeric: tabular-nums;
}

.controls {
  display: flex;
  align-items: center;
  gap: 20px;
}
.play-btn {
  width: 56px;
  height: 56px;
}

.volume-area {
  width: 60%;
  display: flex;
  align-items: center;
  gap: 10px;
}
.volume-slider {
  flex: 1;
}
.volume-num {
  width: 28px;
  font-size: 13px;
  text-align: right;
  color: var(--text-secondary, #999);
}

/* Element Plus 表格深色适配 */
:deep(.el-table) {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: rgba(255,255,255,0.04);
  --el-table-border-color: rgba(255,255,255,0.06);
  --el-table-text-color: #e0e0e0;
  --el-table-header-text-color: #bbb;
  --el-table-row-hover-bg-color: rgba(64,158,255,0.1);
}
:deep(.el-table__empty-text) {
  color: #999;
}

/* 响应式 */
@media (max-width: 900px) {
  .music-page {
    grid-template-columns: 1fr;
  }
  .player-panel {
    position: static;
  }
}
</style>
